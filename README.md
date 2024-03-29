# Axpert Inverter Interface and Controller

**Table of Content**

1. [Introduction](#introduction)
2. [Requirements](#requirements)
3. [Installation](#installation)
	1. [Into a Python Virtual Environment](#into-a-python-virtual-environment)
	2. [By cloning the repo](#by-cloning-the-repo)
4. [Getting started](#getting-started)

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

## Getting started

Once installed, make sure your venv is activated, then try:

    $ axpert -h

To see all CLI options.

## Axpert Protocol

The comms protocol is described to some fashion in
[this](doc/axpert_protocol.md) doc
