# Krugs - Simple daemon manager ![](http://i.imgur.com/TV2l7Iy.png) ![](http://i.imgur.com/uuTtLzU.png)

Krugs is a simple manager for daemon processes. It is easier to use and
deploy than using/writing `init.d` scripts and the Unix `service` command.
Also, Krugs can be used by any user and not just root.

Krugs only works with Unix-like systems.

    niklas@sunbird:~$ krugs status test
    - [test]: stopped
    niklas@sunbird:~$ krugs start test
    - [test]: running /home/niklas/Desktop/my-daemon.sh
    - [test]: started (PID: 4717)
    niklas@sunbird:~$ krugs status
    - [test]: started
    niklas@sunbird:~$ krugs stop test
    - [test]: stopping... stopped
    niklas@sunbird:~$ krugs status all
    - [test]: stopped
    niklas@sunbird:~$ krugs tail test
    Sleeping 60 seconds from now ...
    Complete.
    Sleeping 60 seconds from now ...

__Configuration__

Krugs is configured with a Python script in your home directory called
`krugs_config.py`. Below you can find an example of what that file could
look like. It is fairly long due to the commentary. For this configuration
script, the following functions are already available and need not be
imported manually:

* `join()`, `split()` and `expanduser()` from `os.path`
* `register_daemon()` from `krugs`

```python
# The path of the folder that contains the PID files and standard error
# and output files for relative paths.
root_dir = expanduser('~/.krugs')

# The maximum number of seconds to wait after SIGTERM to send SIGKILL.
kill_timeout = 10

# Declare daemons using the #register_daemon() function. Example:
register_daemon(
  # The name of the daemon that you will use to address it on
  # the command-line.
  name = 'test',

  # The name or full path of the program to execute.
  prog = expanduser('~/Desktop/my-daemon.sh'),

  # Additional command-line arguments for the daemon.
  args = [],

  # The directory to change to for executing the daemon program.
  # The path is passed through #expanduser(), thus `~` will be
  # the home directory of the user that the daemon is run under
  # (important if you changed the user parameter below).
  # Passing None will make the path default to the executing users
  # home directory as well.
  cwd = '~',

  # The username to log-in to when starting the daemon. Sets HOME,
  # but does not using shell login. The user that starts the
  # daemon with Krugs must be allowed to switch to that user.
  user = None,

  # The user group to switch to.
  group = None,

  # The file for stdin. Defaults to /dev/null.
  stdin = None,

  # The output file for stdout. Defaults to $root_dir/$name.out .
  # Explicitly use /dev/null if you want it.
  stdout = None,

  # The output file for stderr. Defaults to the exact same file
  # as stdout when set to None.
  stderr = None,

  # The filename where the PID is saved to. Defaults to
  # $root_dir/$name.pid .
  pidfile = None,
)
```

__Todo__

* [ ] Support for daemon dependencies

__Requirements__

* Python 3

__Changelog__

*v1.0.1*

* Add `krugs tail <daemon> [-e/-stderr]` command
* Add special deaemon name `all`
* Fix `krugs restart` command
