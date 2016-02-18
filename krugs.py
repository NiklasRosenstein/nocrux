# Copyright (c) 2016  Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

__author__ = 'Niklas Rosenstein <rosensteinniklas@gmail.com>'
__version__ = '1.0.0'

import argparse
import errno
import os
import pwd, grp
import runpy
import shlex
import signal
import subprocess
import sys
import time
import types

# The configuration module object that is imported later.
config = None

# A dictionary of all daemons registered with #register_daemon().
daemons = {}


def abspath(path):
  ''' Make *path* absolute if it not already is. Relative paths
  are assumed relative to the ``config.root_dir`` configuration
  parameter.

  .. note:: This function can not be used before the :data:`config`
    is loaded.
  '''

  if not os.path.isabs(path):
    return os.path.abspath(os.path.join(config.root_dir, path))
  return path


def makedirs(path):
  ''' Create the directory *path* if it does not already exist. '''

  if not os.path.exists(path):
    os.makedirs(path)


def process_exists(pid):
  ''' Checks if the process represented by *pid* exists and returns
  True in that case, otherwise False. '''

  if pid == 0:
    return False
  try:
    os.kill(pid, 0)
  except OSError:
    return False
  return True


class Daemon(object):
  ''' Configuration for a daemon process. See ``krugs_config.py``
  for an explanation of the parameters. '''

  Status_Started = 'started'
  Status_Stopped = 'stopped'

  def __init__(
      self, name, prog, args=(), cwd=None, user=None, group=None,
      stdin=None, stdout=None, stderr=None, pidfile=None):

    if cwd and not os.path.isdir(cwd):
      raise ValueError('directory {!r} does not exist'.format(cwd))

    if not pidfile:
      pidfile = abspath(name + '.pid')
    if stdout is None:
      stdout = abspath(name + '.out')

    self._log_newline = True
    self.name = name
    self.prog = prog
    self.args = list(args)
    self.cwd = cwd
    self.user = user
    self.group = group
    self.stdin = stdin or '/dev/null'
    self.stdout = stdout
    self.stderr = stderr
    self.pidfile = pidfile

  def __repr__(self):
    return '<Daemon {!r}: {}>'.format(self.name, self.status)

  @property
  def pid(self):
    ''' Returns the PID of the daemon. It is read from the file
    as referenced by the :attr:`pidfile` attribute. If the file
    contains an invalid PID or is empty or if the file does not
    exist, 0 is returned. '''

    try:
      with open(self.pidfile, 'r') as fp:
        pid_str = fp.readline()
    except OSError as exc:
      if exc.errno != errno.ENOENT:
        raise
      pid_str = ''

    try:
      return int(pid_str)
    except ValueError:
      return 0

  @property
  def status(self):
    ''' Reads the PID and checks if the process under that PID
    exists. Returns :data:`Status_Stopped` or :data:`Status_Started`. '''

    if process_exists(self.pid):
      return self.Status_Started
    else:
      return self.Status_Stopped

  def log(self, *message, **kwargs):
    ''' Prints a message with the name of the daemon as its prefix. '''

    if self._log_newline:
      print('Krugs: [{}]:'.format(self.name), *message, **kwargs)
    else:
      print(*message, **kwargs)
    self._log_newline = '\n' in kwargs.get('end', '\n')
    kwargs.get('file', sys.stdout).flush()

  def start(self):
    ''' Start the daemon if it is not already running. Returns True
    if the daemon is already running or could be started, False if
    it could not be started. '''

    if self.status == self.Status_Started:
      self.log('daemon already started')
      return True

    # Get the user and group information if any.
    home, uid, gid = None, None, None
    if self.user:
      record = pwd.getpwnam(self.user)
      home, uid, gid = record.pw_dir, record.pw_uid, record.pw_gid
    if self.group:
      record = grp.getgrnam(self.group)
      gid = record.gr_gid

    # Fork so we can update detach, etc. The parent waits until
    # the child exits to figure if the process could be started.
    pid = os.fork()
    if pid > 0:
      if os.waitpid(pid, 0)[1] == 0:
        self.log('started (PID: {})'.format(self.pid))
      else:
        self.log('could not be started, check the output file eventually')
      return True

    # Make sure the directory of the PID and output files exist.
    makedirs(os.path.dirname(self.pidfile))
    makedirs(os.path.dirname(self.stdin))
    makedirs(os.path.dirname(self.stdout))
    makedirs(os.path.dirname(self.stderr or self.stdout))

    pidf = open(self.pidfile, 'w')
    try:
      # Detach the process and set the user and group IDs if applicable.
      os.setsid()
      if uid is not None:
        try:
          os.setuid(uid)
        except OSError as exc:
          if exc.errno != errno.EPERM:
            raise
          self.log('not permitted to change to user {!r}'.format(self.user))
          sys.exit(errno.EPERM)
      if gid is not None:
        try:
          os.setgid(gid)
        except OSError as exc:
          if exc.errno != errno.EPERM:
            raise
          self.log('not permitted to change to group {!r}'.format(self.group))
          sys.exit(errno.EPERM)

      # Update the HOME environment variable and switch the working
      # directory for the daemon process.
      if home:
        os.environ['HOME'] = home
      if self.cwd:
        os.chdir(os.path.expanduser(self.cwd))
      else:
        os.chdir(os.environ['HOME'])

      # Open the input file and output files for the daemon.
      si = open(self.stdin, 'r')
      so = open(self.stdout, 'a+')
      se = open(self.stderr, 'a+') if self.stderr else so

      # Print the command before updating the in/out/err file handles
      # so the caller of Krugs can still read it.
      command = [self.prog] + self.args
      self.log('running:', ' '.join(map(shlex.quote, command)))

      # Replace the standard file handles and execute the daemon process.
      os.dup2(si.fileno(), sys.stdin.fileno())
      os.dup2(so.fileno(), sys.stdout.fileno())
      os.dup2(se.fileno(), sys.stderr.fileno())
      process = subprocess.Popen(command)
      pidf.write(str(process.pid))
      sys.exit(0)
    finally:
      pidf.close()

  def stop(self):
    ''' Stop the daemon if it is running. Sends :data:`signal.SIGTERM`
    first, then waits at maximum ``config.kill_timeout`` seconds and
    sends ``signal.SIGKILL`` if the process hasn't terminated by then. '''

    pid = self.pid
    try:
      os.kill(pid, signal.SIGTERM)
    except OSError:
      self.log('not started')
    else:
      self.log('stopping...', end=' ')
      tstart = time.time()
      while time.time() - tstart < config.kill_timeout and process_exists(pid):
        time.sleep(0.5)
      if process_exists(pid):
        self.log('not stopped.', end=' ')
        try:
          os.kill(pid, signal.SIGKILL)
        except OSError:
          self.log('stopped')
        else:
          self.log('SIGKILL')
      else:
        self.log('stopped')


