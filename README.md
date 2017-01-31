nocrux is a painless per-user daemon manager that is easily configured
with a Python 3 script in the users home directory. It supports many of the
common settings to start daemon processes such as redirecting stdout/stderr,
pidfiles (required), additional arguments, process current working directory
and more.

__EXAMPLE CONFIGURATION__

The configuration file for nocrux must be in `~/nocrux_config.py`.

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

__COMMANDLINE INTERFACE__

```
usage: nocrux [-h]
              {version,start,stop,restart,status,fn:out,fn:err,fn:pid,pid,tail,tail:out,tail:err}
              [daemon [daemon ...]]

painless per-user daemon manager. https://github.com/NiklasRosenstein/nocrux

positional arguments:
  {version,start,stop,restart,status,fn:out,fn:err,fn:pid,pid,tail,tail:out,tail:err}
  daemon                name of one or more daemons to interact with. Use
                        'all' to refer to all registered daemons

optional arguments:
  -h, --help            show this help message and exit
```

__EXAMPLE USAGE__

    niklas@sunbird ~$ nocrux start test
    [nocrux]: (test) starting "/home/niklas/Desktop/daemon.sh"
    [nocrux]: (test) started. (pid: 3203)
    niklas@sunbird ~$ nocrux status all
    [nocrux]: (test) started
    niklas@sunbird ~$ nocrux tail test
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
    ^Cniklas@sunbird ~$ nocrux stop all
    [nocrux]: (test) stopping... done

> **Note**: In the example above, we use a shell-script to start an example daemon.
> If that shell script invokes other processes, it must make sure to forward SIGTERM
> to these processes. A common method is to use `exec command args...` as it will
> effectively replace the shell of the script with the new processes shell and
> automatically receive signals.
>
> See http://unix.stackexchange.com/q/146756/73728 for more information.

__INSTALLATION__

    pip install nocrux

__REQUIREMENTS__

* Python 3
* Unix-like operating system (tested on Ubuntu 15.05, Mac OS X El Capitan)
* Pandoc when installing from the Git repository (not required for Pip installation)

__CHANGELOG__

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
