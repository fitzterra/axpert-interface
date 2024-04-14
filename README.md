# Axpert Inverter Interface and Controller

**Table of Content**

1. [Introduction](#introduction)
2. [Requirements](#requirements)
3. [Installation](#installation)
	1. [Into a Python Virtual Environment](#into-a-python-virtual-environment)
	2. [By cloning the repo](#by-cloning-the-repo)
	3. [Setting up `udev` rules](#setting-up-udev-rules)
	4. [Setting up shell completion](#setting-up-shell-completion)
		1. [Bash completion](#bash-completion)
		2. [Zsh completion](#zsh-completion)
		3. [Fish completion](#fish-completion)
5. [Getting started](#getting-started)
6. [Configuration](#configuration)
7. [Query request](#query-request)
8. [Command request](#command-request)
9. [Axpert Protocol](#axpert-protocol)

## Introduction

This package can be used to manage an Axpert (or Voltronix, I understand) type
inverter. It is based on many bits and pieces from all over the interwebs and
Git hubs, and it may or may not work on your version or type of interver, so
YMMV.

This package is installed via Python `pip` and will make the `axpert` command
available for query and managing the inverter.

For now it only supports one inverter via the USB HID interface, but should be
fairly easy to extend for multiple or parallel inverters. I don't have such a
setup, so I;m not able to add support for it right now, but happy for
PR's/MR's.

At the moment this is assumed to run in a Linux environment, so if you're on
Windows, YMMV - happy to get PR's/MR's that will fix things in Windows, but
only if it makes sense an not make it more difficult to support Linux.

## Requirements

* Linux and probably MacOs?. Windows is not supported unless I get
  confirmations or MR's/PRs for Windows support.
* Python 3.8+
* An Axpert or Voltronix type Inverter.

## Installation

### Into a Python Virtual Environment

Use your favourite way to set up a virtual env then inside the venv install
with pip:

    `pip install git+https://github.com/fitzterra/axpert-interface.git`

### By cloning the repo

Close this repo and set up a virtual environment for the repo.

After activating the venv change to the repo dir and run:

    pip install .

### Setting up `udev` rules

This is where we do that ????????????????

### Setting up shell completion

Shell tab completion can be set up for all commands and arguments for the
`axpert` command after [installation](#installation).

Setting up completion for the supported shells are described in the following sections.

Shell completion is done via the [click] library. See [click shell completion] for more info.


#### Bash completion

Add this to `~/.bashrc`:

    eval "$(_AXPERT_COMPLETE=bash_source axpert)"

For faster shell startup, you can write the completion script somewhere and
then source it from `~/.bashrc`. If doing this, you need to update the
completion script every time a new version is installed. Something like:

    _AXPERT_COMPLETE=bash_source axpert > ~/.axpert-completion.bash

Then in you `~/.bashrc`, source it like this:

    . ~/.axpert-completion.bash

#### Zsh completion

Add this to `~/.zshrc`:

    eval "$(_AXPERT_COMPLETE=zsh_source axpert)"

For faster shell startup, you can write the completion script somewhere and
then source it from `~/.zshrc`. If doing this, you need to update the
completion script every time a new version is installed. Something like:

    _AXPERT_COMPLETE=zsh_source axpert > ~/.axpert-completion.zsh

Then in you `~/.zshrc`, source it like this:

    . ~/.axpert-completion.zsh

#### Fish completion

Add this to `~/.config/fish/completions/axpert.fish`:

    (_AXPERT_COMPLETE=fish_source axpert | source

For faster shell startup, you can write the completion script directly to the
completions dir. If doing this, you need to update the
completion script every time a new version is installed. Something like:

    _AXPERT_COMPLETE=fish_source axpert > ~/.config/fish/completions/axpert.fish

## Getting started

Once installed, make sure your venv is activated, then try:

    $ axpert -h

which will look something like:

    Usage: axpert [OPTIONS] COMMAND [ARGS]...

      Axpert Inverter CLI interface.

    Options:
      -c, --config FILE               Config file for any default options.
      -d, --device TEXT               The inverter HID device to connect to.
                                      [default: /dev/hidAxpert]
      -l, --logfile TEXT              Log file path to enable logging. Use - for
                                      stdout or _ for stderr. Disabled by default
      -L, --loglevel [critical|fatal|error|warn|warning|info|debug]
                                      Set the loglevel.  [default: info]
      -h, --help                      Show this message and exit.

    Commands:
      command  Issue the CMD command to the inverter and indicates success or...
      query    Issue the QRY query request to the inverter, returning the...

To see the [config](#configuration) section below for more details on options.

Each command takes it's own `-h` or `--help` arg to get help for that command:

    $ axpert query --help

will print this:

    Usage: axpert.py query [OPTIONS] QRY

      Issue the QRY query request to the inverter, returning the query result.

      To see a list of available QRY arguments, use `list` as QRY argument

    Options:
      -h, --help                     Show this message and exit.
      -u, --units / -nu, --no-units  Add units to any query values that have units
                                     defined.  [default: nu]
      -f, --format [raw|json|table]  Set the output format. The raw option is
                                     standard Python object output
      -P, --pretty / -U, --ugly      Some format option will allow a more readable
                                     (pretty) output. This can be switched on/off
                                     with this option.  [default: U]
      -q, --mqtt / -nq, --no-mqtt    Publish query response as JSON to MQTT server
                                     as configured in config file. Force --no-
                                     units, JSON and --ugly  [default: nq]


## Configuration

Most config option can be supplied as command line arguments, but there are
some that needs to be supplied via a config file.

A config file will be in the [TOML] format which is a very simple config file
format that is very close the INI file format.

Configuration for the app, both from the command line as well as from a config
file, consists of global config options that affect the main app and all sub
commands, and then the sub command specific config.

The global config options are given on the command line before the sub command
name. In the config file, these goes at the top level. For example:

```toml
# This an axpert config file.
# Global options are at the top level.

loglevel = 'debug'
device = '/dev/hidraw1`
```

Sub command configs are in their own __table__ or section. For the `query`
command for example, we can add the MQTT options that can not be supplied on
the command line.

```toml
# This an axpert config file.
# Global options are at the top level.

loglevel = 'debug'
device = '/dev/hidraw1`

[query]
mqtt_host = 'my.mqtt.com'
mqtt_topic = 'my/axpert/topic/%s'
# Don't parse the dev_stat bitstring that is returned by the QPIGS query
parse_dev_stat = false
```

Note that the `mqtt_host` and `mqtt_topic` options are not available on the
command line so they can only supplied in a config file.

The config file can specified using the `--config` or `-c` global command line
option. When no config file is specified, then the following default config
files will be be tried:

* `/etc/axpert.toml` - this is useful for global server defauly config
* `~/.axpert.toml` - this is useful for local user default config

If both files are present, the later will overwrite options from the first.

For both the default config files or one given with the `--config` or `-c`
command line argument, any direct command line args will overwrite any options
specified in the config files.

## Query request

This is used to get information from the inverter such as current status,
default config, etc.

TBCompleted

## Command request

This is to send a change or update command to the inverter.

TBCompleted

## Axpert Protocol

The comms protocol is described to some fashion in
[this](doc/axpert_protocol.md) doc


<!-- links -->
[click]: https://click.palletsprojects.com/en/latest/
[click shell completion]: https://click.palletsprojects.com/en/latest/shell-completion/#enabling-completion
[TOML]: https://toml.io
