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
6. [Axpert Protocol](#axpert-protocol)

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

To see all CLI options.


## Axpert Protocol

The comms protocol is described to some fashion in
[this](doc/axpert_protocol.md) doc


<!-- links -->
[click]: https://click.palletsprojects.com/en/latest/
[click shell completion]: https://click.palletsprojects.com/en/latest/shell-completion/#enabling-completion
