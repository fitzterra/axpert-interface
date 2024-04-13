#!/usr/bin/env python
"""
Interfacing to Axpert type inverters...
"""
# We do sometimes want to catch broad exceptions
# pylint: disable=broad-exception-caught

import os
import sys
import time
import signal
import logging
from binascii import unhexlify
from pprint import pformat
import json
import tomllib

import crcmod
import click
from prettytable import PrettyTable
from paho.mqtt import publish

import entities

# Create a logger
logger = logging.getLogger(__name__)

# The default HID port to connect to. Normally we will have a udev rule that
# will create a symlink to the Axpert device's HID port when it is plugged in.
# This can then be used as default port.
DEFAULT_DEV = "/dev/hidAxpert"

# A constant for how long we wait (in seconds) for sending/receiving from the
# device to complete before we fail with a timeout
DEVICE_TIMEOUT = 10

# This is the default file name we use for the config file
CONFIG_FILE_NAME = "axpert.toml"
# These are the different locations we could have system or user level config
# files. Each of these locations will be examined to see if it is a valid
# config file, and if so, it's config info will be read and applied.
# If the config file exists, but is invalid, an error will be raised.
# NOTE: The config files in this list are read and applied in order, meaning
#       that the later config will overwrite earlier ones. If a config file is
#       supplied on the command line, it will take precedence and the ones in
#       this list will be ignored. Specific command line args will also
#       override any values from these config files.
# NOTE2: Shell type tilde (~) expansion will be attempted if a file name
#        contains one.
CONFIG_FILE_PATHS = [
    f"/etc/{CONFIG_FILE_NAME}",
    f"~/.{CONFIG_FILE_NAME}",
]


def configure(ctx, param, filename=None):
    """
    Sets up default config options from an optional config file.

    See for more info: https://jwodder.github.io/kbits/posts/click-config/

    The config file should be a TOML format (https://toml.io). Any config
    options for the main cli() args should be at the top level, while the
    sub command should have their arguments inside their own table such as
    `[query]` for example.

    Sample axpert.toml:

        # Config file for Axpert interface

        # These are main level config settings that applies to all sub commands
        #device = '/dev/foo'
        logfile = '-'
        #loglevel = 'debug'

        # This is for the query sub command
        [query]
        mqtt = true
        mqtt_host = 'goomba.foo'
        mqtt_topic = 'a/new/topic'

    """
    # We may need the `param` arg later, so @pylint: disable=unused-argument

    # Did we get a config file name?
    if filename:
        # Yes, and in this case that is the only file to consider.
        conf_files = [filename]
        logger.info("Only considering %s file for config.", filename)
    else:
        # No, so we will consider all possible config files.
        conf_files = CONFIG_FILE_PATHS
        logger.info("Considering these files for config: %s", conf_files)

    # Will hold the config options read from the config files.
    config = {}

    for cfile in conf_files:
        try:
            # We will expand a ~ in the file path to the user's home dir
            cfile = os.path.expanduser(cfile)
            with open(cfile, "rb") as f:
                # This update is only on the top level. It will change a
                # `device` entry on the top level, but for the `query` or
                # `command` table definitions in the toml file, these will be
                # completely overridden, and not just updating the sub entires
                # within these tables.
                config.update(tomllib.load(f))
        except FileNotFoundError:
            # If filename was given, then this is an expected config file, and
            # we do not allow failure
            if filename:
                logger.error("Expected config file '%s' not found. Aborting.", filename)
                sys.exit(1)
            # For the others, we can go on to the next file if any
            continue
        except Exception:
            logger.exception("Error opening or parsing config file: %s", cfile)
            sys.exit(1)

    # Set the click context default_map with the default options. These may now
    # be overridden by command line args.
    # TODO: Find a way to have these defaults show up in the --help option as
    # defaults for the different args.
    ctx.default_map = config


