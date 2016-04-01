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
__version__ = '1.1.1-dev'

import argparse
import errno
import os
import pwd, grp
import runpy
import shlex
import signal
import subprocess
import sys
import textwrap
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
  except OSError as exc:
    if exc.errno == errno.ESRCH:
      return False
  return True


class Daemon(object):
  ''' Configuration for a daemon process. See ``nocrux_config.py``
  for an explanation of the parameters. '''

  Status_Started = 'started'
  Status_Stopped = 'stopped'

  def __init__(
      self, name, prog, args=(), cwd=None, user=None, group=None,
      stdin=None, stdout=None, stderr=None, pidfile=None):
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
      print('[nocrux]: ({0})'.format(self.name), *message, **kwargs)
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

    # Fork so we can detach from the parent process etc. The parent
    # will wait for a little time to check if the process has started.
    pid = os.fork()
    if pid > 0:
      time.sleep(0.20)
      pid = self.pid
      if process_exists(pid):
        self.log('started. (pid: {0})'.format(pid))
      else:
        outname = 'err' if self.stderr else 'out'
        self.log('could not be started. try  "tail -f $(nocrux fn:{0} {1})"'.format(outname, self.name))
      return True

    # Make sure the directory of the PID and output files exist.
    makedirs(os.path.dirname(self.pidfile))
    makedirs(os.path.dirname(self.stdin))
    makedirs(os.path.dirname(self.stdout))
    makedirs(os.path.dirname(self.stderr or self.stdout))

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
    # so the caller of nocrux can still read it.
    command = [self.prog] + self.args
    self.log('starting', '"' + ' '.join(map(shlex.quote, command)) + '"')

    # Replace the standard file handles and execute the daemon process.
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())
    process = subprocess.Popen(command)
    try:
      with open(self.pidfile, 'w') as pidf:
        pidf.write(str(process.pid))
    except OSError as exc:
      process.kill()
      process.wait()
      self.log('pid file "{0}" could not be created.'.format(self.pidfile), file=sys.stderr)
      self.log('process killed. error:', exc, file=sys.stderr)

    # Wait until the process exits to delete the pidfile.
    process.wait()
    self.log('terminated. exit code: {0}'.format(process.returncode), file=sys.stderr)
    try:
      os.remove(self.pidfile)
    except OSError:
      self.log('warning: pid file "{0}" could not be removed'.format(self.pidfile), file=sys.stderr)
    sys.exit(0)

  def stop(self):
    ''' Stop the daemon if it is running. Sends :data:`signal.SIGTERM`
    first, then waits at maximum ``config.kill_timeout`` seconds and
    sends ``signal.SIGKILL`` if the process hasn't terminated by then. '''

    pid = self.pid
    if pid == 0:
      self.log('daemon not running')
      return

    try:
      os.kill(pid, signal.SIGTERM)
    except OSError as exc:
      self.log('failed:', exc)
    else:
      self.log('stopping...', end=' ')
      tstart = time.time()
      while time.time() - tstart < config.kill_timeout and process_exists(pid):
        time.sleep(0.5)
      if process_exists(pid):
        self.log('failed')
        self.log('killing...')
        try: os.kill(pid, signal.SIGKILL)
        except OSError: pass
        if process_exists(pid):
          self.log('failed')
        else:
          self.log('done')
      else:
        self.log('done')


def register_daemon(**kwargs):
  ''' Register a daemon to nocrux. The arguments are the same as for
  the :class:`Daemon` class, though only keyword-arguments are accepted. '''

  daemon = Daemon(**kwargs)
  if daemon.name in daemons:
    raise ValueError('daemon name {!r} already in use'.format(daemon))
  daemons[daemon.name] = daemon


def load_config(filename):
  ''' Load the nocrux configuration from *filename*. This effectively
  executes *filename* and returns a Python module object. '''

  module = types.ModuleType('nocrux_config')
  module.__file__ = filename
  module.join = os.path.join
  module.split = os.path.split
  module.expanduser = os.path.expanduser
  module.register_daemon = register_daemon

  # Initialize default values for configuration parameters before
  # executing the configure script.
  module.root_dir = os.path.expanduser('~/.nocrux')
  module.kill_timeout = 10

  global config
  config = module

  try:
    with open(filename) as fp:
      exec(fp.read(), vars(module))
  except:
    config = None
    raise


