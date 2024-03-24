#!/usr/bin/env python
"""
Interfacing to Axpert type inverters...
"""
# We do sometimes want to catch broad exceptions
#pylint: disable=broad-exception-caught

import os
import time
import signal
import logging
from binascii import unhexlify

import crcmod

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(encoding='utf-8', level=logging.INFO)

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
    # These two clas constant defines the chunk size and delay between chunk
    # transmissions.
    TX_CHUNK_SZ = 8
    TX_DELAY = 0.35  # 350ms seems to work well.

    def __init__(self, connection):
        """
        Instance instantiation

        Args:
            connection (str): One of "serial" or "hid" to indicate the
                connection type

        Raises:
            AssertionError if any args are invalid
        """
        # Validate the connection arg
        assert connection in ('serial', 'hid'),\
            f"Invalid connection '{connection}'. Should be 'serial' or 'hid'"
        self.connection = connection

        # TODO: What does these do?
        self.mode0 = self.mode1 = -1

        # TODO: what does this do?
        #self.load = 0

        # TODO: what does this do?
        self.parrallel_num = 0

        # Will be set by _openUSBPorts as open fd's to the raw HID ports
        self.usb0 = self.usb1 = None

        # The CRC function to be used for Axpert command uses is of the
        # CRC-16/XMODEM variant. Here we create a CRC function using the crcmod
        # package and the predefined xmodem definition.
        self._crc = crcmod.predefined.mkCrcFun('xmodem')

        if connection =='hid':
            # Open hidraw ports
            self._openUSBPorts()
        else:
            self._openSerialPort()

    def _openUSBPorts(self):
        """
        Tries to open the hidraw{0,1} ports and assign the open ports to
        `self.usb0` and `self.usb1` respectively.

        Side Effect:
            Sets `self.usb0` and `self.usb1`

        Raises:
            RuntimeError if either port can not be opened
        """
        logger.info("Opening HIDRAW port(s).")
        # We open the port in raw and non-blocking mode
        flags = os.O_RDWR | os.O_NONBLOCK
        try:
            # The hidraw and usb port designators we want
            for port in [0, 1]:
                # Open the port and assign the open fd to self.usb{port}
                setattr(self, f"usb{port}", os.open(f'/dev/hidraw{port}', flags))
                logger.debug("Port /dev/hidraw%d opened", port)
        except Exception as exc:
            raise RuntimeError('Error opening hidraw usb port') from exc

    def _timeoutAlarm(self, signum, _):
        """
        Method that will be called when the timeout alarm is triggered for
        sending an reading a command from the inverted.

        All we do here is raise a TimeoutError which the sendCommand method
        will then handle as a timeout.
        """

    def _calcCRC(self, val):
        """
        Calculates the CRC for the given value.

        The Axpert Inverter uses xmodem CRC for commands and response and this
        method will calculate the CRC for the given value which may be a
        command to be sent, or a response received.

        Args:
            val (str|bytes): A string or bytes string for which the CRC is to
                be calcualted.

        Returns:
            A bytes string as the CRC for the given input val.
        """
        # Ensure that val is a bytes string
        val_b = val.encode('utf-8') if isinstance(val, str) else val
        assert isinstance(val_b, bytes),\
            f"A str or bytes str is expected for _calcCRC, not {type(val)}"

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

        return unhexlify(crc_h)


    def sendCommand(self, command, device):
        """
        ????????????????
        """
        try:
            # Encode the command string to a byte string. We need this to
            # calculate the CRC and sending to the device
            cmd_b = command.encode('utf-8')
            # Calculate the CRC as a bytes string
            crc_b = self._calcCRC(cmd_b)
            # There is an issue in the Axpert firmware where it mistakenly
            # calculates the POP02 CR as 0xE20B, instead of the correct
            # value of 0xE20A. We correct the crc here for this command
            if command == 'POP02':
                # TODO: Test this... looks like there may be an additional
                # b'\x0d' to be added here in addition to the two bytes below
                crc_b = b'\xe2\x0b'

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
                chunk = command_crc[offset:offset+self.TX_CHUNK_SZ]
                logger.debug(
                    "Writing max %s bytes to device: %s", self.TX_CHUNK_SZ, chunk
                )
                os.write(device, chunk)

            response = b""

            # Read the response until we receive a '\r'
            # NOTE: It seems the TX buffer on the Inverter is also only 8 bytes
            #       in size, so we only get 8 bytes on a read at a time
            #       (although we ask for up to 256 bytes). What this also does
            #       is that the last read we do will be up to 8 bytes, but the
            #       last bytes after the \r will be \x00 bytes. We will remove
            #       these trailing \x00 bytes when we see the \r
            while True:
                time.sleep (0.15)
                r = os.read(device, 256)
                logger.debug("Read from device: %s", r)
                response += r
                if b'\r' in r:
                    # Strip any trailing \x00 bytes - see comment above.
                    response = response.rstrip(b'\x00')
                    break

        except Exception as exc:
            logger.exception("Error reading inverter.")
            if self.connection == "serial":
                # Problem with some USB-Serial adapters, they are sometimes
                # disconnecting, 20 second helps to reconnect at same ttySxx
                time.sleep(20)
                ser.open()
            time.sleep(0.5)
            return ''

        # Reset the timeout alarm
        signal.alarm(0)

        #TODO: Make this log the result instead of printing
        print(f"{command} : {response.decode('utf-8')}")
        return response

    #pylint: disable=too-many-statements,too-many-branches
    def getData(self, command, inverter):
        """
        Issues the `command` to the specific `inverter` and returns the result
        read from the inverter.

        Args:
            command (str): A valid command string. See README for details
            inverter (int): A value of 0 or 1 for the first (hidraw0) or second
                (hidraw1) inverter.

        Raises:
            ???????????

        Returns:
            ????????????????
        """
        # Set the correct usb device port based on the inverter
        device = self.usb0 if inverter==0 else self.usb1

        try:
            data = "{"
            if ( connection == "serial" and ser.isOpen() or connection == "USB" ):
                response = self.sendCommand(command, device)
                if "NAKss" in response or response == '':
                    if connection == "serial":
                        time.sleep(0.2)
                        return ''
                else:
                    response_num = re.sub ('[^0-9. ]','',response)
                if command == "QPGS0":
                    response.rstrip()
                    response_num.rstrip()
                    nums = response_num.split(' ', 99)
                    nums_mode = response.split(' ', 99)
                    if nums_mode[2] == "L":
                        data += "Gridmode0:1"
                        data += ",Solarmode0:0"
                        mode0 = 0
                    elif nums_mode[2] == "B":
                        data += "Gridmode0:0"
                        data += ",Solarmode0:1"
                        mode0 = 1
                    elif nums_mode[2] == "S":
                        data += "Gridmode0:0"
                        data += ",Solarmode0:0"
                        mode0 = 2
                    elif nums_mode[2] == "F":
                        data += "Gridmode0:0"
                        data += ",Solarmode0:0"
                        mode0 = 3
                
                    data += ",The_parallel_num0:" + nums[0]
                    data += ",Serial_number0:" + nums[1]
                    data += ",Fault_code0:" + nums[3]
                    data += ",Load_percentage0:" + nums[10]
                    data += ",Total_charging_current:" + nums[15]
                    data += ",Total_AC_output_active_power:" + nums[17]
                    data += ",Total_AC_output_apparent_power:" + nums[16]
                    data += ",Total_AC_output_percentage:" + nums[18]
                    data += ",Inverter_Status0:" + nums[19]
                    data += ",Output_mode0:" + nums[20]
                    data += ",Charger_source_priority0:" + nums[21]
                    data += ",Max_Charger_current0:" + nums[22]
                    data += ",Max_Charger_range0:" + nums[23]
                    data += ",Max_AC_charger_current0:" + nums[24]
                    data += ",Inverter_mode0:" + str (mode0)
                    parrallel_num = int (nums[0])
                    load = int (nums[17])

                elif command == "QPGS1":
                    response.rstrip()
                    response_num.rstrip()
                    nums = response_num.split(' ', 99)
                    nums_mode = response.split(' ', 99)
                    if nums_mode[2] == "L":
                        data += "Gridmode1:1"
                        data += ",Solarmode1:0"
                        mode1 = 0
                    elif nums_mode[2] == "B":
                        data += "Gridmode1:0"
                        data += ",Solarmode1:1"
                        mode1 = 1
                    elif nums_mode[2] == "S":
                        data += "Gridmode1:0"
                        data += ",Solarmode1:0"
                        mode1 = 2
                    elif nums_mode[2] == "F":
                        data += "Gridmode1:0"
                        data += ",Solarmode1:0"
                        mode1 = 3
                    
                    data += ",The_parallel_num1:" + nums[0]
                    data += ",Serial_number1:" + nums[1]
                    data += ",Fault_code1:" + nums[3]
                    data += ",Load_percentage1:" + nums[10]
                    data += ",Total_charging_current:" + nums[15]
                    data += ",Total_AC_output_active_power:" + nums[17]
                    data += ",Total_AC_output_apparent_power:" + nums[16]
                    data += ",Total_AC_output_percentage:" + nums[18]
                    data += ",Inverter_Status1:" + nums[19]
                    data += ",Output_mode1:" + nums[20]
                    data += ",Charger_source_priority1:" + nums[21]
                    data += ",Max_Charger_current1:" + nums[22]
                    data += ",Max_Charger_range1:" + nums[23]
                    data += ",Max_AC_charger_current1:" + nums[24]
                    data += ",Inverter_mode1:" + str (mode1)
                    parrallel_num = int (nums[0])
                    load = int (nums[17])
                elif command == "QPIGS":
                    response_num.rstrip()
                    nums = response_num.split(' ', 99)
                    data += "Grid_voltage" + str(inverter) + ":" + nums[0]
                    data += ",Grid_frequency" + str(inverter) + ":" + nums[1]
                    data += ",AC_output_voltage" + str(inverter) + ":" + nums[2]
                    data += ",AC_output_frequency" + str(inverter) + ":" + nums[3]
                    data += ",AC_output_apparent_power" + str(inverter) + ":" + nums[4]
                    data += ",AC_output_active_power" + str(inverter) + ":" + nums[5]
                    data += ",Output_Load_Percent" + str(inverter) + ":" + nums[6]
                    data += ",Bus_voltage" + str(inverter) + ":" + nums[7]
                    data += ",Battery_voltage" + str(inverter) + ":" + nums[8]
                    data += ",Battery_charging_current" + str(inverter) + ":" + nums[9]
                    data += ",Battery_capacity" + str(inverter) + ":" + nums[10]
                    data += ",Inverter_heatsink_temperature" + str(inverter) + ":" + nums[11]
                    data += ",PV_input_current_for_battery" + str(inverter) + ":" + nums[12]
                    data += ",PV_Input_Voltage" + str(inverter) + ":" + nums[13]
                    data += ",Battery_voltage_from_SCC" + str(inverter) + ":" + nums[14]
                    data += ",Battery_discharge_current" + str(inverter) + ":" + nums[15]
                    data += ",Device_status" + str(inverter) + ":" + nums[16]
                elif command == "Q1":
                    response_num.rstrip()
                    nums = response_num.split(' ', 99)
                    data += "SCCOkFlag" + str(inverter) + ":" + nums[2]
                    data += ",AllowSCCOkFlag" + str(inverter) + ":" + nums[3]
                    data += ",ChargeAverageCurrent" + str(inverter) + ":" + nums[4]
                    data += ",SCCPWMTemperature" + str(inverter) + ":" + nums[5]
                    data += ",InverterTemperature" + str(inverter) + ":" + nums[6]
                    data += ",BatteryTemperature" + str(inverter) + ":" + nums[7]
                    data += ",TransformerTemperature" + str(inverter) + ":" + nums[8]
                    data += ",GPDAT" + str(inverter) + ":" + nums[9]
                    data += ",FanLockStatus" + str(inverter) + ":" + nums[10]
                    data += ",FanPWM" + str(inverter) + ":" + nums[12]
                    data += ",SCCChargePower" + str(inverter) + ":" + nums[13]
                    data += ",ParaWarning" + str(inverter) + ":" + nums[14]
                    data += ",InverterChargeStatus" + str(inverter) + ":" + nums[16]
                elif command == "QBV":
                    response_num.rstrip()
                    nums = response_num.split(' ', 99)
                    data += "Battery_voltage_compensated" + str(inverter) + ":" + nums[0]
                    data += ",SoC" + str(inverter) + ":" + nums[1]
                else: return ''
                data += "}"

        except Exception as e:
            print(f"error parsing inverter data...: {e}")
            print(f"problem command: {command} : {response}")
            return ''

        return data
