"""
This module defines the various entities that make up all the parameters and
settings for the inverter.
"""


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
    "dev_prot_id": {"desc": "Device protocol ID", "fmt": int, "unit": None},
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
    "bat_rchr_v": {
        "desc": "Battery re-charge voltage",
        "fmt": float,
        "unit": "V",
    },
    "bat_und_v": {
        "desc": "Battery under voltage",
        "fmt": float,
        "unit": "V",
    },
    "bat_bulk_v": {
        "desc": "Battery bulk voltage",
        "fmt": float,
        "unit": "V",
    },
    "bat_flt_v": {
        "desc": "Battery float voltage",
        "fmt": float,
        "unit": "V",
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
        "fmt": lambda v: ("Utility 1st", "Solar 1st", "Sol+Util", "SOl Only")[int(v)],
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
    "bat_re_dchg_v": {
        "desc": "Battery re-discharge voltage???",
        "fmt": float,
        "unit": "V",
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
    # TODO: These are not unknown. They seem to be part of the dev_stat bit
    #      above, so when parsing dev_stat, also sort this out then
    # There are 4 additional values that are returned that does not seem to be
    # documented anywhere, so we add them here as unknown for now.
    "unkwn_1": {"desc": "Unknown param 1", "fmt": str, "unit": None},
    "unkwn_2": {"desc": "Unknown param 2", "fmt": str, "unit": None},
    "unkwn_3": {"desc": "Unknown param 3", "fmt": str, "unit": None},
    "unkwn_4": {"desc": "Unknown param 4", "fmt": str, "unit": None},
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
}


# These are all the queries supported currently. The format is a dict with keys
# being the query acronym and values one of:
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
    "QPI": ["dev_prot_id"],
    "QID": ["dev_serial"],
    "QVFW": ["fw_ver"],
    "QVFW2": ["fw2_ver"],
    "QPIRI": [
        "grid_rate_v",
        "grid_rate_c",
        "ac_out_rate_v",
        "ac_out_rate_f",
        "ac_out_rate_c",
        "ac_out_rate_apar_p",
        "ac_out_rate_act_p",
        "bat_rate_v",
        "bat_rchr_v",
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
        "bat_re_dchg_v",
        "pv_para_ok",
        "pv_p_bal",
    ],
    "QFLAG": parseDeviceFlags,
    "QPIGS": [
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
        "unkwn_3",
        "unkwn_4",
    ],
    "QMOD": ["dev_mode"],
    "QPIWS": parseWarnState,
    "QDI": [
        "ac_out_v",
        "ac_out_f",
        "ac_chg_max_c",
        "bat_und_v",
        "chg_float_v",
        "chg_bulk_v",
        "bat_rchr_v",
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
        "bat_re_dchg_v",
        "pv_para_ok",
        "pv_p_bal",
    ],
    "QMCHGCR": str,
    "QMUCHGCR": str,
    "QBOOT": str,
    "QOPM": str,
    "QPGS0": str,
}
