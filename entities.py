"""
This module defines the various entities that make up all the parameters and
settings for the inverter.
"""

import re


def parseDeviceFlags(flags):
    """
    Parses the device flags returned by the QFLAG query.

    Flags are either enabled or disabled. The table below show the available
    flag indicators, the meaning of the flag, the key we use to return in the
    dict for each flag, and the program number on the Inverter itself:

    flag | meaning                           | key               | prog
    ---- + --------------------------------- + ----------------- + ----
      a  | alarm                             |  alarm_act        | 18
      b  | overload bypass                   |  ovrl_bypass      | 23
      j  | power saving                      |  pwr_save         |
      k  | lcd home after 1 min              |  lcd_rtn          | 19
      u  | overload restart                  |  ovrl_rstrt       |
      v  | over temperature restart          |  ovr_tmp_rstrt    |
      x  | backlight on                      |  back_light       | 20
      y  | alarm on primary source interrupt |  alrm_pri_src_off | 23
      z  | fault code record                 |  flt_code_rec     | 25

    Args:
        flags (str): The device as a string in the format 'ExxxxDxxx' where the
            flags following the 'E' means enabled, and those following the 'D'
            means disabled.

    Raises:
        RuntimeError if an unknown flag is present

    Returns:
        Returns a dictionary for each of the flags above using the indicated
        key as the dict key, and a bool value of True or False to indicate
        enabled or disabled respectively. The keys will match entity
        definitions in the ENTITIES dictionary
    """
    # Build a flag key lookup dict from the entities marked as flags in
    # ENTITIES.
    # It will look something like this:
    # {
    #   "a": "alarm_act",
    #   "b": "ovrl_bypass",
    #   "j": "pwr_save",
    #   ....
    # }
    flag_key = {e["flag"]: k for k, e in ENTITIES.items() if "flag" in e}

    # The return dict we will complete from the flags
    res = {}

    # We will set the state from the 'E' or 'D' read from the flags string
    state = None
    for f in flags:
        # Set the state for the next flags
        if f in ("E", "D"):
            state = f == "E"  # True if Enabled, False for Disabled
            continue
        # Get the key
        key = flag_key.get(f)
        if not key:
            raise RuntimeError(f"Unknown flag '{f}' in QFLAG output: '{flags}")
        # Add the flag with the correct state to results dict
        res[key] = state

    return res


def parseWarnState(stat):
    """
    Parses the warning status indicators from the QPIWS query.

    This is a string of 32 0's and 1's indicating the status of the various
    warning indicators.

    The warning indicators are all included in the ENTITIES dict, and can be
    identified by the 'warn_ind' key present in the entity. They keys have
    values that indicate the index into the stat string for the specific
    indicator.

    Args:
        stat (str): A 32 char string of 0 and/or 1 indicators of various
            statuses.

    Returns:
        A dict with keys being the entity key from ENTITIES for each indicator
        and the value being True or False depending if the status is active or
        not.
    """
    # Build a state key list from the entities marked as warning indicators in
    # ENTITIES. The list is ordered by the warn_ind values
    # It will look something like this:
    # ["wi_res1", "wi_inv_fault", "wi_bus_ovr", "wi_bus_und",...]
    # TODO: We're relying on the order of values in the dict instead of sorting
    #       - this should be save in Python 3 onwards.
    state_k = [k for k, e in ENTITIES.items() if "warn_ind" in e]

    # Map the 1's and 0's in stat to a list of booleans
    state_v = [bool(int(v)) for v in stat]

    # Zip em together and returns as a dict.
    return dict(zip(state_k, state_v))


# Some pre-compiled regexes for validation, etc. These are the search function
# for the regexes, so use them like IS_VOLTAGE('12.3') for example.
IS_VOLTAGE = re.compile(r"^\d{2}\.\d$").search

# Device mode lookup table for QMOD
DEVICE_MODE = {
    "P": "Power on mode",
    "S": "Standby mode",
    "L": "Line Mode",
    "B": "Battery mode",
    "F": "Fault mode",
    "H": "Power saving Mode",
}