class Axpert:
    """
    Axpert controller class
    """

    # It seems the receive buffer on the Inverter only holds 8 bytes
    # at a time since sending more than 8 bytes in one go causing
    # things to break. For this reason, we break the command up in 8
    # byte chunks with a slight delay between transmissions.
    # These two class constant defines the chunk size and delay between chunk
    # transmissions.
    TX_CHUNK_SZ = 8
    TX_DELAY = 0.35  # 350ms seems to work well.

    def __init__(self, device=DEFAULT_DEV):
        """
        Instance instantiation

        Args:
            device (str): The HID device we will connect to. This will usually
                be a device entry in '/dev/` to which this process should have
                read and write access.

        Raises:
            RuntimeError if not able to open `self.device`
            Other possible errors.
        """
        self.device = device
        self.port = None

        # The CRC function to be used for Axpert command uses is of the
        # CRC-16/XMODEM variant. Here we create a CRC function using the crcmod
        # package and the predefined xmodem definition.
        self._crc = crcmod.predefined.mkCrcFun("xmodem")

    def __enter__(self):
        """
        Entry point for context manager
        """
        self.open()
        return self

    def __exit__(self, ex_type, ex_value, ex_traceback):
        """
        Called when the context is destroyed.
        """
        self.close()

    def open(self):
        """
        Tries to open the HID device defined by `self.device` and assign this as
        an open file descriptor to `self.port`.

        Side Effect:
            Sets `self.port`

        Raises:
            RuntimeError if device can not be opened
        """
        logger.info("Opening HIDRAW device: %s.", self.device)
        # We open the port in raw and non-blocking mode
        flags = os.O_RDWR | os.O_NONBLOCK
        try:
            self.port = os.open(self.device, flags)
            logger.debug("Device %s opened", self.device)
        except Exception as exc:
            raise RuntimeError(f"Error opening hid device {self.device}") from exc

    def close(self):
        """
        Closes the port if it is open.

        Call this before exiting the program.
        """
        if self.port:
            logger.info("Closing device.")
            os.close(self.port)
        self.port = None

    def _timeoutAlarm(self, signum, _):
        """
        Method that will be called when the timeout alarm is triggered for
        sending a command and reading it's response from the inverted.

        All we do here is raise a TimeoutError which the sendCommand method
        will then handle as a timeout.
        """
        raise TimeoutError("Timeout waiting for inverter response")

    def _calcCRC(self, val):
        """
        Calculates the CRC for the given value.

        The Axpert Inverter uses xmodem CRC for commands and response and this
        method will calculate the CRC for the given value which may be a
        command to be sent, or a response received.

        Note that there are two "reserved" characters used in the Axpert comms
        protocol:
            * `\r` (0x0d) - used to signal end of the command string
            * '(' (0x28)  - used to signal the start of a response.

        When these characters appears in the calculated CRC it could cause
        parsing issues. It seems the way these inverters deals with these are
        to simply increment the byte by, i.e. 0x0d becomes 0x0e and 0x28
        becomes 0x29.

        This function will apply these rules to ensure the inverter and this
        CRC calculations match up.

        Args:
            val (str|bytes): A string or bytes string for which the CRC is to
                be calculated.

        Returns:
            A bytes string as the CRC for the given input val.
        """
        # Ensure that val is a bytes string
        val_b = val.encode("utf-8") if isinstance(val, str) else val
        assert isinstance(
            val_b, bytes
        ), f"A str or bytes str is expected for _calcCRC, not {type(val)}"

        # Calculate the CRC as a bytes string:
        # 1. Use the self._crc() method to calculate the xmodem CRC for the
        #    command in bytes array format as an integer.
        # 2. Convert this crc integer into a hex string, but then strip off
        #    the '0x' prefix added by hex(), and then ensuring the length is a
        #    multiple of 2
        # 3. Convert this hex string into a bytes string using the unhexlify
        #    function
        crc_h = hex(self._crc(val_b))[2:]
        # This must be an even number of bytes, or else we prefix a 0
        if len(crc_h) % 2:
            crc_h = f"0{crc_h}"

        # Incrementing any of the reserved bytes by one if they are present
        # after converting the hex string to a binary version
        crc = unhexlify(crc_h).replace(b"\x0d", b"\x0e").replace(b"\x28", b"\x29")
        # The final CRC must be 2 bytes, or else we pad to the left with null
        if len(crc) == 1:
            crc = b"\x00" + crc
        return crc

    def _sendRequest(self, request):
        """
        Sends the request to the inverter, and returns the response received.

        Args:
            request (str): The request to send.

        Raises:
            AssertionError if the port is not open
            OSError if there was an error reading or writing the port
            Others that might bubble up from lower levels

        Returns:
            The response after removing the leading '(', validating and
            removing the CRC and trailing '\r' if all is well.
            None if an error occurred, with the error info logged.
        """
        if self.port is None:
            logger.error("Inverter port is not open. Try using open() first.")
            return None

        try:
            # Encode the request string to a byte string. We need this to
            # calculate the CRC and sending to the device
            cmd_b = request.encode("utf-8")
            # Calculate the CRC as a bytes string
            crc_b = self._calcCRC(cmd_b)

            # Now create the final request to send to the device consisting of
            # the request name, followed by the crc, followed by a CR ('\r')
            request_crc = b"%b%b\r" % (cmd_b, crc_b)

            # Set up a timeout alarm in case the process gets stuck
            signal.signal(signal.SIGALRM, self._timeoutAlarm)
            signal.alarm(DEVICE_TIMEOUT)

            # We write the request in chunks with a delay between chunks. See
            # comment above for TX_CHUNK_SZ and TX_DELAY
            for offset in range(0, len(request_crc), self.TX_CHUNK_SZ):
                time.sleep(self.TX_DELAY)
                chunk = request_crc[offset : offset + self.TX_CHUNK_SZ]
                logger.debug(
                    "Writing max %s bytes to device: %s", self.TX_CHUNK_SZ, chunk
                )
                try:
                    # This is a hack to get a round a strange error where the
                    # os.write raises this error:
                    #  OSError: [Errno 22] Invalid argument
                    # if the last chunk to write is a single b'\r'
                    # To get around this, we append a null character to the
                    # bytes to write, which it seems the inverter is fine with.
                    # I noticed that bytes received from the inverter are
                    # always padded with nulls to fill up 8 bytes, so the idea
                    # to add a null comes from there.
                    if chunk == b"\r":
                        chunk = b"\r\x00"
                        logging.info("Adding b'\x00' to chunk: %s", chunk)
                    # Now write it
                    os.write(self.port, chunk)
                except OSError:
                    logger.exception("Error writing to device.")
                    # Reset the timeout alarm
                    signal.alarm(0)
                    # Close the port
                    self.close()
                    return None

            response = b""

            # Read the response until we receive a '\r'
            # NOTE: It seems the TX buffer on the Inverter is also only 8 bytes
            #       in size, so we only get 8 bytes on a read at a time
            #       (although we ask for up to 256 bytes). What this also does
            #       is that the last read we do will be up to 8 bytes, but the
            #       last bytes after the \r will be \x00 bytes. We will remove
            #       these trailing \x00 bytes when we see the \r
            while True:
                time.sleep(0.15)
                r = os.read(self.port, 256)
                logger.debug("Read from device: %s", r)
                response += r
                if b"\r" in r:
                    # Strip any trailing \x00 bytes - see comment above.
                    response = response.rstrip(b"\x00")
                    break

        except Exception:
            logger.exception("Error reading inverter.")
            return None

        # Reset the timeout alarm
        signal.alarm(0)

        logger.debug("Request: %s | Response: %s", request, response)

        # For sanity, validate that the last byte in the response is '\r' and
        # if so, trim it. Indexes into bytes string returns int, so we use ord
        # here to make sure we compare ints to ints.
        if response[-1] != ord(b"\r"):
            logger.error("Response [%s] does not end with '\\r'", response)
            return None
        response = response[:-1]

        # Validate that the CRC matches. The last 2 bytes are the CRC for the
        # response, which is calculated from the full response except the last
        # 2 bytes.
        crc = self._calcCRC(response[:-2])
        if not response[-2:] == crc:
            logger.error(
                "Response [%s] CRC does not match expected CRC: [%s]", response, crc
            )
            return None
        # Strip the CRC
        response = response[:-2]

        # All responses starts with a '('. Validate and then strip it. Indexes
        # into bytes string returns int, so we use ord here to make sure we
        # compare ints to ints.
        # NOTE: we use the hex representation here because using a "(" directly
        # somehow messes up with VIM's bracket matching and then starts new
        # code lines way more indented as they should.
        start_char = b"\x28"
        if not response[0] == ord(start_char):
            logger.error(
                "Response [%s] does not start with expected %s", response, start_char
            )
        response = response[1:]

        return response

    def query(self, qry, add_units=True):
        """
        Sends a query command to the inverter and returns the result.

        ???
        """
        # Send the query and get the returned data as a bytes string. If the
        # result has multiple values, they would be separated by spaces.
        # Also immediately convert to a unicode string for easier usage from
        # here on
        res = self._sendRequest(qry).decode("utf-8")
        # Now split on spaces for any multi-value results
        res = res.split(" ")

        # Do we have a entity definition for this query?
        ent_def = entities.QUERIES.get(qry, None)
        if ent_def is None:
            raise ValueError(f"No query definition for {qry}")

        # The entity definition is in definition is in the 'def' key
        ent_def = ent_def["def"]

        # Is the definition callable, i.e. a function?
        if callable(ent_def):
            # Then call it passing in the result. If result is a one element
            # array, we pass the element directly
            return ent_def(res if len(res) > 1 else res[0])

        # Combine the entity keys list with the results split on spaces into a
        # dict
        res = dict(zip(ent_def, res))
        # Cycle through all entries in this dict and format any values that
        # need formatting
        try:
            for k, v in res.items():
                # Format the value
                val = entities.ENTITIES[k]["fmt"](v)
                # If we need to add units, go see if a unit is defined
                unit = add_units and entities.ENTITIES[k].get("unit", False)
                # If a unit should be added and one is available, reformat to a
                # string and add the unit
                if unit:
                    val = f"{val}{unit}"
                res[k] = val
        except Exception as exc:
            raise RuntimeError(f"Error formatting entity {k}") from exc

        return res

    def command(self, cmd):
        """
        Sends a command to the inverter and returns the result.

        Args:
            cmd (str): The inverter command to send.

        Returns:
            True if the command was accepted, False otherwise
        """
        logger.info("Issuing command '%s'....", cmd)
        # Send the command and get the returned data as a bytes string. If the
        # result has multiple values, they would be separated by spaces.
        # Also immediately convert to a unicode string for easier usage from
        # here on
        res = self._sendRequest(cmd).decode("utf-8")

        if res == "ACK":
            logger.info("Command '%s' completed successfully.", cmd)
            # Command was accepted, return True
            return True

        logger.error("Command '%s' was not accepted. Response: %s", cmd, res)
        return False