def register_daemon(**kwargs):
  ''' Register a daemon to Krugs. The arguments are the same as for
  the :class:`Daemon` class, though only keyword-arguments are accepted. '''

  daemon = Daemon(**kwargs)
  if daemon.name in daemons:
    raise ValueError('daemon name {!r} already used'.format(daemon))
  daemons[daemon.name] = daemon


def load_config(filename):
  ''' Load the Krugs configuration from *filename*. This effectively
  executes *filename* and returns a Python module object. '''

  module = types.ModuleType('krugs_config')
  module.__file__ = filename
  module.join = os.path.join
  module.split = os.path.split
  module.expanduser = os.path.expanduser
  module.register_daemon = register_daemon

  global config
  config = module

  try:
    with open(filename) as fp:
      exec(fp.read(), vars(module))
  except:
    config = None
    raise


def main():
  parser = argparse.ArgumentParser(prog='krugs', description='A simple daemon manager')
  parser.add_argument('command', choices=['start', 'stop', 'restart', 'status', 'version', 'list'])
  parser.add_argument('daemons', nargs='*', default=[])
  args = parser.parse_args()

  if args.command == 'version':
    print('Krugs v{}'.format(__version__))
    return 0

  # Load the Krugs configuration file.
  config_file = os.path.expanduser('~/krugs_config.py')
  if not os.path.isfile(config_file):
    parser.error('~/krugs_config.py does not exist')
  load_config(config_file)

  try:
    target_daemons = [daemons[x] for x in args.daemons]
  except KeyError as exc:
    parser.error('unknown daemon {!r}'.format(str(exc)))

  if args.command == 'status':
    for daemon in (target_daemons or daemons.values()):
      daemon.log(daemon.status)
    return 0
  elif args.command == 'list':
    for daemon in daemons.keys():
      print(daemon)
    return 0
  elif not args.daemons:
    parser.error('need at least one argument for "daemons"')

  if args.command == 'stop':
    for daemon in target_daemons:
      if not daemon.stop():
        return 1
    return 0
  elif args.command == 'start':
    for daemon in target_daemons:
      if not daemon.start():
        return 1
    return 0
  elif args.command == 'restart':
    for daemon in target_daemons:
      if not daemon.stop():
        return 1
    for daemon in target_daemons:
      if not daemon.start():
        return 1
    return 0

  parser.error('unknown command {!r}'.format(args.command))
