__NAME__

`nocrux` - painless per-user daemon manager

__SYNOPSIS__

    nocrux [-h] [-e] {start,stop,restart,status,version,tail}
           [daemon [daemon ...]]

__DESCRIPTION__

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
    -  [test] running test
    -  [test] started (PID: 5887)
    $ nocrux status all
    -  [test] started
    $ nocrux tail test
    This is from my-daemon.sh
    ^C
    $ nocrux stop all
    -  [test] stopped

__DEPENDENCIES__

* Python 3

__EXAMPLES__

Make nocrux available for everyone.

    $ sudo git clone https://github.com/NiklasRosenstein/nocrux.git /opt/nocrux
    $ sudo tail /etc/profile
    # ...
    export PATH="$PATH:/opt/nocrux"

A simple daemon for [Gogs](https://gogs.io/)

    $ cat ~/nocrux_config.py
    register_daemon(
      name = 'gogs',
      prog = expanduser('~/gogs/gogs'),
      args = ['web'],
    )

Run the daemon on startup

    $ crontab -l
    @reboot nocrux start gogs

Show the latest output of the daemon process

    $ nocrux tail gogs

__CHANGELOG__

*v1.1.0*

* Renamed to `nocrux`
* Update README and command-line help description

*v1.0.1*

* Add `krugs tail <daemon> [-e/-stderr]` command
* Add special deaemon name `all`
* Fix `krugs restart` command
