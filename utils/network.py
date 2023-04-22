"""
The serial_ports module provides a function to list the available serial ports on the system.

It uses different methods depending on the operating system to retrieve the available serial ports.

Usage:
------
To use this module, simply import it and call the `serial_ports()` function.

Example:
--------
    import serial_ports

    ports = serial_ports.serial_ports()
    print('Available serial ports: ', ports)

Exceptions:
-----------
- EnvironmentError: raised on unsupported or unknown platforms.

Functions:
----------
    serial_ports():
        Lists the serial port names available on the system.
        
        :raises EnvironmentError: On unsupported or unknown platforms.
        :return: A list of the serial ports available on the system.
        :rtype: List
"""

__author__ = "Ilya Molodkin"
__date__ = "2023-04-22"
__version__ = "1.0"
__license__ = "MIT License"


import sys
import glob
from typing import List
import serial


def serial_ports() -> List:
    """Lists serial port names

    :raises EnvironmentError: On unsupported or unknown platforms
    :return: A list of the serial ports available on the system
    :rtype: List
    """
    if sys.platform.startswith('win'):
        ports = [f'COM{i + 1}' for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result
