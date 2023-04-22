"""
The module provides several useful utility functions.

"""

__author__ = "Ilya Molodkin"
__date__ = "2023-04-22"
__version__ = "1.0"
__license__ = "MIT License"


from typing import Any, Union
from PySide6 import QtCore
from PySide6.QtWidgets import QComboBox


def get_cbox_index(cbox: QComboBox, item: str) -> int:
    """Returns the index of the specified item in a QComboBox
    :param cbox: The QComboBox to search in
    :type cbox: QComboBox
    :param item: The item to search for
    :type item: str

    :return: The index of the item, or -1 if it is not found
    :rtype: int
    """
    return cbox.findText(
        item,
        QtCore.Qt.MatchFixedString
    )


def set_cbox_value(cbox: QComboBox, value: str) -> None:
    """Sets the value of a QComboBox to the specified item
    :param cbox: The QComboBox to modify
    :type cbox: QComboBox
    :param value: The value to set the QComboBox to
    :type value: str

    :return: nothing
    :rtype: None
    """
    index = get_cbox_index(cbox, value)
    if index >= 0:
        cbox.setCurrentIndex(index)


def isNumerical(value: Any) -> bool:
    """Checks if the input value can be converted to a floating-point number
    :param value: The value to check
    :type value: Any

    :return: True if the value can be converted to a floating-point number, False otherwise
    :rtype: bool
    """
    try:
        float(value)
        return True
    except ValueError:
        return False


def notZero(initial_value: Union[float, int],
            value_if_zero: Union[float, int]) -> Union[float, int]:
    """
    Return `initial_value` if it is not zero, otherwise return `value_if_zero`
    :param initial_value:   A float or integer representing the initial value to be checked
    :param value_if_zero:   A float or integer representing the value to be returned if
                            `initial_value` is zero.

    :return:                A float or integer representing either `initial_value` or
                            `value_if_zero`, depending on the value of `initial_value`
    :rtype:                 Union[float, int]
    """
    return initial_value if initial_value else value_if_zero
