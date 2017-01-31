# nocrux

*nocrux* is a painless per-user daemon manager that is easily configured
with a Python 3 script in the users home directory. It supports many of the
common settings to start daemon processes such as redirecting stdout/stderr,
pidfiles (required), additional arguments, current working directory and more.

## Installation

The *nocrux* daemon manager is available via Pip. Python 3 is required. It has
been tested on Ubuntu 15.05 and macOS Sierra.

    $ pip3 install nocrux

> **Note**: Installing from the Git repository requires Pandoc.

## Configuration

The configuration file for *nocrux* is `~/nocrux_config.py`. Below is a sample
configuration that highlights the available options and their default values.

```python
root_dir = expanduser('~/.nocrux')  # default
kill_timeout = 10  # default
register_daemon(
  name = 'test',
  prog = expanduser('~/Desktop/my-daemon.sh'),
  args = [],      # default
  cwd  = '~',     # default, automatically expanded after setting user ID
  user = None,    # name of the user, defaults to current user
  group = None,   # name of the group, defaults to current user group
  stdin = None,   # stdin file, defaults to /dev/null
  stdout = None,  # stdout file, defaults to ${root_dir}/${name}.out
  stderr = None,  # stderr file, defaults to stdout
  pidfile = None, # pid file, defaults to ${root_dir}/${name}.pid
  requires = [],  # default, list of daemon names that need to run before this
)
```

## Command-line Interface

    nocrux [daemon(s)] command

The following commands expect no daemon(s) on the command-line.

- `version` -- Print the version of *nocrux* and exit

The following commands expect one or more daemons be specified on the command-line.

- `start` -- Start the daemon(s)
- `stop` -- Stop the daemon(s)
- `restart` -- Restart the daemon(s)
- `status` -- Show the status of the daemon(s)

The following commands expect exactly one daemon be specified on the command-line.

- `tail`-- Alias for `tail:out`
- `tail:out` -- Shows the tail of the daemons' stdout
- `tail:err` -- Shows the tail of the daemons' stderr
- `pid` -- Print the PID of the daemon (0 if the daemon is not running)
- `fn:out` -- Prints the path to the stdout file
- `fn:err` -- Prints the path to the stderr file
- `fn:pid` -- Prints the path to the PID file

## Daemon termination

*nocrux* can only send SIGTERM (and alternatively SIGKILL if the process doesn't response
to the previous signal) to the main process that was also started with *nocrux*. If that
process spawns any subprocess, it must take care of forwarding the signals to the child
processes.

The thread [Forward SIGTERM to child in Bash](http://unix.stackexchange.com/q/146756/73728)
contains some information on doing that for Bash scripts. For very simple scripts that just
set up an environment, I reccomend the `exec` approach.

## Example

    niklas@sunbird ~$ nocrux test start
    [nocrux]: (test) starting "/home/niklas/Desktop/daemon.sh"
    [nocrux]: (test) started. (pid: 3203)
    niklas@sunbird ~$ nocrux all status
    [nocrux]: (test) started
    niklas@sunbird ~$ nocrux test tail
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
    ^Cniklas@sunbird ~$ nocrux all stop
    [nocrux]: (test) stopping... done

## Changelog

v2.0.0

* cli is now `nocrux <daemon> <command>` (switched)
* to specify multiple daemons, the `<daemon>` argument can be a list of
  comma separated daemon names

v1.1.3

* update `README.md` (corrected example and command-line interface)
* remove unusued `-e, --stderr` argument
* fix `setup.py` (use `py_modules` instead of the invalid `modules` parameter)
* enable running `nocrux.py` directly without prior installation
* add `pid`, `tail`, `tail:out` and `tail:err` subcommands

v1.1.2

* add `setup.py` installation script, remove `nocrux` script
* update `README.md` and renamed from `README.markdown`

v1.1.1

* close #18: Automatically expand prog ~ before starting process
* fix #17: PID file not deleted after daemon stopped
* close #16: Tail command is counter intuitive
* update output of command-line program
* process exit code is now printed to daemon standard error output file
* fixed stopping multiple daemons when one wasn't running
* implement #10: daemon dependencies

v1.1.0

* Renamed to `nocrux`
* Update README and command-line help description

v1.0.1

* Add `krugs tail <daemon> [-e/-stderr]` command
* Add special deaemon name `all`
* Fix `krugs restart` command
