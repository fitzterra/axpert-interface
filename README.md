# Axpert Inverter Interface and Controller

**Table of Content**

1. [Introduction](#introduction)
2. [Axpert Commands and examples](#axpert-commands-and-examples)
	1. [Q1 - Undocumented command](#q1---undocumented-command)
	2. [QPI - Device protocol ID inquiry](#qpi---device-protocol-id-inquiry)
	3. [QID - The device serial number inquiry](#qid---the-device-serial-number-inquiry)
	4. [QVFW - Main CPU Firmware version inquiry](#qvfw---main-cpu-firmware-version-inquiry)
	5. [QVFW2 - Another CPU Firmware version inquiry](#qvfw2---another-cpu-firmware-version-inquiry)
	6. [QFLAG - Device flag status inquiry](#qflag---device-flag-status-inquiry)
	7. [QPIGS - Device general status parameters inquiry](#qpigs---device-general-status-parameters-inquiry)
	8. [QMOD - Device mode inquiry](#qmod---device-mode-inquiry)
	9. [QPIWS - Device warning status inquiry](#qpiws---device-warning-status-inquiry)
	10. [QDI - The default setting value information](#qdi---the-default-setting-value-information)
	11. [QMCHGCR - Enquiry selectable value about max charging current](#qmchgcr---enquiry-selectable-value-about-max-charging-current)
	12. [QMUCHGCR - Enquiry selectable value about max utility charging current](#qmuchgcr---enquiry-selectable-value-about-max-utility-charging-current)
	13. [QBOOT - Enquiry DSP has bootstrap or not](#qboot---enquiry-dsp-has-bootstrap-or-not)
	14. [QOPM - Enquiry output mode](#qopm---enquiry-output-mode)
	15. [QPIRI - Device rating information inquiry - nefunguje](#qpiri---device-rating-information-inquiry---nefunguje)
	16. [QPGS0 - Parallel information inquiry](#qpgs0---parallel-information-inquiry)
	17. [QBV - Compensated Voltage, SoC](#qbv---compensated-voltage-soc)
	18. [PEXXX - Setting some status enable](#pexxx---setting-some-status-enable)
	19. [PDXXX - Setting some status disable](#pdxxx---setting-some-status-disable)
	20. [PF - Setting control parameter to default value](#pf---setting-control-parameter-to-default-value)
	21. [FXX - Setting device output rating frequency](#fxx---setting-device-output-rating-frequency)
	22. [POP02 - set to SBU](#pop02---set-to-sbu)
	23. [POP01 - set to Solar First](#pop01---set-to-solar-first)
	24. [POP00 - Set to UTILITY](#pop00---set-to-utility)
	25. [PBCVXX_X - Set battery re-charge voltage](#pbcvxx_x---set-battery-re-charge-voltage)
	26. [PBDVXX_X - Set battery re-discharge voltage](#pbdvxx_x---set-battery-re-discharge-voltage)
	27. [PCP00 - Setting device charger priority: Utility First](#pcp00---setting-device-charger-priority-utility-first)
	28. [PCP01 - Setting device charger priority: Solar First](#pcp01---setting-device-charger-priority-solar-first)
	29. [PCP02 - Setting device charger priority: Solar and Utility](#pcp02---setting-device-charger-priority-solar-and-utility)
	30. [PGRXX - Setting device grid working range](#pgrxx---setting-device-grid-working-range)
	31. [PBTXX - Setting battery type](#pbtxx---setting-battery-type)
	32. [PSDVXX_X - Setting battery cut-off voltage](#psdvxx_x---setting-battery-cut-off-voltage)
	33. [PCVVXX_X - Setting battery C.V. charging voltage](#pcvvxx_x---setting-battery-cv-charging-voltage)
	34. [PBFTXX_X - Setting battery float charging voltage](#pbftxx_x---setting-battery-float-charging-voltage)
	35. [PPVOCKCX - Setting PV OK condition](#ppvockcx---setting-pv-ok-condition)
	36. [PSPBX - Setting solar power balance](#pspbx---setting-solar-power-balance)
	37. [MCHGC0XX - Setting max charging Current          M XX](#mchgc0xx---setting-max-charging-current----------m-xx)
	38. [MUCHGC002 - Setting utility max charging current  0 02](#muchgc002---setting-utility-max-charging-current--0-02)
	39. [MUCHGC010 - Setting utility max charging current  0 10](#muchgc010---setting-utility-max-charging-current--0-10)
	40. [MUCHGC020 - Setting utility max charging current  0 20](#muchgc020---setting-utility-max-charging-current--0-20)
	41. [MUCHGC030 - Setting utility max charging current  0 30](#muchgc030---setting-utility-max-charging-current--0-30)
	42. [POPMMX - Set output mode](#popmmx---set-output-mode)
	43. [Not Working](#not-working)
		1. [PPCP000 - Setting parallel device charger priority: UtilityFirst - notworking](#ppcp000---setting-parallel-device-charger-priority-utilityfirst---notworking)
		2. [PPCP001 - Setting parallel device charger priority: SolarFirst - notworking](#ppcp001---setting-parallel-device-charger-priority-solarfirst---notworking)
		3. [PPCP002 - Setting parallel device charger priority: OnlySolarCharging - notworking](#ppcp002---setting-parallel-device-charger-priority-onlysolarcharging---notworking)

## Introduction

This package can be used to manage an Axpert type inverter. It is based on many
bits and pieces from all over the interwebs and Git hubs, and it may or may not
work on your version or type of Axpert interver, so YMMV.

## Axpert Commands and examples

### Q1 - Undocumented command

    LocalInverterStatus (seconds from absorb),
    ParaExistInfo (seconds from end of Float),
    SccOkFlag,
    AllowSccOnFlag,
    ChargeAverageCurrent,
    SCC PWM Temperature,
    Inverter Temperature,
    Battery Temperature,
    Transformer Temperature,
    GPDAT,
    FanLockStatus,
    FanPWMDuty,
    FanPWM,
    SCCChargePowerWatts,
    ParaWarning,
    SYNFreq,
    InverterChargeStatus

### QPI - Device protocol ID inquiry

### QID - The device serial number inquiry

### QVFW - Main CPU Firmware version inquiry

### QVFW2 - Another CPU Firmware version inquiry

### QFLAG - Device flag status inquiry

### QPIGS - Device general status parameters inquiry

    GridVoltage,
    GridFrequency,
    OutputVoltage,
    OutputFrequency,
    OutputApparentPower,
    OutputActivePower,
    OutputLoadPercent,
    BusVoltage,
    BatteryVoltage,
    BatteryChargingCurrent,
    BatteryCapacity,
    InverterHeatSinkTemperature,
    PV-InputCurrentForBattery,
    PV-InputVoltage,
    BatteryVoltageFromSCC,
    BatteryDischargeCurrent,
    DeviceStatus,

### QMOD - Device mode inquiry

* P: PowerOnMode,
* S: StandbyMode,
* L: LineMode,
* B: BatteryMode,
* F: FaultMode,
* H: PowerSavingMode

### QPIWS - Device warning status inquiry

    Reserved,
    InverterFault,
    BusOver,
    BusUnder,
    BusSoftFail,
    LineFail,
    OPVShort,
    InverterVoltageTooLow,
    InverterVoltageTooHIGH,
    OverTemperature,
    FanLocked,
    BatteryVoltageHigh,
    BatteryLowAlarm,
    Reserved,
    ButteryUnderShutdown,
    Reserved,
    OverLoad,
    EEPROMFault,
    InverterSoftFail,
    SelfTestFail,
    OPDCVoltageOver,
    BatOpen,
    CurrentSensorFail,
    BatteryShort,
    PowerLimit,
    PVVoltageHigh,
    MPPTOverloadFault,
    MPPTOverloadWarning,
    BatteryTooLowToCharge,
    Reserved,
    Reserved

### QDI - The default setting value information

### QMCHGCR - Enquiry selectable value about max charging current

### QMUCHGCR - Enquiry selectable value about max utility charging current

### QBOOT - Enquiry DSP has bootstrap or not

### QOPM - Enquiry output mode

### QPIRI - Device rating information inquiry - nefunguje

### QPGS0 - Parallel information inquiry

    TheParallelNumber,
    SerialNumber,
    WorkMode,
    FaultCode,
    GridVoltage,
    GridFrequency,
    OutputVoltage,
    OutputFrequency,
    OutputAparentPower,
    OutputActivePower,
    LoadPercentage,
    BatteryVoltage,
    BatteryChargingCurrent,
    BatteryCapacity,
    PV-InputVoltage,
    TotalChargingCurrent,
    Total-AC-OutputApparentPower,
    Total-AC-OutputActivePower,
    Total-AC-OutputPercentage,
    InverterStatus,
    OutputMode,
    ChargerSourcePriority,
    MaxChargeCurrent,
    MaxChargerRange,
    Max-AC-ChargerCurrent,
    PV-InputCurrentForBattery,
    BatteryDischargeCurrent

### QBV - Compensated Voltage, SoC

### PEXXX - Setting some status enable

### PDXXX - Setting some status disable

### PF - Setting control parameter to default value

### FXX - Setting device output rating frequency

### POP02 - set to SBU

### POP01 - set to Solar First

### POP00 - Set to UTILITY

### PBCVXX_X - Set battery re-charge voltage

### PBDVXX_X - Set battery re-discharge voltage

### PCP00 - Setting device charger priority: Utility First

### PCP01 - Setting device charger priority: Solar First

### PCP02 - Setting device charger priority: Solar and Utility

### PGRXX - Setting device grid working range

### PBTXX - Setting battery type

### PSDVXX_X - Setting battery cut-off voltage

### PCVVXX_X - Setting battery C.V. charging voltage

### PBFTXX_X - Setting battery float charging voltage

### PPVOCKCX - Setting PV OK condition

### PSPBX - Setting solar power balance

### MCHGC0XX - Setting max charging Current          M XX

### MUCHGC002 - Setting utility max charging current  0 02

### MUCHGC010 - Setting utility max charging current  0 10

### MUCHGC020 - Setting utility max charging current  0 20

### MUCHGC030 - Setting utility max charging current  0 30

### POPMMX - Set output mode

**M**:

    0:single
    1: parrallel
    2: PH1
    3: PH2
    4: PH3

### Not Working

#### PPCP000 - Setting parallel device charger priority: UtilityFirst - notworking

#### PPCP001 - Setting parallel device charger priority: SolarFirst - notworking

#### PPCP002 - Setting parallel device charger priority: OnlySolarCharging - notworking
