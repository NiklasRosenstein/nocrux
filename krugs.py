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

import argparse
import errno
import os
import pwd, grp
import time
import shlex
import signal
import subprocess
import sys

# Imported later to give the config file access to the Krugs API
config = None


def abspath(path):
  if not os.path.isabs(path):
    return os.path.abspath(os.path.join(config.root_dir, path))
  return path


class Daemon(object):
  ''' Configuration for a daemon process.

  :param name: The name of the daemon. This name is used when invoking
    Krugs to address a specific daemon.
  :param bin: Path to the daemon executable/script.
  :param args: A list of additional arguments for the daemon process.
  :param stdout: Filename to pipe the standard output to. If None,
    the file is piped into ``dev/null``.
  :param stderr: Filename to pipe the standard output to. If None,
    the file is piped into the same file/device as *stdout*.
  :param user: The name of the user to execute the daemon as.
  :param group: The name of the group to execute the daemon as.
  :param login: If true, the ``-l`` option is passed to bash.
  :param cwd: The working directory for the daemon process.
    Defaults to the HOME directory of the user that executes
    the process.
  '''

  objects = {}

  def __init__(self, name, bin, args=(), pidfile=None,
      stdin='/dev/null', stdout=None, stderr=None,
      user=None, group=None, login=True, cwd=None):

    if name in Daemon.objects:
      raise ValueError('daemon name {!r} already reserved'.format(name))
    if cwd and not os.path.isdir(cwd):
      raise ValueError('directory {!r} does not exist'.format(cwd))

    if not pidfile:
      pidfile = abspath(name + '.pid')
    if stdout is None:
      stdout = abspath(name + '.out')

    self.name = name
    self.bin = bin
    self.args = list(args)
    self.pidfile = pidfile
    self.stdin = stdin
    self.stdout = stdout
    self.stderr = stderr
    self.user = user
    self.group = group
    self.login = login
    self.cwd = cwd
    Daemon.objects[name] = self

  def pid(self):
    try:
      with open(self.pidfile, 'r') as fp:
        value = fp.read().strip()
        try:
          return int(value)
        except ValueError:
          return 0
    except OSError as exc:
      if exc.errno != errno.ENOENT:
        raise
      return 0

  def start(self):
    ''' Start the Daemon if it is not already running. '''

    if self.status():
      print('[{}]: already running')
      return True

    print('[{}]: starting ...'.format(self.name))

    home, uid, gid = None, None, None
    if self.user:
      home, uid, gid = get_user_info(self.user)
    if self.group:
      gid = get_group_id(self.group)

    # Fork so we can update detach, etc.
    pid = os.fork()
    if pid > 0:
      # Wait until the child process started the actual daemon.
      if os.waitpid(pid, 0)[1] == 0:
        print('[{}]: started'.format(self.name))
      else:
        print('[{}]: could not be started'.format(self.name))
      return True

    # Open the PID file.
    makedirs(os.path.dirname(self.pidfile))
    pidf = open(self.pidfile, 'w')

    try:
      os.setsid()
      if uid is not None:
        try:
          os.setuid(uid)
        except OSError as exc:
          if exc.errno != errno.EPERM:
            raise
          print('[{}]: not permitted to change to user {!r}'.format(self.name, self.user))
          sys.exit(errno.EPERM)
      if gid is not None:
        try:
          os.setgid(gid)
        except OSError as exc:
          if exc.errno != errno.EPERM:
            raise
          print('[{}]: not permitted to change to group {!r}'.format(self.name, self.group))
          sys.exit(errno.EPERM)
      if home:
        os.environ['HOME'] = home

      if self.cwd:
        os.chdir(self.cwd)
      else:
        os.chdir(os.environ['HOME'])

      # Generate the comamnd to execute.
      command = [self.bin] + self.args

      # Redirect the standard in, out and error.
      si = open(self.stdin, 'r')
      so = open(self.stdout, 'a+')
      if self.stderr:
        se = open(self.stderr, 'a+')
      else:
        se = so

      # Print the command before updating the in/out/err file handles.
      print('[{}]: $'.format(self.name), ' '.join(map(shlex.quote, command)))
      os.dup2(si.fileno(), sys.stdin.fileno())
      os.dup2(so.fileno(), sys.stdout.fileno())
      os.dup2(se.fileno(), sys.stderr.fileno())

      # Execute the daemon.
      process = subprocess.Popen(command)
      pidf.write(str(process.pid))

      sys.exit(0)
    finally:
      pidf.close()

  def status(self, pid=None, do_print=False):
    ''' Returns True if the process is running, otherwise false. '''

    if pid is None:
      pid = self.pid()
    if pid == 0:
      if do_print:
        print('[{}]: stopped'.format(self.name))
      return False
    if not pid_exists(pid):
      if do_print:
        print('[{}]: stopped'.format(self.name))
      return False
    else:
      if do_print:
        print('[{}]: running'.format(self.name))
      return True

  def stop(self):
    pid = self.pid()
    try:
      os.kill(pid, signal.SIGTERM)
    except OSError:
      print('[{}]: not running'.format(self.name))
    else:
      print('[{}]: SIGTERM sent'.format(self.name))
      tstart = time.time()
      while time.time() - tstart < config.kill_timeout and pid_exists(pid):
        time.sleep(0.5)
      if pid_exists(pid):
        try:
          os.kill(pid, signal.SIGKILL)
        except OSError:
          pass
        else:
          print('[{}]: SIGKILL sent'.format(self.name))
      print('[{}]: stopped'.format(self.name))


def get_user_info(user_name):
  record = pwd.getpwnam(user_name)
  return record.pw_dir, record.pw_uid, record.pw_gid


def get_group_id(group_name):
  record = grp.getgrnam(group_name)
  return record.gr_gid


def makedirs(path):
  if not os.path.exists(path):
    os.makedirs(path)


def pid_exists(pid):
  try:
    os.kill(pid, 0)
  except OSError:
    return False
  return True


def main():
  parser = argparse.ArgumentParser(prog='krugs', description='A simple daemon manager')
  parser.add_argument('daemon', choices=Daemon.objects.keys())
  parser.add_argument('command', choices=['start', 'stop', 'restart', 'status'])
  args = parser.parse_args()

  daemon = Daemon.objects[args.daemon]
  if args.command == 'start':
    if daemon.start():
      sys.exit(0)
    sys.exit(1)
  elif args.command == 'stop':
    if daemon.stop():
      sys.exit(0)
    sys.exit(1)
  elif args.command == 'restart':
    daemon.stop()
    if daemon.start():
      sys.exit(0)
    sys.exit(1)
  elif args.command == 'status':
    if daemon.status(do_print=True):
      sys.exit(0)
    sys.exit(1)
  else:
    assert False


import krugs_config as config