def formatOutput(dat, fmt, pretty):
    """
    Format a Python data structure for output.

    Args:
        dat (dict): This is a dictionary with entity keys and values. The keys
            are expected to exists in entities.ENTITIES.
        fmt (str): Currently one of:
            * 'raw': This indicates no formatting
            * 'json': Return data as a compact JSON string unless pretty is
                True
            * 'table': Returns the dat as a pretty formatted table.
        pretty (bool): If True and the format option supports it, the output
            will be pretty formatted.

    Returns:
        The dat input formatted as a string in the desired format.
    """
    if fmt == "raw":
        # If there is no pretty formatting, we return data as a string
        if not pretty:
            return str(dat)
        # Pretty format the output
        return pformat(dat)

    if fmt == "json":
        if not pretty:
            # Most compact output if not pretty
            separators = (",", ":")
            indent = None
        else:
            # If pretty we only need to set indent, and leave separators to
            # None for it to use the default separators.
            separators = None
            indent = 2

        return json.dumps(dat, separators=separators, indent=indent)

    if fmt == "table":
        table = PrettyTable()
        table.field_names = ["key", "desc", "value", "prog"]
        for k, v in dat.items():
            table.add_row(
                [
                    k,
                    entities.ENTITIES[k]["desc"],
                    v,
                    entities.ENTITIES[k].get("prog", ""),
                ]
            )
        table.align = "l"
        table.align["value"] = "r"
        table.align["prog"] = "c"
        return table.get_string()

    raise ValueError(f"Format '{format}' is not supported")


