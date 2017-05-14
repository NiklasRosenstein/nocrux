
*nocrux* -- a painless **per-user** daemon manager.

## Installation

The *nocrux* daemon manager is available via Pip and Node.py. Minimum version
required is Python 3.4. It has been tested on Ubuntu 15.05 and macOS Sierra.

    $ nodepy-pm install @NiklasRosenstein/nocrux  #or
    $ pip3 install nocrux

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

## Daemon termination

*nocrux* can only send SIGTERM (and alternatively SIGKILL if the process
doesn't respond to the previous signal) to the main process that was also
started with *nocrux*. If that process spawns any subprocess, it must take
care of forwarding the signals to the child processes.

The thread [Forward SIGTERM to child in Bash](http://unix.stackexchange.com/q/146756/73728)
contains some information on doing that for Bash scripts. For very simple
scripts that just set up an environment, I recommend the `exec` approach.

## Changelog

__v2.0.1__

* removed `fn:out`, `fn:err` and `fn:pid` commands (actually already removed in 2.0.0)
* the default `root` config value will now be `/var/run/nocrux` if the
  configuration file is loaded from `/etc/nocrux/conf`

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
