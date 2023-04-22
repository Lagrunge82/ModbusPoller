"""
This module provides two mixin classes: LoadUiMixin and FormSubmitMixin.

LoadUiMixin is a mixin class that provides the functionality to load interface elements from a file and
return them as a widget.

FormSubmitMixin is a mixin class that provides the functionality to submit form data and perform
validation before submission.
"""

__author__ = "Ilya Molodkin"
__date__ = "2023-04-22"
__version__ = "1.0"
__license__ = "MIT License"

import os
from pathlib import Path
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile
from PySide6.QtWidgets import QWidget, QMessageBox


class LoadUiMixin:
    """
    Mixin class providing the functionality to load interface elements from a file and return them
    as a widget.

    :ivar ui_file: str
        The path of the file containing the interface elements.

    :method load_ui:
        Loads interface elements from a file and returns them as a widget.

        :return: The loaded interface as a QWidget object.
        :rtype: QWidget
    """
    # pylint: disable=too-few-public-methods
    def load_ui(self, ui_file: str) -> QWidget:
        """
        This method loads interface elements from a file and returns them as a widget.

        :return:    loaded interface as a QWidget object
        :rtype:     QWidget
        """
        loader: QUiLoader = QUiLoader()
        path: str = os.fspath(Path(__file__).resolve().parent / ui_file)
        ui_file: QFile = QFile(path)
        ui_file.open(QFile.ReadOnly)
        result: QWidget = loader.load(ui_file, self)
        ui_file.close()
        return result


class FormSubmitMixin:
    """
    Mixin class providing the functionality to submit form data and perform validation before
    submission.

    :method submit:
        Submits the form data and performs validation before submission.

        :raises: QMessageBox
            Displays an error message with validation failure details.

        :return: None
    """
    # pylint: disable=too-few-public-methods
    def submit(self) -> None:
        """
        Handles click events on the "Save" button.
        In case of the form is filled correctly it calls self.do_submit() to store data into the 
        configuration object.
        
        :return:    nothing
        :rtype:     None
        """
        form_check: str = self.form_check()
        if form_check:
            msgBox: QMessageBox = QMessageBox()
            msgBox.setText(form_check)
            msgBox.exec_()
        else:
            self.do_submit()