def loggerConfig(logfile, loglevel):
    """
    Sets up output logging.

    Note: This function assumes a logger has already been created and is
    available in the global context as `logger`. This can be done with:

        logger = logging.getLogger(__name__)

    Args:
        logfile (str|None): Path to logfile or None to disable. This could also
            be '-' for stdout or '_' for stderr.
        loglevel (str): One of 'critical', 'fatal', 'error', 'warn', 'warning',
            'info' or 'debug'
    """
    # Set up the correct handler based of the logfile path
    if logfile is None:
        # If logfile is None, we add a NullHandler which makes logging no-op
        handler = logging.NullHandler()
    elif logfile in ("-", "_"):
        # For stdout or stderr we need to add a stream handler
        stream = sys.stdout if logfile == "-" else sys.stderr
        handler = logging.StreamHandler(stream)
    else:
        # We assume it is a valid path and add a file handler
        handler = logging.FileHandler(logfile, encoding="utf-8")

    # Set up the formatter
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    handler.setFormatter(formatter)

    # Add the handler to the logger
    logger.addHandler(handler)

    # Get the log level by converting the level string to a logging level
    # integer and set the level on the handler
    level = logging.getLevelNamesMapping()[loglevel.upper()]
    logger.setLevel(level)


def shellCompleteHelper(ctx, param, incomplete):
    """
    Helper function for shell completion of query and command arguments.

    This is called if shell completion has been installed and the <tab> is
    pressed after the `query` or `command` arguments.

    See: https://click.palletsprojects.com/en/latest/shell-completion/#overriding-value-completion
    for more info.

    Args:
        ctx (obj): The current command context.
        param (click.Argument): The current parameter requesting completion.
        incomplete (str): The partial word that is being completed. May be an
            empty string if no characters have been entered yet.

    Returns:
        A list of strings that matches the incomplete arg for the given
        parameter.
    """
    # We do not use the ctx arg now @pylint: disable=unused-argument

    # Set the source for completions from the param
    src = entities.QUERIES if param.name == "qry" else entities.COMMANDS

    # We also have a 'list' arg to either 'query' or 'command' args, but list
    # is not a key in either the QUERIES or COMMANDS dict. To allow the 'list'
    # arg to be considered for completion, we create a new dict with 'list' as
    # the first element, and the src dict keys as the remaining elements
    src = ["list"] + list(src)

    # Return all keys in the given source based on the incomplete arg. Note
    # that startswith() will always match if the starts with string is ''
    return [opt for opt in src if opt.startswith(incomplete)]


