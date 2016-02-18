# Krugs - Simple daemon manager <img src="http://i.imgur.com/IJ6EHnq.png"/> <img src="http://i.imgur.com/59R7gD9.png"/>

Krugs is a simple manager for daemon processes. It is easier to use and
deploy than using/writing `init.d` scripts and the Unix `service` command.
Also, Krugs can be used by any user and not just root.

Krugs only works Unix-like systems.

__Configuration__

Krugs is configured with a Python script. This script is imported when
Krugs is loaded. Take a look at the [`krugs_config.py`](krugs_config.py) file
for the configuration template.

To configure a daemon, you write it like this:

```python
Daemon(
  name = 'test',
  bin = expath('~/Desktop/test.sh'),
  args = ['42'],
  user = None,
  group = None,
  login = True,
)
```

__Todo__

* [ ] Code cleanup
* [ ] Support for daemon dependencies
* [ ] Confirm/update Krugs to ensure it works with shells other than Bash

__Requirements__

* Python 3
