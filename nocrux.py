# Copyright (c) 2017  Niklas Rosenstein
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
__version__ = '2.0.0'

import argparse
import collections
import errno
import glob
import nr.parse.strex as strex
import os
import pwd, grp
import runpy
import shlex
import signal
import string
import subprocess
import sys
import textwrap
import time
import types

config = {
  'root': os.path.expanduser('~/.nocrux/run'),
  'kill_timeout': 10
}
daemons = {}


def abspath(path):
  ''' Make *path* absolute if it not already is. Relative paths
  are assumed relative to the ``config['root']`` configuration
  parameter.

  .. note:: This function can not be used before the :data:`config`
    is loaded.
  '''

  path = os.path.expanduser(path)
  if not os.path.isabs(path):
    return os.path.abspath(os.path.join(config['root'], path))
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
  ''' Configuration for a daemon process. '''

  Status_Started = 'started'
  Status_Stopped = 'stopped'

  def __init__(
      self, name, prog, args=(), cwd=None, user=None, group=None,
      stdin=None, stdout=None, stderr=None, pidfile=None,
      requires=None, env=None):
    if not pidfile:
      pidfile = abspath(name + '.pid')
    if stdout is None:
      stdout = abspath(name + '.out')

    if not requires:
      requires = []
    if name in requires:
      raise ValueError('daemon can not require itself')

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
    self.requires = requires
    self.env = {} if env is None else env

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

    # Make sure all dependent daemons are running as well.
    if self.requires:
      self.log('checking requirements ...')
    for name in self.requires:
      if name not in daemons:
        self.log('* "{0}" does not exist')
        return False
      daemon = daemons[name]
      daemon.start()

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
        cmd = 'tail:err' if self.stderr else 'tail'
        self.log('could not be started. try "nocrux {} {}"'.format(self.name, cmd))
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
    command = [os.path.expanduser(self.prog)] + self.args
    self.log('starting', '"' + ' '.join(map(shlex.quote, command)) + '"')

    # Replace the standard file handles and execute the daemon process.
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())
    env = os.environ.copy()
    if self.env:
      env.update(self.env)
    process = subprocess.Popen(command, env=env)
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
      while time.time() - tstart < config['kill_timeout'] and process_exists(pid):
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


class ConfigParser(object):

  Section = collections.namedtuple('Section', 'name value data subsections')

  rules = [
    strex.Charset('ws', string.whitespace, skip=True),
    strex.Charset('key', string.ascii_letters + '_/'),
    strex.Keyword('left_bracket', '{'),
    strex.Keyword('right_bracket', '}'),
    strex.Keyword('semicolon', ';'),
    strex.Charset('value', set(map(chr, range(0,255))) - set('{};')),  # TODO
  ]

  @staticmethod
  def parse(source):
    lexer = strex.Lexer(strex.Scanner(source), ConfigParser.rules)
    return ConfigParser._parse_section(lexer, None, None, False)

  @staticmethod
  def _parse_section(lexer, name, value, expect_closing=True):
    section = ConfigParser.Section(name, value, [], [])
    while True:
      if not expect_closing:
        key = lexer.next('key', 'eof')
      else:
        key = lexer.next('key', 'right_bracket')
      if key.type in ('right_bracket', 'eof'): break
      value = lexer.next('value', weighted=True)
      if value: value = value.value.strip()
      if lexer.next('semicolon', 'left_bracket').type == 'semicolon':
        section.data.append((key.value, value))
      else:
        section.subsections.append(ConfigParser._parse_section(lexer, key.value, value))
    return section


