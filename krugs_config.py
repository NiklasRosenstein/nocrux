'''
Krugs configuration file.
'''

import os, sys
import krugs
krugs.config = sys.modules[__name__]

from os.path import expanduser as expath
from krugs import Daemon

# The path of the folder that contains the PID files and standard error
# and output files for relative paths.
root_dir = os.path.join(os.path.dirname(__file__), 'run')

# The maximum number of seconds to wait after SIGTERM to send SIGKILL.
kill_timeout = 10

# Create Daemon objects to declare the available daemons to Krugs.
# The arguments pidfile, stdin, stdout, stderr, user and group are optional.
# Daemon processes are executed with the shell.
Daemon(
  name = 'test',
  bin = expath('~/Desktop/test.sh'),
  args = ['42'],
)