# TODO: Proper documentation
ENTITIES = {
    "dev_prot_id": {"desc": "Device protocol ID", "fmt": str, "unit": None},
    "dev_serial": {"desc": "Device serial number", "fmt": str, "unit": None},
    "fw_ver": {"desc": "Main CPU firmware version", "fmt": str, "unit": None},
    "fw2_ver": {"desc": "Additional CPU firmware version", "fmt": str, "unit": None},
    # ===== Start Device rating entities: QPIRI ========
    "grid_rate_v": {
        "desc": "Grid rating voltage",
        "fmt": float,
        "unit": "V",
    },
    "grid_rate_c": {
        "desc": "Grid rating current",
        "fmt": float,
        "unit": "A",
    },
    "ac_out_rate_v": {
        "desc": "AC output rating ",
        "fmt": float,
        "unit": "V",
    },
    "ac_out_rate_f": {
        "desc": "AC output rating frequency",
        "fmt": float,
        "unit": "Hz",
    },
    "ac_out_rate_c": {
        "desc": "AC output rating current",
        "fmt": float,
        "unit": "A",
    },
    "ac_out_rate_apar_p": {
        "desc": "AC output rating apparent power",
        "fmt": int,
        "unit": "VA",
    },
    "ac_out_rate_act_p": {
        "desc": "AC output rating active power",
        "fmt": int,
        "unit": "W",
    },
    "bat_rate_v": {
        "desc": "Battery rating voltage",
        "fmt": float,
        "unit": "V",
    },
    "bat_util_fb_v": {
        # Note in the PDF doc this is called `Battery re-charge voltage`, but
        # in my Inverter manual this is the point where input falls back to
        # utility when in Solar 1st, or SBU mode (prog 01)
        "desc": "Battery voltage point for utility fallback",
        "fmt": float,
        "unit": "V",
        "prog": "12",
    },
    "bat_und_v": {
        "desc": "Battery under voltage (low DC cut-off)",
        "fmt": float,
        "unit": "V",
        "prog": "29",
    },
    "bat_bulk_v": {
        "desc": "Battery bulk charging voltage",
        "fmt": float,
        "unit": "V",
        "prog": "26",
    },
    "bat_flt_v": {
        "desc": "Battery float charging voltage",
        "fmt": float,
        "unit": "V",
        "prog": "27",
    },
    "bat_type": {
        "desc": "Battery type",
        "fmt": lambda v: ("AGM", "Flooded", "User")[int(v)],
        "unit": None,
        "prog": "05",
    },
    "ac_chg_max_c": {
        "desc": "AC max charging current",
        "fmt": int,
        "unit": "A",
    },
    "chg_max_c": {
        "desc": "Max charging current total",
        "fmt": int,
        "unit": "A",
        "prog": "02",
    },
    "ac_in_range_v": {
        "desc": "AC input voltage range",
        "fmt": lambda v: ("Appliance", "UPS")[int(v)],
        "unit": None,
        "prog": "03",
    },
    "out_src_pri": {
        "desc": "Output source priority",
        "fmt": lambda v: ("Utility 1st", "Solar 1st", "SBU 1st")[int(v)],
        "unit": None,
        "prog": "01",
    },
    "chg_src_pri": {
        "desc": "Charge source priority",
        "fmt": lambda v: ("Utility 1st", "Solar 1st", "Sol+Util", "Sol Only")[int(v)],
        "unit": None,
        "prog": "16",
    },
    "para_max_num": {
        "desc": "Parallel max num",
        # Seems for non parallel Inverter this return just '-'
        "fmt": lambda v: v if v == "-" else int(v),
        "unit": None,
    },
    "inv_type": {
        "desc": "Inverter type",
        "fmt": lambda v: {"00": "Grid tie", "01": "Off grid", "10": "Hybrid"}[v],
        "unit": None,
    },
    "topology": {
        "desc": "Topology",
        "fmt": lambda v: ("No Transformer", "Transformer")[int(v)],
        "unit": None,
    },
    "out_mode": {
        "desc": "Output mode",
        "fmt": lambda v: ("Single", "Parallel", "Ph1/3", "Ph2/3", "Ph3/3")[int(v)],
        "unit": None,
    },
    "bar_ret_v": {
        "desc": "Battery voltage return to solar/battery (0=full)",
        "fmt": float,
        "unit": "V",
        "prog": "13",
    },
    "pv_para_ok": {
        "desc": "PV OK condition for parallel",
        "fmt": lambda v: ("PV on one", "PV on all")[int(v)],
        "unit": None,
    },
    "pv_p_bal": {
        "desc": "PV power balance",
        "fmt": lambda v: ("PV max C", "PV max sum P")[int(v)],
        "unit": None,
    },
    # ===== End Device Rating entities ======
    # ===== Flags Start ======
    "alarm_act": {
        "desc": "Alarm enabled",
        "prog": "18",
        "flag": "a",
    },
    "ovrl_bypass": {
        "desc": "Overload bypass",
        "prog": "23",
        "flag": "b",
    },
    "pwr_save": {
        "desc": "Power Saving",
        "prog": "",
        "flag": "j",
    },
    "lcd_rtn": {
        "desc": "LCD return to home screen after 1 min",
        "prog": "19",
        "flag": "k",
    },
    "ovrl_rstrt": {
        "desc": "Overload restart",
        "prog": "",
        "flag": "u",
    },
    "ovr_tmp_rstrt": {
        "desc": "Over temperature restart",
        "prog": "",
        "flag": "v",
    },
    "back_light": {
        "desc": "Backlight on",
        "prog": "20",
        "flag": "x",
    },
    "alrm_pri_src_off": {
        "desc": "Alarm on primary source interrupt",
        "prog": "23",
        "flag": "y",
    },
    "flt_code_rec": {
        "desc": "Fault code record",
        "prog": "25",
        "flag": "z",
    },
    # ==== Flags end ====
    # ==== Start device status entities ====
    "grid_v": {
        "desc": "Grid voltage",
        "fmt": float,
        "unit": "V",
    },
    "grid_f": {
        "desc": "Grid frequency",
        "fmt": float,
        "unit": "Hz",
    },
    "ac_out_v": {
        "desc": "AC output voltage ",
        "fmt": float,
        "unit": "V",
    },
    "ac_out_f": {
        "desc": "AC output frequency",
        "fmt": float,
        "unit": "Hz",
    },
    "ac_out_apar_p": {
        "desc": "AC output apparent power",
        "fmt": int,
        "unit": "VA",
    },
    "ac_out_act_p": {
        "desc": "AC output active power",
        "fmt": int,
        "unit": "W",
    },
    "out_load_perc": {
        "desc": "Output load percentage",
        "fmt": int,
        "unit": "%",
    },
    "bus_v": {
        "desc": "Bus voltage",
        "fmt": int,
        "unit": "V",
    },
    "bat_v": {
        "desc": "Battery voltage",
        "fmt": float,
        "unit": "V",
    },
    "bat_chg_c": {
        "desc": "Battery charging current",
        "fmt": float,
        "unit": "A",
    },
    "bat_cap": {
        "desc": "Battery capacity",
        "fmt": int,
        "unit": "%",
    },
    "inv_temp": {"desc": "Inverter heat sink temperature", "fmt": int, "unit": "°C"},
    "pv_bat_cur": {"desc": "PV input current for battery", "fmt": int, "unit": "A"},
    "pv_in_v": {"desc": "PV input voltage", "fmt": float, "unit": "V"},
    "bat_v_scc": {"desc": "Battery voltage from SCC", "fmt": float, "unit": "V"},
    "bat_dchg_c": {"desc": "Battery discharge current", "fmt": int, "unit": "A"},
    "dev_stat": {
        "desc": "Device status",
        # TODO: This is string that needs to be parsed
        "fmt": str,
        "unit": None,
    },
    "pv_power": {"desc": "PV output power", "fmt": int, "unit": "W"},
    # There are 3 additional values that are returned that does not seem to be
    # documented anywhere, so we add them here as unknown for now.
    "unkwn_1": {"desc": "Unknown param 1", "fmt": str, "unit": None},
    "unkwn_2": {"desc": "Unknown param 2", "fmt": str, "unit": None},
    "unkwn_3": {"desc": "Unknown param 3", "fmt": str, "unit": None},
    # ==== End device status entities ====
    "dev_mode": {
        "desc": "Device mode",
        "fmt": lambda v: DEVICE_MODE.get(v) or f"Unknown {v}",
        "unit": None,
    },
    # ====== Start of warning indicators ======
    # The "warn_ind" key is the position of this indicator in the list
    "wi_res1": {"desc": "Reserved", "warn_ind": 0},
    "wi_inv_fault": {"desc": "Inverter Fault", "warn_ind": 1},
    "wi_bus_ovr": {"desc": "Bus over voltage Fault", "warn_ind": 2},
    "wi_bus_und": {"desc": "Bus under voltage Fault", "warn_ind": 3},
    "wi_bus_soft_fail": {"desc": "Bus soft fail", "warn_ind": 4},
    "wi_line_fail": {"desc": "Line Fail Warning", "warn_ind": 5},
    "wi_opv_short": {"desc": "OPV Short Warning", "warn_ind": 6},
    "wi_inv_v_lo": {"desc": "Inverter Voltage too low Fault", "warn_ind": 7},
    "wi_inv_v_hi": {"desc": "Inverter Voltage too high Fault", "warn_ind": 8},
    "wi_ovr_temp": {"desc": "Over temperature Warn/Fault", "warn_ind": 9},
    "wi_fan_lock": {"desc": "Fan locked Warn/Fault", "warn_ind": 10},
    "wi_bat_v_hi": {"desc": "Battery voltage hight Warn/Fault", "warn_ind": 11},
    "wi_lo_alrm": {"desc": "Battery low alarm Warn", "warn_ind": 12},
    "wi_res2": {"desc": "Reserved", "warn_ind": 13},
    "wi_bat_und_off": {"desc": "Battery under shutdown Warning", "warn_ind": 14},
    "wi_res3": {"desc": "Reserved", "warn_ind": 28},
    "wi_ovr_load": {"desc": "Overload", "warn_ind": 16},
    "wi_eeprom_fault": {"desc": "EEPROM fault Warn", "warn_ind": 17},
    "wi_inv_ovr_c": {"desc": "Inverter over current Fault", "warn_ind": 18},
    "wi_inv_soft_fail": {"desc": "Inverter soft fail Fault", "warn_ind": 19},
    "wi_self_tst_fail": {"desc": "Self test fail Fault", "warn_ind": 20},
    "wi_op_dc_v_ovr": {"desc": "Output DC voltage over Fault", "warn_ind": 21},
    "wi_bat_open": {"desc": "Battery open Fault", "warn_ind": 22},
    "wi_c_sen_fail": {"desc": "Current sensor fail Fault", "warn_ind": 23},
    "wi_bat_short": {"desc": "Battery short Fault", "warn_ind": 24},
    "wi_pwr_limit": {"desc": "Power limit Warning", "warn_ind": 25},
    "wi_pv_v_hi": {"desc": "PV voltage high Warning", "warn_ind": 26},
    "wi_mppt_ovr_f": {"desc": "MPPT overload fault Warning", "warn_ind": 27},
    "wi_mppt_ovr_w": {"desc": "MPPT overload Warning", "warn_ind": 28},
    "wi_bat_2_lo": {"desc": "Battery too low to charge Warn", "warn_ind": 29},
    "wi_res4": {"desc": "Reserved", "warn_ind": 30},
    "wi_res5": {"desc": "Reserved", "warn_ind": 31},
    # ====== End of warning indicators ======
    # ====== Start of default settings values (QDI) ====
    # NOTE: some of the QDI values are already defined above, so these are only
    # the ones not defined yet.
    "chg_float_v": {
        "desc": "Charging float voltage",
        "fmt": float,
        "unit": "V",
    },
    "chg_bulk_v": {
        "desc": "Charging bulk voltage",
        "fmt": float,
        "unit": "V",
    },
    "alarm_en": {"desc": "Alarm enabled", "fmt": lambda v: bool(int(v)), "unit": None},
    "pwr_save_en": {
        "desc": "Power saving enabled",
        "fmt": lambda v: bool(int(v)),
        "unit": None,
    },
    "ovld_rstr_en": {
        "desc": "Overload restart enabled",
        "fmt": lambda v: bool(int(v)),
        "unit": None,
    },
    "ovr_temp_rstr_en": {
        "desc": "Over temperature restart enabled",
        "fmt": lambda v: bool(int(v)),
        "unit": None,
    },
    "lcd_blght_en": {
        "desc": "LCD backlight enabled",
        "fmt": lambda v: bool(int(v)),
        "unit": None,
    },
    "alrm_pri_src_int_en": {
        "desc": "Alarm on for primary source interrupt enabled",
        "fmt": lambda v: bool(int(v)),
        "unit": None,
    },
    "flt_code_rec_en": {
        "desc": "Fault code recording enabled",
        "fmt": lambda v: bool(int(v)),
        "unit": None,
    },
    "ovrl_bypass_en": {
        "desc": "Overload bypass enabled",
        "fmt": lambda v: bool(int(v)),
        "unit": None,
    },
    "lcd_rtn_en": {
        "desc": "LCD return to home page after 1 min enabled",
        "fmt": lambda v: bool(int(v)),
        "unit": None,
    },
}

