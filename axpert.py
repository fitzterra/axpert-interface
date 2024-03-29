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

import crcmod
import click
from prettytable import PrettyTable

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

        # Return the crc after incrementing each of the reserved bytes by one
        # if they are present.
        return unhexlify(crc_h).replace(b"\x0d", b"\x0e").replace(b"\x28", b"\x29")

    def _sendCommand(self, command):
        """
        Sends the command to the inverter, and returns the response received.

        Args:
            command (str): The command to send.

        Returns:
            The response after removing the leading '(', validating and
            removing the CRC and trailing '\r' if all is well.
            None if an error occurred, with the error info logged.
        """
        try:
            # Encode the command string to a byte string. We need this to
            # calculate the CRC and sending to the device
            cmd_b = command.encode("utf-8")
            # Calculate the CRC as a bytes string
            crc_b = self._calcCRC(cmd_b)

            # Now create the final command to send to the device consisting of
            # the command name, followed by the crc, followed by a CR ('\r')
            command_crc = b"%b%b\r" % (cmd_b, crc_b)

            # Set up a timeout alarm in case the process gets stuck
            signal.signal(signal.SIGALRM, self._timeoutAlarm)
            signal.alarm(DEVICE_TIMEOUT)

            # We write the command in chunks with a delay between chunks. See
            # comment above for TX_CHUNK_SZ and TX_DELAY
            for offset in range(0, len(command_crc), self.TX_CHUNK_SZ):
                time.sleep(self.TX_DELAY)
                chunk = command_crc[offset : offset + self.TX_CHUNK_SZ]
                logger.debug(
                    "Writing max %s bytes to device: %s", self.TX_CHUNK_SZ, chunk
                )
                os.write(self.port, chunk)

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

        logger.debug("Command: %s | Response: %s", command, response)

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
        res = self._sendCommand(qry).decode("utf-8")
        # Now split on spaces for any multi-value results
        res = res.split(" ")

        # Do we have a entity definition for this query?
        ent_def = entities.QUERIES.get(qry, None)
        if ent_def is None:
            raise ValueError(f"No query definition for {qry}")

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


def formatOutput(dat, fmt, pretty):
    """
    Format a Python data structure for output.

    Args:
        dat (dict): This is a dictionary with entity keys and values. The keys
        are expected to exists in entities.ENTITIES.
        fmt (str): Currently one of:
            * 'raw': This indicates no formatting
            * 'json': Return data as a JSON string
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
        indent = 2 if pretty else None
        return json.dumps(dat, indent=indent)

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


@click.command()
@click.help_option("-h", "--help")
@click.option(
    "-d",
    "--device",
    default=DEFAULT_DEV,
    help="The inverter HID device to connect to.",
    show_default=True,
)
@click.option(
    "-q",
    "--query",
    default=None,
    type=click.Choice(entities.QUERIES.keys()),
    help="The query to issue.",
)
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
def cli(device, query, units, fmt, pretty, logfile, loglevel):
    """
    Main CLI interface
    """
    # We need all these args, so @pylint: disable=too-many-arguments

    loggerConfig(logfile, loglevel)

    logger.info("Instantiating inverter device...")
    inv = Axpert(device=device)
    inv.open()
    if query:
        print(formatOutput(inv.query(query, units), fmt, pretty))
    inv.close()


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
