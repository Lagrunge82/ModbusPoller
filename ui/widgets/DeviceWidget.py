"""This module provides class for working with Device Widget Window."""

__author__ = "Ilya Molodkin"
__date__ = "2023-04-22"
__version__ = "1.0"
__license__ = "MIT License"

import traceback
from typing import Optional, Dict, List

from PySide6.QtGui import QCloseEvent
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QMessageBox

from ui.widgets.Mixins import LoadUiMixin, FormSubmitMixin
from utils.utils import set_cbox_value


class DeviceWidget(QWidget, LoadUiMixin, FormSubmitMixin):
    """The `DeviceWidget` class is used to display a device window
    :param parent: reference to the parent widget in which the class instance is created
    :type parent: Widget
    """
    def __init__(self, parent=None) -> None:
        super().__init__()
        self.parent: QWidget = parent
        self.guid: Optional[str] = None
        self.setWindowModality(Qt.ApplicationModal)
        self.ui: QWidget = self.load_ui(ui_file="DeviceWidget.ui")
        self.ui.protocol_cbox.addItems(['Modbus RTU', 'Modbus TCP'])
        self.ui.protocol_cbox.setCurrentIndex(0)
        self.ui.protocol_cbox.currentIndexChanged.connect(self.protocol_cbox_changed)
        self.ui.port_cbox.addItems(self.parent.serial.config.keys())
        self.ui.ip_label.setHidden(True)
        self.ui.ip_input.setHidden(True)
        self.ui.address_input.setText('1')
        self.ip_input_value: str = ''
        self.ui.ip_input.textChanged.connect(self.ip_check)
        self.address_input_value: str = ''
        self.ui.address_input.textChanged.connect(self.address_check)
        self.ui.submit_btn.clicked.connect(self.submit)

    def fill_widget(self, guid: str, data: Dict) -> None:
        """The method fills interface elements with device parameters from the `data` dictionary
        :param guid:    unique device identifier
        :type guid:     str
        :param data:    dictionary with device parameters
        :type data:     Dict
        
        :return:        nothing
        :rtype:         None

        .. note::
            The data structure in the `data` dictionary:
            {
                "active": true,
                "address": 1,
                "interface": null,
                "ip": "127.0.0.1",
                "name": "Some Device Name",
                "protocol": "Modbus TCP",
                "registers": {
                    ...
                }
            },
            {
                "active": false,
                "address": 1,
                "interface": COM1,
                "ip": null,
                "name": "Some Other Device Name",
                "protocol": "Modbus RTU",
                "registers": {
                    ...
                }
            }
        """
        self.guid: str = guid
        self.ui.device_input.setText(data['name'])
        set_cbox_value(self.ui.protocol_cbox, data['protocol'])

        if data['ip']:
            self.ui.ip_input.setText(data['ip'])
            self.ui.ip_label.setHidden(False)
            self.ui.ip_input.setHidden(False)
            self.ui.port_label.setHidden(True)
            self.ui.port_cbox.setHidden(True)
        else:
            set_cbox_value(self.ui.port_cbox, data['interface'])
            self.ui.ip_label.setHidden(True)
            self.ui.ip_input.setHidden(True)
            self.ui.port_label.setHidden(False)
            self.ui.port_cbox.setHidden(False)
        self.ui.address_input.setText(str(data['address']))

    def protocol_cbox_changed(self) -> None:
        """
        The method is called on the combobox change event and brings other controls in line with the
        newly set value

        :return:        nothing
        :rtype:         None
        """
        hide_port: bool = bool(self.ui.protocol_cbox.currentIndex())
        self.ui.ip_input.setText('')
        self.ui.port_label.setHidden(hide_port)
        self.ui.port_cbox.setHidden(hide_port)
        self.ui.ip_label.setHidden(not hide_port)
        self.ui.ip_input.setHidden(not hide_port)

    def ip_check(self, text: str) -> None:
        """
        The method is called on the event of changing the ip-address input field, checks its
        correctness and does not allow user to enter an incorrect ip-address
        :param text:    new ip-address
        :type text:     str
        
        :return:        nothing
        :rtype:         None
        """
        octets: str = text.split('.')
        if len(octets) > 4:
            self.ui.ip_input.setText(self.ip_input_value)
            return None

        for octet in octets:
            if octet != '':
                if not octet.isdigit() or int(octet) > 255:
                    self.ui.ip_input.setText(self.ip_input_value)
                    return None
        self.ip_input_value: str = text
        return None

    def address_check(self, text: str) -> None:
        """
        The method is called on the event of the device address input field change and checks its
        correctness.
        It does not allow user to enter an incorrect address (0 <= text <= 247)

        :param text:    new address
        :type text:     str
        
        :return:        nothing
        :rtype:         None
        """
        if text.isdigit():
            if 0 <= int(text) <= 247:
                self.address_input_value = text
                return None
        self.ui.address_input.setText(self.address_input_value)
        return None

    def form_check(self) -> Optional[str]:
        """The method checks the correctness of filling all interface elements
        
        :return:            None if there are no errors, or a string describing the error
        :rtype:             Optional[str]
        :raises ValueError: if the form is filled out incorrectly
        """
        try:
            if not self.ui.device_input.text():
                raise ValueError('Поле "Устройство" не может быть пустым.')
            if self.ui.protocol_cbox.currentText() == 'Modbus RTU':
                if not self.ui.port_cbox.currentText():
                    raise ValueError('Поле "Порт" не может быть пустым.')
            elif self.ui.protocol_cbox.currentText() == 'Modbus TCP':
                ip_octets: List = self.ui.ip_input.text().split('.')
                if len(ip_octets) != 4:
                    raise ValueError('Указан неверный IP-адрес')
                for ip_octet in ip_octets:
                    if int(ip_octet) > 255:
                        raise ValueError('Указан неверный IP-адрес')
            else:
                raise ValueError('Указан неверный протокол.')
            if self.ui.address_input.text():
                if int(self.ui.address_input.text()) > 255:
                    raise ValueError('Адрес не может быть больше 255')
            else:
                raise ValueError('Поле "Адрес" не может быть пустым.')
        except ValueError as e:
            return e.args[0]
        return None
    
    def do_submit(self) -> None:
        """
        Processes the form submission by extracting the data from the form fields, creating 
        a dictionary object and then calling the corresponding configuration object's method 
        to create or update a device based on the extracted data.
        
        :return:    nothing
        :rtype:     None
        """
        interface: Optional[str] = None
        address: str = self.ui.address_input.text()
        protocol: str = self.ui.protocol_cbox.currentText()
        if protocol == 'Modbus RTU':
            interface = self.ui.port_cbox.currentText()
            ip = None
        else:
            ip: str = self.ui.ip_input.text()
        
        name: str = self.ui.device_input.text()
        data: Dict = {'address': int(address),
                      'protocol': protocol,
                      'interface': interface,
                      'ip': ip,
                      'name': name,
                      'active': True}
        if self.guid:
            result: str = self.parent.config.change_device_data(self.guid, data)
            if result:
                msgBox: QMessageBox = QMessageBox()
                msgBox.setText(result)
                msgBox.exec_()
            else:
                self.parent.tables['devices_tb'].load()
                self.close()
        else:
            data['registers']: Dict = {'01 Read Coils': None,
                                       '02 Read Discrete Inputs': None,
                                       '03 Read Holding Registers': None,
                                       '04 Read Input Registers': None, }
            result: Optional[str] = self.parent.config.create_device_data(data)
            try:
                if result:
                    raise LookupError(
                        'Error@DeviceWidget.submit.',
                        f'{result}'
                    )
                self.parent.tables['devices_tb'].load()
                self.close()
            except LookupError as e:
                print(f'{type(e).__name__} occurred, args={str(e.args)}\n\
                        {traceback.format_exc()}')
                msgBox: QMessageBox = QMessageBox()
                msgBox.setText(e.args[1])
                msgBox.exec_()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handles the window close event, deletes its own instance in parent's variable
        :param event: A QCloseEvent object that represents the window close event
        :type event: QCloseEvent

        :return: nothing
        :rtype: None
        """
        _ = event
        self.parent.widgets['device_widget'] = None