# These are all the queries supported currently. The format is a dict with keys
# being the query acronym and values a dict with 'def' and 'info' keys. The
# 'info' key is used to show information about what the query does. The 'def'
# key value can be one of:
#   * A list of entity keys making up the result from the query. This list must
#     match the values as returned by the query when sent to the inverter, in
#     the same order as returned.
#     The query mechanist will take this list one at a time, find it's entity
#     definition in ENTITIES, and apply the result value to the formatting
#     function to format the returned value. The entity keys and formatted
#     values will then be added to a dict as the result for the query.
#   * A callable that will parse or format the result. If a callable, it will
#     be called passing in the query result as only arg, and the return from
#     the callable will be the result returned.
# The keys in this dict is also used as the choices list for the CLI -q
# argument
QUERIES = {
    "QPI": {"def": ["dev_prot_id"], "info": "Get device protocol ID."},
    "QID": {"def": ["dev_serial"], "info": "Get device serial number."},
    "QVFW": {"def": ["fw_ver"], "info": "Get main firmware version."},
    "QVFW2": {"def": ["fw2_ver"], "info": "Get secondary firmware version."},
    "QPIRI": {
        "def": [
            "grid_rate_v",
            "grid_rate_c",
            "ac_out_rate_v",
            "ac_out_rate_f",
            "ac_out_rate_c",
            "ac_out_rate_apar_p",
            "ac_out_rate_act_p",
            "bat_rate_v",
            "bat_util_fb_v",
            "bat_und_v",
            "bat_bulk_v",
            "bat_flt_v",
            "bat_type",
            "ac_chg_max_c",
            "chg_max_c",
            "ac_in_range_v",
            "out_src_pri",
            "chg_src_pri",
            "para_max_num",
            "inv_type",
            "topology",
            "out_mode",
            "bar_ret_v",
            "pv_para_ok",
            "pv_p_bal",
        ],
        "info": "Rate and current settings configuration.",
    },
    "QFLAG": {"def": parseDeviceFlags, "info": "Report various device status flags."},
    "QPIGS": {
        "def": [
            "grid_v",
            "grid_f",
            "ac_out_v",
            "ac_out_f",
            "ac_out_apar_p",
            "ac_out_act_p",
            "out_load_perc",
            "bus_v",
            "bat_v",
            "bat_chg_c",
            "bat_cap",
            "inv_temp",
            "pv_bat_cur",
            "pv_in_v",
            "bat_v_scc",
            "bat_dchg_c",
            "dev_stat",
            "unkwn_1",
            "unkwn_2",
            "pv_power",
            "unkwn_3",
        ],
        "info": "Show current general status information.",
    },
    "QMOD": {"def": ["dev_mode"], "info": "Show the current device mode."},
    "QPIWS": {"def": parseWarnState, "info": "Show all warning statuses."},
    "QDI": {
        "def": [
            "ac_out_v",
            "ac_out_f",
            "ac_chg_max_c",
            "bat_und_v",
            "chg_float_v",
            "chg_bulk_v",
            "bat_util_fb_v",
            "chg_max_c",
            "ac_in_range_v",
            "out_src_pri",
            "chg_src_pri",
            "bat_type",
            "alarm_en",
            "pwr_save_en",
            "ovld_rstr_en",
            "ovr_temp_rstr_en",
            "lcd_blght_en",
            "alrm_pri_src_int_en",
            "flt_code_rec_en",
            "ovrl_bypass_en",
            "lcd_rtn_en",
            "out_mode",
            "bar_ret_v",
            "pv_para_ok",
            "pv_p_bal",
        ],
        "info": "Show default settings.",
    },
    "QMCHGCR": {
        "def": str,
        "info": "Show battery charging currents that may be set.",
    },
    "QMUCHGCR": {
        "def": str,
        "info": "Show max utility charging currents that may be set.",
    },
    "QBOOT": {"def": str, "info": "Check if DSP bootstrap is supported."},
    # "QOPM": {"def": str, "info": ""},
    # "QPGS0": {"def": str, "info": ""},
}


