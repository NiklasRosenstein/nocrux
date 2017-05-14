
*nocrux* -- a painless **per-user** daemon manager.

## Installation

Nocrux is developed for unix-like systems and is known to work on
Ubuntu 15.05, Debian Jessie and macOS Sierra. It can be installed via
Pip and Node.py. Requires **CPython 3.4** or above.

    $ nodepy-pm install @NiklasRosenstein/nocrux  # or
    $ pip3 install nocrux

## Command-line Interface

    nocrux version                 (print the version of nocrux and exit)
    nocrux edit                    (edit the nocrux configuration file)
    nocrux all <command>           (apply <command> on all daemons)
    nocrux <daemon(s)> <command>   (apply <command> on the specified daemons)

When specifying multiple daemons on the command-line, they must be a single
argument and separated by a comma, for example `nocrux mongod,nginx,php-fpm stop`.
Below is a list of the available commands.

- `start` -- Start the daemon(s)
- `stop` -- Stop the daemon(s)
- `restart` -- Restart the daemon(s)
- `status` -- Show the status of the daemon(s)

Note that the following commands can only be used with a single daemon.

- `tail`-- Alias for `tail:out`
- `tail:out` -- Shows the tail of the daemons' stdout
- `tail:err` -- Shows the tail of the daemons' stderr
- `pid` -- Print the PID of the daemon (0 if the daemon is not running)

## Daemon termination

*nocrux* can only send SIGTERM (and alternatively SIGKILL if the process
doesn't respond to the previous signal) to the main process that was also
started with *nocrux*. If that process spawns any subprocess, it must take
care of forwarding the signals to the child processes.

The thread [Forward SIGTERM to child in Bash](http://unix.stackexchange.com/q/146756/73728)
contains some information on doing that for Bash scripts. For very simple
scripts that just set up an environment, I recommend the `exec` approach.

## Configuration

The configuration file is loaded from `~/.nocrux/conf` or `/etc/nocrux/conf`
(preferring the former over the latter). The syntax is similar to what you
know from NGinx.

    ## Directory where the default daemon files are stored. Defaults to
    ## /var/run/nocrux if the configuration file is read from /etc/nocrux/conf,
    ## otherwise defaults to ~/.nocrux/run .
    #root ~/.nocrux/run;
    
    ## The timeout after which a process will be killed when it can not
    ## be terminated with SIGINT.
    #kill_timeout 10;

    ## Include all files in the conf.d directory relative to the
    ## configuration file.
    include conf.d/*;

    ## Defines a daemon.
    daemon test {
        run ~/Desktop/mytestdaemon.sh arg1 "arg 2";
        cwd ~;
        export PATH=/usr/sbin:$PATH;
        export MYTESTDAEMON_DEBUG=true;

        ## The user to run start the daemon as. If omitted, the user will
        ## not be changed.
        #user www-data;

        ## The group to run start the daemon as. If omitted, the user will
        ## not be changed.
        #group www-data;

        ## Path to a file to input to stdin.
        #stdin /dev/null;

        ## Path to the file that will capture the daemon's stdout.
        #stdout $root/$name.out;

        ## Path to the file that will capture the daemon's stderr.
        #stderr $stdout;

        ## Path to the file that will be used to store the PID.
        ## Do not change this value until the daemon is stopped again.
        #pidfile $root/$name.pid;

        ## Zero, one or more names of daemons that need to be started
        ## before this daemon can be started.
        #requires daemon1 daemon2;
    }

## Changelog

__v2.0.3__

- support environment variable substition in the `daemon > export` field

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
