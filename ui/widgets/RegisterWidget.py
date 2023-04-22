"""This module provides class for working with Registry Widget Window."""

__author__ = "Ilya Molodkin"
__date__ = "2023-04-22"
__version__ = "1.0"
__license__ = "MIT License"


import re
from typing import Optional, Dict, List

from PySide6.QtGui import QCloseEvent
from PySide6.QtCore import Qt, QModelIndex
from PySide6.QtWidgets import QWidget, QLineEdit, QInputDialog, QMessageBox
from ui.models.tables import AdjustTable

from ui.widgets import Widget
from ui.widgets.Mixins import LoadUiMixin, FormSubmitMixin
from utils.utils import set_cbox_value


class RegisterWidget(QWidget, LoadUiMixin, FormSubmitMixin):
    """The `RegisterWidget` class is used to display a register window
    :param parent: reference to the parent widget in which the class instance is created
    :type parent: Widget
    """
    def __init__(self, parent: Widget = None) -> None:
        super().__init__()
        self.__parent: Widget = parent
        self.__id: Optional[str] = None
        self.__isBinary: Optional[bool] = None
        self.setWindowModality(Qt.ApplicationModal)
        self.__ui = self.load_ui(ui_file="RegisterWidget.ui")

        # configure comboboxes
        self.__binary: Dict = {True: ['Signed'], False: list(parent.vars["formats"].keys())}
        self.__ui.func_cbox.setCurrentIndex(0)
        self.__ui.func_cbox.currentIndexChanged.connect(self.__func_cbox_changed)
        self.__ui.func_cbox.addItems(parent.vars["functions"].keys())

        # configure adjustment table
        self.__adjust_tb = AdjustTable(parent=self, 
                                       table=self.__ui.adjust_tb, 
                                       edit_adjustment_fn=self.__edit_adjustment)
        self.__adjust_tb.header = ['Исходное', 'Преобразованное']
        self.__set_data_type(is_binary=True)
        
        # configure inputs
        self.__input_value: Dict = {}
        self.__input_value['reg_addr']: str  =''
        self.__ui.reg_addr_input.textChanged.connect(self.__address_check)
        self.__input_value['code']: str  =''
        self.__ui.code_input.textChanged.connect(self.__code_check)

        # configure buttons
        self.__ui.add_adjustment_btn.clicked.connect(self.__add_adjustment)
        self.__ui.delete_adjustment_btn.clicked.connect(self.__delete_adjustment)
        self.__ui.submit_btn.clicked.connect(self.submit)

    def fill_widget(self, func: str, addr: int, data: Dict) -> None:
        """The method fills interface elements with device parameters from the `data` dictionary
        :param func:    Modbus function name
        :type func:     str
        :param addr:    register address in Modbus network
        :type addr:     int
        :param data:    dictionary with register parameters
        :type data:     Dict
        
        :return:        nothing
        :rtype:         None

        .. note::
            The data structure in the `data` dictionary:
            {
                "active": true,
                "adjustments": [...],
                "code": "TST3",
                "format": "Signed",
                "id": "d340a7ac-a6a5-4aa9-b9f4-fa4df9022fa2",
                "name": "Test3"
            }
        """
        self.__id = data.get('id', {})
        if func in ['01 Read Coils', '02 Read Discrete Inputs']:
            if self.__isBinary is not True:
                self.__set_data_type(is_binary=True)
        elif func in ['03 Read Holding Registers', '04 Read Input Registers']:
            if self.__isBinary is not False:
                self.__set_data_type(is_binary=False)
        if data.get('adjustments'):
            self.__adjust_tb.data = [[list(item.keys())[0], list(item.values())[0]]
                                     for item in data['adjustments']]
        self.__adjust_tb.load()
        set_cbox_value(self.__ui.func_cbox, func)
        self.__ui.reg_addr_input.setText(str(addr))
        set_cbox_value(self.__ui.format_cbox, data['format'])
        self.__ui.name_input.setText(data['name'])
        self.__ui.code_input.setText(data['code'])

    def __func_cbox_changed(self, text: str) -> None:
        """
        The method is called on the `func_cbox` combobox change event and brings other controls in
        line with the newly set value
        :param text:    the newly set value of the `func_cbox` combobox
        :type text:     str

        :return:        nothing
        :rtype:         None
        """
        if self.__isBinary is not None:
            if text in [0, 1]:
                if self.__isBinary is not True:
                    self.__set_data_type(is_binary=True)
            elif text in [2, 3]:
                if self.__isBinary is not False:
                    self.__set_data_type(is_binary=False)
            else:
                # raise Exception
                pass

    def __set_data_type(self, is_binary: bool) -> None:
        """
        The method sets the data type of the register (numeric if `is_binary` False and binary if
        True) and sets the controls to match the newly set type
        :param is_binary: newly set type (numeric if False and binary if True)
        :type is_binary: bool

        :return: nothing
        :rtype: None
        """
        cbox_data_source: List = self.__binary.get(is_binary)
        self.__ui.format_cbox.clear()
        self.__ui.format_cbox.addItems(cbox_data_source)
        self.__isBinary: bool = is_binary
        binary_header: List = ['Исходное', 'Преобразованное']
        numerical_header: List = ['Операция', 'Операнд']
        self.__adjust_tb.header = binary_header if is_binary else numerical_header
        self.__adjust_tb.data: List = [['0', '0'], ['1', '1']] if is_binary else []
        self.__ui.add_adjustment_btn.setEnabled(not is_binary)
        self.__ui.delete_adjustment_btn.setEnabled(not is_binary)
        self.__adjust_tb.load()

    def __add_adjustment(self) -> None:
        """The method adds new entry to the `adjust_tb` table

        :return: nothing
        :rtype: None
        """
        text: str
        submitted: bool
        text, submitted = QInputDialog.getText(self, 'Операнд',
                                               'Введите значение',
                                               QLineEdit.Normal, '')
        if submitted:
            if text in ['+', '-', '*', '/', '^'] or self.__isBinary:
                self.__adjust_tb.data.append([text, '1'])
                self.__adjust_tb.load()
            else:
                msgBox: QMessageBox = QMessageBox()
                msgBox.setText("Введён некорректрый оператор.")
                msgBox.exec()

    def __edit_adjustment(self, index: QModelIndex) -> None:
        """The method modifies an entry in the `adjust_tb` table
        :param index:   index of the element being changed in the data model
        :type index:    QModelIndex

        :return:        nothing
        :rtype:         None

        .. note::
            This method is used in tables.AdjustTable object
        """
        cur_value: str = self.__adjust_tb.get_row_data(index=index)
        input_dialog_header: str
        text: Optional[str] = None
        submitted: bool = False
        if index.column() == 0:
            input_dialog_header = "Оператор"
        elif index.column() == 1:
            input_dialog_header = "Операнд" if not self.__isBinary else "Преобразованное"
        else:
            raise IndexError('Error@RegisterWidget.edit_adjustment.',
                             'No such column.')
        if index.column() or not self.__isBinary:
            text, submitted = QInputDialog.getText(self,
                                                   input_dialog_header,
                                                   'Введите значение',
                                                   QLineEdit.Normal,
                                                   str(cur_value))
        if submitted:
            if index.column() == 0:
                if text not in ['+', '-', '*', '/', '^']:
                    text = None
                    msgBox = QMessageBox()
                    msgBox.setText("Введён некорректрый оператор.")
                    msgBox.exec()
            elif index.column() == 1:
                if not self.__isBinary:
                    text = text.replace(',', '.')
                    exp = r'^[+-]?\d*\.?\d+(?:[eE][+-]?\d+)?$'
                    if not re.match(exp, text) and not text.isdigit():
                        text = None
                        msgBox = QMessageBox()
                        msgBox.setText("Введён некорректрый операнд.")
                        msgBox.exec()
            else:
                raise IndexError('Error@RegisterWidget.edit_adjustment.',
                                 'No such column.')

            if text:
                self.__adjust_tb.data[index.row()][index.column()] = text
                self.__adjust_tb.load()

    def __delete_adjustment(self) -> None:
        """The method deletes an entry in the `adjust_tb` table

        :return:    nothing
        :rtype:     None
        """
        row_index: QModelIndex = self.__ui.adjust_tb.currentIndex()
        msgBox: QMessageBox = QMessageBox()
        msgBox.setIcon(msgBox.Icon.Warning)
        msgBox.setText('Вы уверены?')
        msgBox.setWindowTitle('Удаление выражения')
        msgBox.setStandardButtons(QMessageBox.Cancel | QMessageBox.Ok)
        value: int = msgBox.exec_()
        # Cancel = 4194304, OK = 1024
        if value == 1024:
            self.__adjust_tb.data.pop(row_index.row())
            self.__adjust_tb.load()

    def __address_check(self, text: str) -> None:
        """
        The method is called on the event of a change in the register address input field and checks
        its correctness
        It does not allow user to enter an incorrect address (0 <= text <= 65535)
        :param text:    new address
        :type text:     str
        
        :return:        nothing
        :rtype:         None
        """
        if text.isdigit() or text == '':
            if 0 <= int(text) <= 65535 or text == '':
                self.__input_value['reg_addr'] = text
                return None
        elif text == '':
            self.__input_value['reg_addr'] = text
            return None
        self.__ui.reg_addr_input.setText(self.__input_value.get('reg_addr'))
        return None

    def __code_check(self, text: str) -> None:
        """
        The method is called on the event of a change in the unique code input field and checks its
        correctness
        It does not allow user to enter an incorrect address ('^[a-zA-Z][a-zA-Z0-9_-]*$')
        :param text:    new code
        :type text:     str
        
        :return:        nothing
        :rtype:         None
        """
        if text:
            if not re.match('^[a-zA-Z][a-zA-Z0-9_-]*$', text):
                self.__ui.code_input.setText(self.__input_value.get('code'))
                return None
        self.__input_value['code'] = text
        return None

    def form_check(self) -> Optional[str]:
        """The method checks the correctness of filling all interface elements
        
        :return:        None if there are no errors, or a string describing the error
        :rtype:         Optional[str]
        """
        if not self.__ui.reg_addr_input.text():
            return 'Поле "Адрес регистра" не может быть пустым.'
        if not self.__ui.code_input.text():
            return 'Поле "Уникальный код" не может быть пустым.'
        if self.__parent.config.check_code_unique(code=self.__ui.code_input.text(), 
                                                  reg_id=self.__id):
            return 'Значение поля "Уникальный код" уже присвоено другому регистру'
        return None

    def do_submit(self) -> None:
        """
        Collects the data entered into the form, constructs a dictionary with the data, and submits
        it to the configuration object for creation or updating of a register record. 
        If successful, reloads the register table and closes the form.
        
        :return:    nothing
        :rtype:     None
        """
        guid: str = self.__parent.tables['devices_tb'].get_row_data(col_index=0)
        tbl_data: List = self.__adjust_tb.data
        data: Dict = {'code': self.__ui.code_input.text(),
                      'id': self.__id,
                      'adjustments': [{item[0]: item[1]} for item in tbl_data],
                      'format': str(self.__ui.format_cbox.currentText()),
                      'name': self.__ui.name_input.text(),
                      'active': True, }
        register_params: Dict = {'guid': guid,
                                 'func': self.__ui.func_cbox.currentText(),
                                 'addr': self.__ui.reg_addr_input.text(),
                                 'data': data, }
        result: bool
        if self.__id:
            result = self.__parent.config.update_register(**register_params)
        else:
            result = self.__parent.config.create_register(**register_params)
        if result:
            self.__parent.tables['registers_tb'].load()
            self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handles the window close event, deletes its own instance in parent's variable
        :param event: A QCloseEvent object that represents the window close event
        :type event: QCloseEvent

        :return: nothing
        :rtype: None
        """
        _ = event
        self.__parent.widgets['register_widget'] = None