def load_config(filename):
  ''' Load the nocrux configuration from *filename*. '''

  with open(filename) as fp:
    section = ConfigParser.parse(fp.read())

  for key, value in section.data:
    if key == 'include':
      path = value
      if not os.path.isabs(path):
        path = os.path.join(os.path.dirname(filename), path)
      if '?' in path or '*' in path:
        for fname in glob.iglob(path):
          load_config(fname)
      else:
        load_config(path)
    elif key == 'root':
      if not os.path.isabs(value):
        raise ValueError('root must be an absolute path')
      config['root'] = value
    elif key == 'kill_timeout':
      config['kill_timeout'] = int(value.strip())
    else:
      raise ValueError('unexpected config key: {}'.format(key))

  for subsection in section.subsections:
    if subsection.name != 'daemon':
      raise ValueError('unexpected section: {}'.format(subsection.name))
    if not subsection.value:
      raise ValueError('daemon section requies a value')
    if subsection.subsections:
      raise ValueError('daemon section does not expect subsections')
    name = subsection.value
    params = {'name': name}
    for key, value in subsection.data:
      if key == 'run':
        args = shlex.split(value)
        if len(args) < 1:
          raise ValueError('daemon {}: run field is empty'.format(name))
        params['prog'] = args[0]
        params['args'] = args[1:]
      elif key == 'cwd':
        params['cwd'] = value.strip()
      elif key == 'export':
        key, sep, value = value.strip().partition('=')
        if not sep:
          raise ValueError('daemon {}: invalid export key'.format(name))
        params.setdefault('env', {})[key] = value
      elif key in ('user', 'group'):
        params[key] = value.strip()
      elif key in ('stdin', 'stdout', 'stderr', 'pidfile'):
        if key == 'stderr' and value.strip() == '$stdout':
          value = None
        if value:
          value = string.Template(value).safe_substitute(name=name, root=config['root'])
        params[key] = value
      elif key == 'requires':
        items = value.strip().split(' ')
        if not items:
          raise ValueError('daemon {}: requires field is invalid'.format(name))
        params['requires'] = items
      else:
        raise ValueError('daemon {}: unexpected config key: {}'.format(name, item))
      daemons[name] = Daemon(**params)


def main():
  parser = argparse.ArgumentParser(
    prog='nocrux',
    description="""
      a painless per-user daemon manager.
      https://github.com/NiklasRosenstein/nocrux
      """)
  parser.add_argument(
    'daemon',
    default=[],
    help="name of one or more daemons to interact with. Use 'all' to refer "
         "to all registered daemons. Can be comma-separated to list multiple "
         "daemons.")
  parser.add_argument(
    'command',
    choices=['version', 'start', 'stop', 'restart', 'status',
             'pid', 'tail', 'tail:out', 'tail:err'])
  args = parser.parse_args()

  if args.command == 'version':
    print('nocrux v{}'.format(__version__))
    return 0

  args.daemons = args.daemon.strip(',').split(',')
  if not args.daemons:
    parser.error('need at least one argument for "daemons"')

  # Load the nocrux configuration file.
  config_file = os.path.expanduser('~/.nocrux/conf')
  if not os.path.isfile(config_file):
    config_file = '/etc/nocrux/conf'
    config['root'] = '/var/run/nocrux'
    if not os.path.isfile(config_file):
      print("Error: file '~/.nocrux/conf' or '/etc/nocrux/conf' does not exist")
      return 1
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
      daemon.stop()
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
  elif args.command in ('pid', 'tail', 'tail:out', 'tail:err'):
    if len(target_daemons) != 1 or args.daemons == ['all']:
      parser.error('command "{0}": only one daemon name expected'.format(args.command))
    daemon = target_daemons[0]
    if args.command in ('tail', 'tail:out'):
      if daemon.stdout:
        try:
          subprocess.call(['tail', '-f', daemon.stdout])
        except KeyboardInterrupt:
          pass
    elif args.command == 'tail:err':
      if daemon.stderr:
        try:
          subprocess.call(['tail', '-f', daemon.stderr])
        except KeyboardInterrupt:
          pass
    elif args.command == 'pid':
      print(daemon.pid)
    else:
      assert False
    return 0

  parser.error('unknown command {!r}'.format(args.command))


if ('require' in globals() and require.main == module) or __name__ == '__main__':
  sys.exit(main())
