# nocrux

Nocrux is an easily configurable daemon manager that can be used by any user
on the system. It uses double-forks to transfer cleanup responsibility of
daemons to the init process.

__Synopsis__

```
Usage: nocrux [OPTIONS] [DAEMON] [COMMAND]

  Available COMMANDs: start, stop, restart, status, pid, cat, tail

Options:
  -e, --edit    Edit the nocrux configuration file.
  -l, --list    List up all daemons and their status.
  -f, --follow  Pass -f to the tail command.
  --stderr      Choose stderr instead of stdout for the cat/tail command.
  --version     Print the nocrux version and exit.
  --help        Show this message and exit.
```

__Requirements__

- Unix-like OS (tested on Ubuntu 25.05, Debian Jessie, macOS Sierra)
- Python 3.4+
- [Node.py] (optional)

[Node.py]: https://github.com/nodepy/nodepy

__Installation__

    $ pip3 install nocrux    # or
    $ nodepy-pm install git+https://github.com/NiklasRosenstein/nocrux.git@v2.0.2

__A note about daemon termination__

*nocrux* can only send SIGTERM (and alternatively SIGKILL if the process
doesn't respond to the previous signal) to the main process that was also
started with *nocrux*. If that process spawns any subprocess, it must take
care of forwarding the signals to the child processes.

The thread [Forward SIGTERM to child in Bash][0] contains some information on
doing that for Bash scripts. For very simple scripts that just set up an
environment, I recommend the `exec` approach.

  [0]: http://unix.stackexchange.com/q/146756/73728

## Configuration

You can use `nocrux --edit` to open the `$EDITOR` (defaults to `nano`) with
the nocrux configuration file. The configuration file must be located at
`~/.nocrux/conf` but can also be placed globally in `/etc/nocrux/conf`.

Below is an illustration of the configuration format:

    root ~/.nocrux/run;
    kill_timeout 10;
    include conf.d/*;

    daemon test {
        export PATH=/usr/sbin:$PATH;
        run ~/Desktop/mytestdaemon.sh arg1 "arg 2";
        cwd ~;
        user me;
        group me;
        stdin /dev/null;
        stdout $root/$name.out;
        stderr $stdout;
        pidfile $root/$name.pid;
        signal term TERM;
        signal kill KILL;
        command uptime echo $(($(date +%s) - $(date +%s -r $DAEMON_PIDFILE))) seconds;
        requires daemon1 daemon2;
    }

## Changelog

__v2.0.3__

- Update for Node.py 2
- Add `--sudo` command-line option
- Add `--as <user>` command-line option
- Add support for variable substition in the `daemon { export; }` field
- Add support for custom signals for termination and killing a daemon process
  (see issue #21)
- Add support for custom daemon subcommands that have access to the following
  environment variables: `$DAEMON_PID`, `$DAEMON_PIDFILE`, `$DAEMON_STDOUT`,
  `$DAEMON_STDERR` (see issue #22)
- Fix configuration loading (`run;` may now be preceeded by any other option)
- Fix `-e, --edit` now opens the editor always for the user's file

__v2.0.2__

- fix `nocrux version` command
- add `nocrux edit` command
- order of daemons when referencing them with `all` is now sorted alphabetically

__v2.0.1__

* removed `fn:out`, `fn:err` and `fn:pid` commands (actually already removed in 2.0.0)
* the default `root` config value will now be `/var/run/nocrux` if the
  configuration file is loaded from `/etc/nocrux/conf`
* more sophisticated config file parsing with `nr.parse.strex` module
* update error message hinting to check output of `nocrux <daemon> tail` if
  daemon could not be started

__v2.0.0__

* cli is now `nocrux <daemon> <command>` (switched)
* to specify multiple daemons, the `<daemon>` argument can be a list of
  comma separated daemon names
* configuration file is no longer a Python script
* configuration file must now be located at `~/.nocrux/conf` or
  `/etc/nocrux/conf`
* nocrux can now be installed via Node.py
* add support for defining per-process environment variables

__v1.1.3__

* update `README.md` (corrected example and command-line interface)
* remove unusued `-e, --stderr` argument
* fix `setup.py` (use `py_modules` instead of the invalid `modules` parameter)
* enable running `nocrux.py` directly without prior installation
* add `pid`, `tail`, `tail:out` and `tail:err` subcommands

__v1.1.2__

* add `setup.py` installation script, remove `nocrux` script
* update `README.md` and renamed from `README.markdown`

__v1.1.1__

* close #18: Automatically expand prog ~ before starting process
* fix #17: PID file not deleted after daemon stopped
* close #16: Tail command is counter intuitive
* update output of command-line program
* process exit code is now printed to daemon standard error output file
* fixed stopping multiple daemons when one wasn't running
* implement #10: daemon dependencies

__v1.1.0__

* Renamed to `nocrux`
* Update README and command-line help description

__v1.0.1__

* Add `krugs tail <daemon> [-e/-stderr]` command
* Add special deaemon name `all`
* Fix `krugs restart` command