@click.help_option("-h", "--help")
@click.group(invoke_without_command=True)
@click.option(
    "-c",
    "--config",
    type=click.Path(dir_okay=False),
    default=None,
    callback=configure,
    is_eager=True,
    expose_value=False,
    help="Config file for any default options.",
    show_default=True,
)
@click.option(
    "-d",
    "--device",
    default=DEFAULT_DEV,
    help="The inverter HID device to connect to.",
    show_default=True,
)
@click.option(
    "-l",
    "--logfile",
    default=None,
    help="Log file path to enable logging. Use - for stdout or _ for stderr. Disabled by default",
)
@click.option(
    "-L",
    "--loglevel",
    default="info",
    type=click.Choice(
        # We get all the available level names where the level is greater than
        # 0 (NOTSET) and convert them to lowercase names as the level choices
        [n.lower() for n, l in logging.getLevelNamesMapping().items() if l > 0]
    ),
    show_default=True,
    help="Set the loglevel.",
)
@click.pass_context
def cli(ctx, device, logfile, loglevel):
    """
    Axpert Inverter CLI interface.
    """
    # ensure that ctx.obj exists and is a dict (in case `cli()` is called
    # by means other than the `if` block below)
    ctx.ensure_object(dict)
    # Pass this through so the sub commands can open the inverter
    ctx.obj["device"] = device

    loggerConfig(logfile, loglevel)

    logger.info("Instantiating inverter device...")