def onOff(val):
    """
    Converts the val argument to a True or False value.

    The following values for val will result in a True return (string values
    will be lower cased):

        "1", "on", "true", True

    These will result in False values:

        "0", "off", "false", 0, False

    Args:
        val (any): The input to convert.

    Raises:
        ValueError if val is not one of the allowed values

    Returns:
        True or False
    """
    # Always cast val to a string and then lowercase
    val = str(val).lower()

    if val in ["1", "on", "true", True]:
        return True

    if val in ["0", "off", "false", False]:
        return False

    raise ValueError(f"Invalid on/off value: {val}")


# This dictionary defines all available commands, any optional arguments a
# command takes, how to convert these arguments if needed and how to generate
# the command mnemonic to send using the args.
# The low level protocol commands are quite obscure and for that reason we will
# create a set of human readable commands to set various options and settings.
#
# The dict below will have as keys these human version of these commands as the
# keys.
# The value for each key is then another dictionary defining the command info and
# requirements. This dict has these keys:
# 'info': An info message giving details of the purpose of the command and any
#         arguments it takes.
# 'args': A list of functions for each of the required arguments. If the number
#         of args read from the command line does not match the number of
#         entries in this list, it will be an error.
#         If the counts match, then each function in this list will be used to
#         convert the corresponding command line args to a new arg value. If
#         the function is None, no conversion is done.
#         If the resultant args list is only one element, it will be popped out
#         of the list and be handled as a singe value arg.
# 'validate':Optional. As for 'cmd' this is a list of validation functions to
#            call for each arg, AFTER the arg conversions has been done. If any
#            of these are None, validation is ignored. This list must match the
#            number of args expected.
# 'cmd':  This can be an actual protocol command mnemonic, or a callable. If a
#         callable, it will be called with passing in the args converted before
#         as the only function argument. This will be a list if there were
#         multiple args, or a single arg if there was only one arg given.
#         The purpose here to generate the final inverter command to send to
#         perform the action required.
# 'prog': Optionally the program number as per the Mecer SOL-I-AX-3VP manual.
# 'disabled': Optional. If defined with a value of True, the full command and
#             arg processing will be done, but just before sending to the
#             inverter, will show a message that the command is disabled, and
#             exit with status code 1.
COMMANDS = {
    "ALARM": {
        "info": "Enable or disable the buzzer alarm. ARG: [on,1]/[off,0]",
        # Converts the arg to a True/False value
        "args": [onOff],
        # Receives the converted arg (True/False) and builds the inverter
        # command as 'PEa' if arg is True, else 'PDa'
        "cmd": lambda a: f"P{'E' if a else 'D'}a",
        "prog": "18",
    },
    "OVL_BP": {
        "info": "Enable or disable overload bypass. ARG: [on,1]/[off,0]",
        # Converts the arg to a True/False value
        "args": [onOff],
        # Receives the converted arg (True/False) and builds the inverter
        # command as 'PEb' if arg is True, else 'PDb'
        "cmd": lambda a: f"P{'E' if a else 'D'}b",
        "prog": "23",
    },
    "PWR_SV": {
        "info": "Enable or disable power saving mode. ARG: [on,1]/[off,0]",
        # Converts the arg to a True/False value
        "args": [onOff],
        # Receives the converted arg (True/False) and builds the inverter
        # command as 'PEj' if arg is True, else 'PDj'
        "cmd": lambda a: f"P{'E' if a else 'D'}b",
    },
    "LCD_HM": {
        "info": "Enable or disable LCD returning home after 1 min. ARG: [on,1]/[off,0]",
        # Converts the arg to a True/False value
        "args": [onOff],
        # Receives the converted arg (True/False) and builds the inverter
        # command as 'PEk' if arg is True, else 'PDk'
        "cmd": lambda a: f"P{'E' if a else 'D'}k",
        "prog": "19",
    },
    "OL_RST": {
        "info": "Enable or disable overload restart. ARG: [on,1]/[off,0]",
        # Converts the arg to a True/False value
        "args": [onOff],
        # Receives the converted arg (True/False) and builds the inverter
        # command as 'PEu' if arg is True, else 'PDu'
        "cmd": lambda a: f"P{'E' if a else 'D'}u",
        "prog": "06",
    },
    "OT_RST": {
        "info": "Enable or disable over temperature restart. ARG: [on,1]/[off,0]",
        # Converts the arg to a True/False value
        "args": [onOff],
        # Receives the converted arg (True/False) and builds the inverter
        # command as 'PEv' if arg is True, else 'PDv'
        "cmd": lambda a: f"P{'E' if a else 'D'}v",
        "prog": "07",
    },
    "BL": {
        "info": "Backlight control. ARG: [on,1]/[off,0]",
        # Converts the arg to a True/False value
        "args": [onOff],
        # Receives the converted arg (True/False) and builds the inverter
        # command as 'PEx' if arg is True, else 'PDx'
        "cmd": lambda a: f"P{'E' if a else 'D'}x",
        "prog": "20",
    },
    "AL_PSRC": {
        "info": "Enable or disable alarm on primary source interrupt. ARG: [on,1]/[off,0]",
        # Converts the arg to a True/False value
        "args": [onOff],
        # Receives the converted arg (True/False) and builds the inverter
        # command as 'PEy' if arg is True, else 'PDy'
        "cmd": lambda a: f"P{'E' if a else 'D'}y",
        "prog": "22",
    },
    "FC_REC": {
        "info": "Enable or disable fault code record. ARG: [on,1]/[off,0]",
        # Converts the arg to a True/False value
        "args": [onOff],
        # Receives the converted arg (True/False) and builds the inverter
        # command as 'PEz' if arg is True, else 'PDz'
        "cmd": lambda a: f"P{'E' if a else 'D'}z",
        "prog": "25",
    },
    "FACT_RST": {
        "info": "Factory reset to all default values. CAREFUL!!",
        "args": [],
        # This is a command without args.
        "cmd": "PF",
        # Disabled for now
        "disabled": True,
    },
    "OUT_FRQ": {
        "info": "Set the frequency to 50Hz or 60Hz. ARG: 50/60",
        # Converts the arg to a True/False value
        "args": [None],
        "validate": [lambda v: v in ["50", "60"]],
        # Receives the converted arg and builds the inverter command as 'Fnn'
        "cmd": lambda a: f"F{a}",
        # Disabled for now
        "disabled": True,
    },
    "OUT_PRI": {
        "info": "Set device output source priority. ARG: utility_1st | solar_1st | SBU",
        # Conversion is the get() method for this dict.
        "args": [{"utility_1st": "00", "solar_1st": "01", "SBU": "02"}.get],
        "validate": [lambda v: v in ["00", "01", "02"]],
        # Receives the converted arg and builds the inverter command as 'POPnn'
        "cmd": lambda a: f"POP{a}",
        # Disabled for now
        "disabled": True,
        "prog": "01",
    },
    "BAT_UFB_V": {
        # The PDF doc refers to this as the battery recharge voltage, but my
        # interver manual refers to this as the battery voltage at which point
        # the input source will fall back to utility if in Solar 1st or SBU
        # mode (prog 01 or OUT_PRI)
        "info": "Set battery voltage point for utility fallback. ARG nn.n",
        # No conversion. Validation will catch most errors
        "args": [None],
        "validate": [IS_VOLTAGE],
        "cmd": lambda a: f"PBCV{a}",
        "prog": "12",
    },
    "BAT_RET_V": {
        # The PDF doc refers to this as the battery re-discharge voltage, but
        # my inverter manual refers to this as the voltage point at which to
        # return to battery input when in solar/sbu mode and having switched to
        # utility.
        "info": "Set battery voltage to return to bat in sol/bat mode (0=full). ARG: nn.n",
        # No conversion. Validation will catch most errors
        "args": [None],
        "validate": [IS_VOLTAGE],
        # Receives the converted arg and builds the inverter
        # command as 'PBDVnn.n'
        "cmd": lambda a: f"PBDV{a}",
        "prog": "13",
    },
    "CHG_PRI": {
        "info": "Set device charge priority. ARG: utility_1st | solar_1st | sol_util | sol_only",
        # Conversion is the get() method for this dict, returning None if the
        # arg is not in the dict below
        "args": [
            {
                "utility_1st": "00",
                "solar_1st": "01",
                "sol_util": "02",
                "sol_only": "03",
            }.get
        ],
        "validate": [lambda v: v in ["00", "01", "02", "03"]],
        # Receives the converted arg and builds the inverter command as 'PCPnn'
        "cmd": lambda a: f"PCP{a}",
        "prog": "16",
        # Disabled for now
        "disabled": True,
    },
    "AC_IN_V": {
        "info": "Set AC input voltage range. ARG: appliance | ups",
        # Conversion is the get() method for this dict, returning None if the
        # arg is not in the dict below
        "args": [
            {
                "appliance": "00",
                "ups": "01",
            }.get
        ],
        "validate": [lambda v: v in ["00", "01"]],
        # Receives the converted arg and builds the inverter command as 'PGRnn'
        "cmd": lambda a: f"PGR{a}",
        "prog": "03",
        # Disabled for now
        "disabled": True,
    },
    "BAT_TYPE": {
        "info": "Set battery type. ARG: AGM | flooded | user",
        # Conversion is the get() method for this dict, returning None if the
        # arg is not in the dict below
        "args": [
            {
                "AGM": "00",
                "flooded": "01",
                "user": "02",
            }.get
        ],
        "validate": [lambda v: v in ["00", "01", "02"]],
        # Receives the converted arg and builds the inverter command as 'PBTnn'
        "cmd": lambda a: f"PBT{a}",
        "prog": "05",
        # Disabled for now
        "disabled": True,
    },
    "BAT_UND_V": {
        "info": "Set battery under (low DC cut-off) voltage, ARG: nn.n",
        # No conversion. Validation will catch most errors
        "args": [None],
        "validate": [IS_VOLTAGE],
        # Receives the converted arg and builds the inverter
        # command as 'PCVVnn.n'
        "cmd": lambda a: f"PSDV{a}",
        "prog": "29",
    },
    "BAT_BCH": {
        "info": "Set battery bulk charge (c.v.) voltage. ARG: nn.n",
        # No conversion. Validation will catch most errors
        "args": [None],
        "validate": [IS_VOLTAGE],
        # Receives the converted arg and builds the inverter
        # command as 'PCVVnn.n'
        "cmd": lambda a: f"PCVV{a}",
        "prog": "26",
    },
    "BAT_FCH": {
        "info": "Set battery float charge voltage. ARG: nn.n",
        # No conversion. Validation will catch most errors
        "args": [None],
        "validate": [IS_VOLTAGE],
        # Receives the converted arg and builds the inverter
        # command as 'PBFTnn.n'
        "cmd": lambda a: f"PBFT{a}",
        "prog": "27",
    },
}