def main():
  parser = argparse.ArgumentParser(
    prog='nocrux',
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description=textwrap.dedent('''
      nocrux is a painless per-user daemon manager. Every user can
      configure daemons in the `~/nocrux_config.py` file using the
      `register_daemon()` function. An example configuration file
      may look like this:

      ```python
      root_dir = expanduser('~/.nocrux')  # default
      kill_timeout = 10  # default
      register_daemon(
        name = 'test',
        prog = expanduser('~/Desktop/my-daemon.sh'),
        args = [],     # default
        cwd  = '~',    # default, automatically expanded after setting user ID
        user = None,   # name of the user, defaults to current user
        group = None,  # name of the group, defaults to current user group
        stdin = None,  # stdin file, defaults to /dev/null
        stdout = None, # stdout file, defaults to ${root_dir}/${name}.out
        stderr = None, # stderr file, defaults to stdout
        pidfile = None,# pid file, defaults to ${root_dir}/${name}.pid
      )
      ```

      The daemon can then be controlled by the `nocrux` command.

          $ nocrux start test
          [nocrux]: (test) starting "/home/niklas/Desktop/daemon.sh"
          [nocrux]: (test) started. (pid: 3203)
          $ nocrux status all
          [nocrux]: (test) started
          $ nocrux tail test
          daemon.sh started
          [nocrux]: (test) terminated. exit code: -15
          daemon.sh started
          [nocrux]: (test) terminated. exit code: -15
          daemon.sh started
          [nocrux]: (test) terminated. exit code: -15
          daemon.sh started
          daemon.sh ended
          [nocrux]: (test) terminated. exit code: 0
          daemon.sh started
          ^C$ nocrux stop all
          [nocrux]: (test) stopping... done
      '''))
  parser.add_argument(
    'command',
    choices=['start', 'stop', 'restart', 'status', 'version', 'tail'])
  parser.add_argument(
    'daemons',
    metavar='daemon',
    nargs='*',
    default=[],
    help="name of one or more daemons to interact with. the special name"
         "'all' can be used to refer to all registered daemons")
  parser.add_argument(
    '-e', '--stderr',
    action='store_true',
    help="display stderr rather than stdout. only used for the 'tail' command")
  args = parser.parse_args()

  if args.command == 'version':
    print('nocrux v{}'.format(__version__))
    return 0
  if not args.daemons:
    parser.error('need at least one argument for "daemons"')

  # Load the nocrux configuration file.
  config_file = os.path.expanduser('~/nocrux_config.py')
  if not os.path.isfile(config_file):
    parser.error('"{0}" does not exist'.format(config_file))
  load_config(config_file)

  if args.daemons == ['all']:
    target_daemons = list(daemons.values())
  else:
    try:
      target_daemons = [daemons[x] for x in args.daemons]
    except KeyError as exc:
      parser.error('unknown daemon {!r}'.format(str(exc)))

  if args.command == 'status':
    for daemon in target_daemons:
      daemon.log(daemon.status)
    return 0
  elif args.command == 'stop':
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
      daemon.stop()
    for daemon in target_daemons:
      if not daemon.start():
        return 1
    return 0
  elif args.command == 'tail':
    if len(target_daemons) != 1 or args.daemons == ['all']:
      parser.error('can only select one daemon for "tail" command')
    daemon = target_daemons[0]
    if args.stderr:
      if not daemon.stderr:
        daemon.log('no stderr')
        return 1
      fn = daemon.stderr
    else:
      if not daemon.stdout:
        daemon.log('no stdout')
        return 1
      fn = daemon.stdout
    try:
      return subprocess.call(['tail', '-f', fn])
    except KeyboardInterrupt:
      return 0

  parser.error('unknown command {!r}'.format(args.command))