@cli.command()
@click.help_option("-h", "--help")
@click.argument("qry", shell_complete=shellCompleteHelper)
@click.option(
    "-u/-nu",
    "--units/--no-units",
    default=False,
    show_default=True,
    help="Add units to any query values that have units defined.",
)
@click.option(
    "-f",
    "--format",
    "fmt",  # The format name is a reserved word so we pass it as 'fmt'
    default="raw",
    type=click.Choice(("raw", "json", "table")),
    help="Set the output format. The raw option is standard Python object output",
)
@click.option(
    "-P/-U",
    "--pretty/--ugly",
    default=False,
    show_default=True,
    help="Some format option will allow a more readable (pretty) output. "
    "This can be switched on/off with this option.",
)
@click.option(
    "-q/-nq",
    "--mqtt/--no-mqtt",
    default=False,
    show_default=True,
    help="Publish query response as JSON to MQTT server as configured in "
    "config file. Force --no-units, JSON and --ugly",
)
@click.pass_context
def query(
    ctx,
    qry,
    units,
    fmt,
    pretty,
    mqtt,
):
    """
    Issue the QRY query request to the inverter, returning the query result.

    To see a list of available QRY arguments, use `list` as QRY argument
    """
    # pylint: disable=too-many-arguments

    # TODO: add some logging here

    # Show available queries if required
    if qry.lower() == "list":
        print("\nAvailable queries:")
        table = PrettyTable()
        table.field_names = ["QRY", "Description"]
        for k, v in entities.QUERIES.items():
            table.add_row([k, v["info"]])
        table.align = "l"
        print(table)
        return

    # Validate that the qry arg is valid
    if qry not in entities.QUERIES:
        print(
            f"\nInvalid query request '{qry}'. Use `list` as QRY arg for "
            "a list of available queries, or try -h\n"
        )
        sys.exit(1)

    # Send to MQTT?
    if mqtt:
        # There are no options to set the MQTT host, etc from the command line.
        # These are expected to be in a toml config file in the [query] table,
        # which we will then get from the ctx.default_map.
        # If no config file was given however, then ctx.default_map may be
        # None. To make things easier for the fetching of the info below, we
        # will set default_map to an empty dict if it is None so the
        # `.get(...)` below does not fail prematurely.
        if ctx.default_map is None:
            ctx.default_map = {}
        # Now fetch the values.
        mqtt_host = ctx.default_map.get("mqtt_host", None)
        mqtt_topic = ctx.default_map.get("mqtt_topic", None)
        if not all((mqtt_host, mqtt_topic)):
            logger.error(
                "Either MQTT host or topic not defined in config file. Please fix and try again"
            )
            sys.exit(1)
        # The topic may contain '%s' which means we need to interpolate the qry
        # arg
        if r"%s" in mqtt_topic:
            mqtt_topic = mqtt_topic % qry

        logger.debug("Publishing to MQTT, so forcing --no-units, JSON and --ugly.")
        logger.info("Publishing via MQTT to %s on topic '%s'", mqtt_host, mqtt_topic)
        # These are the defaults for units and format when publishing to MQTT.
        units = pretty = False
        fmt = "json"

    # Instantiate an Axpert instance and send the query
    device = ctx.obj["device"]
    with Axpert(device=device) as inv:
        res = formatOutput(inv.query(qry, units), fmt, pretty)

    if not mqtt:
        print(res)
        return

    logger.debug("MQTT: host=%s, topic=%s", mqtt_host, mqtt_topic)
    try:
        publish.single(mqtt_topic, res, hostname=mqtt_host)
        logger.info("MQTT published %s: %s", mqtt_topic, res)
    except Exception:
        logger.exception("Error publishing to MQTT host: %s", mqtt_host)
        sys.exit(1)


@cli.command()
@click.help_option("-h", "--help")
@click.pass_context
def version(ctx):
    """
    Shows the current version number and then exits.
    """
    # pylint: disable=unused-argument,import-outside-toplevel

    # This makes use of Python 3.8+ importlib.metadata function to get the
    # version number from setup.py.
    # See the 5th option here:
    # https://packaging.python.org/en/latest/guides/single-sourcing-package-version/

    from importlib import metadata

    try:
        ver = metadata.version("axpert-interface")
    except metadata.PackageNotFoundError:
        # This error means the axpert-interface package is not known, so we
        # assume we are in a development version.
        # NOTE that this will also be the case if the package name is changed,
        # so be careful about that.
        ver = "_development_"

    print(f"\nVersion: v{ver}\n")


