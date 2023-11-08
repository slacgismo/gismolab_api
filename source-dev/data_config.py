"""Data configuration

This file is used to configure data records exchanged between modules and
supported by the data module.

FIELDS

    description (string) - helpful description of the field

    type (type) - data type to use when creating a value in the field

    unit (str) - unit of float/complex fields (optional)

    format (str) - formatting string

    none (str or callable) - value to use when no value is provided

    datetime_format (str) - format to use for datetime values (optional)
"""
import time

fields = {
        'timestamp' : {
            'description' : "Last update time in seconds of Unix epoch",
            'type' : float,
            'unit' : 's',
            'format' : '%.6f',
            'none' : time.time,
            'datetime_format' : '%Y-%m-%d %H:%M:%S',
        },
        'energy' : {
            'description' : "Energy meter",
            'type' : float,
            'unit' : 'Wh',
            'none' : 'nan',
            'format' : '%.3f',
        },
        'power' : {
            'description' : "Power measurement",
            'type' : float,
            'unit' : 'W',
            'none' : 'nan',
            'format' : '%.1f',
        },
        'current' : {
            'description' : "Current measurement",
            'type' : float,
            'unit' : 'A',
            'none' : 'nan',
            'format' : '%.1f',
        },
        'voltage' : {
            'description' : "Voltage measurement",
            'type' : float,
            'unit' : 'V',
            'none' : 'nan',
            'format' : '%.1f',
        },
        'ramp' : {
            'description' : "Ramp measurement",
            'type' : float,
            'unit' : 'W/s',
            'none' : 'nan',
            'format' : '%.1f',
        },
        'voltage_control' :
        {
            'description' : 'Voltage control setting',
            'type' : float,
            'unit' : 'V',
            'none' : 'nan',
            'format' : '%.1f',
        },
        'current_control' :
        {
            'description' : 'Current control setting',
            'type' : float,
            'unit' : 'A',
            'none' : 'nan',
            'format' : '%.1f',
        },
        'ramp_control' : {
            'description' : "Ramp control setting",
            'type' : float,
            'unit' : 'W/s',
            'none' : 'nan',
            'format' : '%.1f',
        },
        'power_control' : {
            'description' : "Power control setting",
            'type' : float,
            'unit' : 'W',
            'none' : 'nan',
            'format' : '%.1f',
        },
        'energy_control' : {
            'description' : "Energy control setting",
            'type' : float,
            'unit' : 'Wh',
            'none' : 'nan',
            'format' : '%.1f',
        },
        'device_state' : {
            'description' : "Device status flag",
            'type' : str,
            'format' : '%s',
            'none' : 'UNKNOWN',
        },
    }