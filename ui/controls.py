"""This module provides controls functions."""

__author__ = "Ilya Molodkin"
__date__ = "2023-04-22"
__version__ = "1.0"
__license__ = "MIT License"


from PySide6.QtWidgets import QMessageBox


def msgBox_fn(text: str, 
              title: str, 
              icon: QMessageBox.Icon = QMessageBox.Icon.Warning, 
              buttons: QMessageBox.StandardButton = QMessageBox.Cancel | QMessageBox.Ok) -> int:
    """
    Displays a message box dialog and returns the result of the user's interaction with it.

    :param text:    The message to be displayed in the message box.
    :type text:     str
    :param title:   The title of the message box.
    :type title:    str
    :param icon:    The icon to be displayed in the message box., defaults to 
                    QMessageBox.Icon.Warning
    :type icon:     QMessageBox.Icon, optional
    :param buttons: The standard buttons to be displayed in the message box.,
                    defaults to QMessageBox.Cancel | QMessageBox.Ok
    :type buttons:  QMessageBox.StandardButton, optional
    :return:        The result of the user's interaction with the message box.
    :rtype:         int

    .. note::
        * Cancel = 4194304
        * OK = 1024
    """
    msbox = QMessageBox()
    msbox.setText(text)
    msbox.setWindowTitle(title)
    msbox.setIcon(icon)
    msbox.setStandardButtons(buttons)

    return msbox.exec_()