@cli.command()
@click.help_option("-h", "--help")
@click.argument("cmd", shell_complete=shellCompleteHelper)
@click.argument("arg", required=False, nargs=-1)
@click.pass_context
def command(ctx, cmd, arg):
    """
    Issue the CMD command to the inverter and indicates success or failure.

    To get a list of available commands, use 'list' for CMD.
    Some commands takes additional arguments, and these should be supplied as
    ARG to the CMD.
    """
    # We may refactor later, but for now
    # pylint: disable=too-many-branches,too-many-statements,too-many-locals

    logger.debug("Processing command '%s' with arg '%s'", cmd, arg)

    # Show a list of commands?
    if cmd.lower() == "list":
        print("\nAvailable commands:")
        table = PrettyTable()
        table.field_names = ["CMD", "Description", "Prog"]
        for k, v in entities.COMMANDS.items():
            table.add_row([k, v["info"], v.get("prog", "")])
        table.align = "l"
        print(table)
        return

    # Get the command definition, or None if invalid cmd
    cmd_def = entities.COMMANDS.get(cmd, None)
    if cmd_def is None:
        print(
            f"\nInvalid command request '{cmd}'. Use `list` as CMD arg for "
            "a list of available commands, or try -h\n"
        )
        sys.exit(1)

    # Do the arg count match the expected count?
    if len(cmd_def["args"]) != len(arg):
        print(
            f"\nExpected {len(cmd_def['args'])} argument(s), for {cmd} "
            f"but got {len(arg)}: {arg}. Try 'list' or -h.\n"
        )
        sys.exit(1)

    # Convert the args using the args conversion functions
    args = []
    for conv, val in zip(cmd_def["args"], arg):
        if conv is not None:
            try:
                logger.debug("Attempting argument conversion using %s(%s)", conv, val)
                args.append(conv(val))
            except ValueError as exc:
                print(f"\nArgument error: {exc}. Try 'list' or -h\n")
                sys.exit(1)
        else:
            args.append(val)

    # Do we have a validation definition?
    # NOTE: If available, we apply it after the arg conversions
    validate = cmd_def.get("validate", None)
    if validate is not None:
        if len(validate) != len(args):
            print(
                f"\nExpected {len(args)} validation(s), for {cmd} "
                f"but got {len(validate)}. Seems to be a definition error.\n"
            )
            sys.exit(1)
        # Validate each arg with the corresponding validation function,
        # including the original arg for error reporting if validation fails.
        for v, a, o_a in zip(validate, args, arg):
            if v is None:
                continue
            # The validation rule is expected to be callable.
            if not v(a):
                print(f"\nValidation for argument '{o_a}' failed. Try 'list' or -h.\n")
                sys.exit(1)

    # For convenience, if args is only one element, we pop it out of the list
    # as a single arg
    if len(args) == 1:
        args = args.pop()

    logger.debug("Args converted to: '%s'", args)

    # Now, if the entity definition command is a callable, we call it, passing
    # it args, and this will give us the command mnemonic to send to the
    # inverter.
    cmd_f = cmd_def["cmd"]
    if callable(cmd_f):
        logger.debug("Attempting to generate mnemonic with %s(%s)", cmd_f, args)
        cmd_f = cmd_f(args)

    logger.debug("Final mnemonic to send: %s", cmd_f)

    # If the command is disabled, we just log that here and return
    if cmd_def.get("disabled", False):
        print(f"Command {cmd} is hard disabled. Not sending.")
        return
    # Instantiate an Axpert instance and send the command
    device = ctx.obj["device"]
    with Axpert(device=device) as inv:
        res = inv.command(cmd_f)

    if res:
        print(f"Successfully completed command: {cmd} {arg} as {cmd_f}")
    else:
        print(f"Command '{cmd} {arg}' failed. See log for details.")
        sys.exit(1)


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
