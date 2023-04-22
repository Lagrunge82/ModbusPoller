"""This module provides class for working with Main Widget Window."""

__author__ = "Ilya Molodkin"
__date__ = "2023-04-22"
__version__ = "1.0"
__license__ = "MIT License"


import copy
import os
from datetime import datetime
from itertools import chain
from pathlib import Path
from typing import Dict, List, Optional
import yaml

from PySide6.QtCore import Qt, QThreadPool, QTimer, QPoint, Slot
from PySide6.QtGui import QAction, QBrush, QColor, QCloseEvent
from PySide6.QtWidgets import (QWidget, QMessageBox, QTableView, QTreeWidgetItem,
                               QInputDialog, QLineEdit, QMenu, QApplication)

from tabulate import tabulate

from ui.controls import msgBox_fn
from ui.models.tables import DataTable, DeviceTable, RegisterTable, StatusTable
from ui.widgets.DeviceWidget import DeviceWidget
from ui.widgets.RegisterWidget import RegisterWidget
from ui.widgets.ChartWidget import ChartWidget
from ui.widgets.Mixins import LoadUiMixin
from utils.config import Config
from utils.modbus import Poller
from utils.network import serial_ports
from utils.workers import PollingWorker, Worker
# from guppy import hpy


class Serial:
    """
    A class for managing serial port connections
    :param config: A dictionary containing configuration options for each serial port
    :type config: dict

    :ivar config: The input configuration dictionary
    :ivar fact: A list of the available serial ports in the system
    :ivar disabled: A list of the serial ports configured in the input dictionary but not available
    :ivar parameters: Dictionary that contains all parameters for the serial connection
    """
    # pylint: disable=too-few-public-methods
    def __init__(self, config: Dict) -> None:
        # ports configured
        self.config: Dict = config
        # ports physically available
        self.fact: List = serial_ports()
        # ports configured but physically not available
        self.disabled: List = list(set(self.config.keys()) - set(self.fact))
        # serial dict parameters
        self.parameters: Optional[Dict] = None


class Daemon:
    """A class that represents a daemon for managing worker threads and polling devices
    :ivar threadpool: A `QThreadPool` instance used to manage worker threads
    :ivar data_file: An optional string representing the path to a data file
    :ivar is_polling: A boolean indicating whether polling is currently enabled
    :ivar devices: A dictionary mapping device names to device objects
    :ivar register_counter: An integer representing the current register count
    :ivar workers: A dictionary mapping worker IDs to worker objects
    :ivar workers_data: A dictionary storing data retrieved from worker
    :ivar table_data: A dictionary that stores data to put in a table
    :ivar onPollingDisabled: A list of controls to disable when polling is started

    """
    def __init__(self) -> None:
        self.threadpool = QThreadPool()
        print(f"Multithreading with maximum {self.threadpool.maxThreadCount()} threads")
        self.data_file: Optional[str] = None
        self.is_polling: bool = False
        self.devices: Dict = {}
        self.register_counter: int = 0
        self.workers: Dict[Worker] = {}
        self.workers_data: Dict = {}
        self.table_data: Dict = {}
        self.onPollingDisabled: List = []


class Widget(QWidget, LoadUiMixin):
    """
    The Widget class is used to display the main window of the application.
    
    """
    # pylint: enable=too-many-instance-attributes
    # pylint: disable=too-many-public-methods

    def __init__(self, parent=None) -> None:
        super().__init__()
        _ = parent
        with open('variables.yml', "r", encoding='utf8') as stream:
            try:
                self.vars = yaml.safe_load(stream)
            except yaml.YAMLError as e:
                print(e)

        # !!!=== load config ===!!! #
        self.config: Config = Config('config.yml')
        self.serial: Serial = Serial(config=self.config._serial)
        self.serial.parameters = self.vars['serial parameters']

        # !!!=== load ui ===!!! #
        self.ui: QWidget = self.load_ui(ui_file="Widget.ui")
        self.tables: Dict = {}
        self.widgets: Dict = {}
        self.widgets['charts']: Dict = {}
        self.configure_main_tab()
        self.configure_slaves_tab()
        self.configure_network_tab()

        initial_tab = self.ui.tabWidget.findChild(QWidget, 'tab1')
        if self.serial.disabled:
            msgBox_fn(text='Обнаружено несоответствие.\n'
                      'Проверьте конфигурацию последовательных портов.',
                      title='Ошибка конфигурации', buttons=QMessageBox.Ok)
            initial_tab = self.ui.tabWidget.findChild(QWidget, 'tab3')
        self.ui.tabWidget.setCurrentWidget(initial_tab)

        # !!!=== configure threadpool ===!!! #
        self.dmn: Daemon = Daemon()
        self.dmn.onPollingDisabled = [self.ui.test_poll_btn,
                                      self.ui.addDevice,
                                      self.ui.changeDevice,
                                      self.ui.deleteDevice,
                                      self.ui.addRegister,
                                      self.ui.changeRegister,
                                      self.ui.deleteRegister, ]
        self.timer = QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.daemon_fn)
        self.timer.start()

    def configure_main_tab(self):
        """
        Configures the main tab of the UI, including the status and data tables,
        and other elements such as buttons.

        :return:    nothing
        :rtype:     None
        """
        # === configure status_tb === #
        self.tables['status_tb'] = StatusTable(parent=self, table=self.ui.status_tb)

        # === configure data_tb === #
        self.tables['data_tb'] = DataTable(parent=self, table=self.ui.data_tb)

        # === configure other elements === #
        self.ui.start_poll_btn.clicked.connect(self.start_polling)
        self.ui.test_poll_btn.clicked.connect(self.test_polling)

    def configure_slaves_tab(self) -> None:
        """
        Configures the slaves tab of the UI, including the device and register tables,
        and other elements such as buttons.

        :return:    nothing
        :rtype:     None
        """
        # === configure devices_tb === #
        self.tables['devices_tb'] = DeviceTable(parent=self, table=self.ui.devices_tb)

        # === configure registers_tb === #
        self.tables['registers_tb'] = RegisterTable(parent=self, table=self.ui.registers_tb)

        # === configure other elements === #
        self.ui.addDevice.clicked.connect(self.add_device)
        self.ui.changeDevice.clicked.connect(self.edit_device)
        self.ui.deleteDevice.clicked.connect(self.delete_device)

        self.ui.addRegister.clicked.connect(self.add_register)
        self.ui.changeRegister.clicked.connect(self.edit_register)
        self.ui.deleteRegister.clicked.connect(self.delete_register)

        self.ui.saveConfig.clicked.connect(self.save_config)

    def configure_network_tab(self) -> None:
        """
        Configures the network tab of the UI, including the serials table and context menu, 
        and sets up signal connections.

        :return:    nothing
        :rtype:     None
        """
        self.ui.serials_tw.setStyleSheet("QHeaderView::section { background-color:silver }")
        self.ui.serials_tw.setColumnCount(2)
        self.ui.serials_tw.setHeaderLabels(["Параметр", "Значение"])
        self.ui.serials_tw.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.serials_tw.customContextMenuRequested.connect(self._serials_context_menu)
        self.load_serials()
        self.ui.serials_tw.doubleClicked.connect(self.edit_serial)

    def load_serials(self) -> None:
        """
        Loads the serial ports and their parameters from the internal data structures and displays
        them as a QTreeWidget in the UI.

        :return:    nothing
        :rtype:     None
        """
        self.ui.serials_tw.clear()

        items: List = []
        for serial in sorted(set( self.serial.fact + list(self.serial.config.keys()))):
            item = QTreeWidgetItem([serial])
            if serial in self.serial.config.keys():
                for parameter, value in self.serial.config.get(serial, {}).items():
                    child = QTreeWidgetItem([parameter.capitalize(), str(value)])
                    item.addChild(child)
            else:
                for parameter in ['baud', 'bits', 'parity', 'stop']:
                    child = QTreeWidgetItem([parameter.capitalize(), 'None'])
                    item.addChild(child)
            items.append(item)
        self.ui.serials_tw.insertTopLevelItems(0, items)
        self.map_serial_status()

    def start_polling(self) -> None:
        """Starts or stops polling of slave devices and saves data to a CSV file.
        If polling is started, initializes poller workers and disables pool buttons
        from `onPollingDisabled` list.
        If polling is stopped, terminates poller workers, closes all chart windows, and enables
        pool buttons from `onPollingDisabled` list.

        :return:    nothing
        :rtype:     None
        """
        self.dmn.is_polling = self.ui.start_poll_btn.isChecked()
        if self.dmn.is_polling:
            filename = datetime.now().strftime('%Y%m%d_%H%M%S.%f.csv')
            self.dmn.data_file: str = os.fspath(Path(__file__).parents[2] / 'data' / filename)
            self._init_pollers()
            self.ui.start_poll_btn.setText('Стоп')
            for btn in self.dmn.onPollingDisabled:
                btn.setEnabled(not self.dmn.is_polling)
            for worker in self.dmn.workers.values():
                self.dmn.threadpool.start(worker)
        else:
            self._kill_pollers()
            for key in list(self.widgets['charts'].keys()):
                self.widgets['charts'][key].close()
            self.ui.start_poll_btn.setText('Старт')
            for btn in self.dmn.onPollingDisabled:
                btn.setEnabled(not self.dmn.is_polling)
            self.dmn.data_file = None

    def polling(self) -> bool:
        """
        Returns a boolean indicating whether the application is currently in polling mode.

        :return: A boolean indicating whether the application is currently polling.
        :rtype: bool
        """
        return self.dmn.is_polling

    def test_polling(self) -> None:
        """
        Starts a test poll of the connected devices.

        :return:    nothing
        :rtype:     None
        """
        if self.dmn.is_polling is False:
            self._init_pollers()
            for worker in self.dmn.workers.values():
                self.dmn.threadpool.start(worker)
            # self._kill_pollers()

    def _init_pollers(self) -> None:
        """
        Initialize pollers for all devices and the memory worker.

        Each device's poller is set up with the device's settings and registers,
        and a polling worker is created for each device. The polling worker
        is started on a separate thread, and its result signal is connected to the 
        `worker_exec` slot.

        The memory worker is also created and started on a separate thread. Its result signal
        is connected to the `mem_worker_res` slot, and its finished signal is connected to the
        `mem_worker_fin` slot.

        :return:    nothing
        :rtype:     None
        """
        self.dmn.devices = self.config.get_pollers()
        self.dmn.register_counter = 0
        for guid, device in self.dmn.devices.items():
            poller = Poller(device['settings'])
            self.dmn.register_counter += len(list(chain(*device['registers'].values())))
            poller.registers = device['registers']
            worker: PollingWorker = PollingWorker(guid=guid, sleep=1000, fn=self.polling)
            worker.poller = poller
            worker.signals.result.connect(self.worker_exec)
            self.dmn.workers[guid] = worker

        # print('Запускаем MemWorker...')
        # mem_worker = MemWorker(fn=self.polling)
        # mem_worker.signals.result.connect(self.mem_worker_res)
        # mem_worker.signals.finished.connect(self.mem_worker_fin)
        # self.dmn.workers['MemWorker'] = mem_worker

    def _kill_pollers(self) -> None:
        """
        Stops all running workers.
        
        """
        self.dmn.register_counter = 0
        if self.dmn.workers:
            self.dmn.workers.clear()

    @Slot(dict)
    def worker_exec(self, result: Dict) -> None:
        """
        Updates the data of a specific poller worker.

        :param result: _description_
        :type result: dict

        .. note::
            Data structure of `result` dictionary:
            {
                "guid": "fab33655-d9e8-56fb-a863-4550d349ef21", <<< Уникальный id устройства
                "registers": [                                  <<< Строки (список регистров),
                    [                                               соответствуют header таблицы
                        "MBus Tools test",
                        "8182d55d-3531-4594-b430-a643d8f3bc4c",
                        "0",
                        "Test0",
                        "TCP0",
                        "Signed",
                        "Yes",
                        [
                            true,
                            true,
                            true
                        ],
                        "04-04-2023 13:28:26",
                        true
                    ],
                    ...
                ]
            }
        """
        guid = result['guid']
        self.dmn.workers_data[guid] = result['registers']

    def daemon_fn(self) -> None:
        """
        The daemon function that updates the table and charts with data from workers.
        Refreshes the table data with the most recent data from the workers and updates the charts
        and CSV files.
        When polling started, appends the most recent data to the file and generates an information
        file containing the column descriptions.
        If the number of rows in the data table does not match the length of the data, reloads
        the data into the table, otherwise updates the data.
        For each chart, finds the row with matching id and updates the value, series and ranges
        of the chart's axis.

        :return:    nothing
        :rtype:     None
        """
        if self.dmn.table_data != self.dmn.workers_data:
            self.dmn.table_data = copy.deepcopy(self.dmn.workers_data)
            for device in self.dmn.workers_data.values():
                for register in device:
                    if register[9] is True:
                        register[9] = False
                    elif register[9] is False:
                        register[9] = None
            data = list(chain.from_iterable(self.dmn.table_data.values()))
            status = [['', value[9] if value[6] is not None else None] for value in data]
            self.tables['status_tb'].load(data=status)
            if self.tables['data_tb'].row_count != len(data):
                self.tables['data_tb'].load(data=data)
            else:
                self.tables['data_tb'].update(data=data, columns=[6])
            
            if self.dmn.is_polling:
                if self.dmn.register_counter == len(data):
                    self.store_to_csv(data=data)
                self.draw_chart(data=data)

    def store_to_csv(self, data: List) -> None:
        """
        Stores the provided data into a CSV file.

        :param data:    The data to store into the CSV file, where each row of data is represented
                        as a list of values.
        :type data:     List

        :return:        nothing
        :rtype:         None
        """
        
        if self.dmn.data_file:
            # generate info file if it doesn't exist
            info_path = self.dmn.data_file[:-3] + 'info'
            if not os.path.isfile(info_path):
                formated_data = list(zip(*data))
                info_data: Dict = {'Device': formated_data[0],
                                   'Function': formated_data[10],
                                   'Register': formated_data[2],
                                   'Format': formated_data[5],
                                   'Code': formated_data[4],
                                   'Description': formated_data[3], }
                with open(file=info_path, mode='w', encoding='utf-8') as info_file:
                    info_file.write(tabulate(info_data,
                                             headers='keys',
                                             tablefmt="simple_grid", ))
            # append data to the CSV file
            csv_header: List = []
            if not os.path.isfile(self.dmn.data_file):
                csv_header = [f'"{value}"' for value in [register[4] for register in data]]
                csv_header.insert(0, '"date"')
            csv_data = [register[6] if register[6] is not None else 'None' for register in data]
            csv_data.insert(0, datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f') + '+03')
            with open(file=self.dmn.data_file, mode='a', encoding='utf-8') as csv_file:
                if csv_header:
                    csv_file.write('\t'.join(csv_header) + '\n')
                    csv_header = []
                csv_file.write('\t'.join(csv_data) + '\n')
        
    def draw_chart(self, data: List) -> None:
        """
        Updates the chart with new data points
        :param data:    A list of rows of data to be displayed on the chart, where each row 
                        is represented as a list of values. The first value in each row is
                        the chart ID
        :type data:     List

        :return:        nothing
        :rtype:         None
        """
        now: datetime = datetime.now()
        dt: float = datetime.timestamp(now) * 1000

        for row in data:
            if row[1] in self.widgets['charts']:
                self.widgets['charts'][row[1]].add_point(dt, float(row[6]))

    def data_tb_doubleclicked(self) -> None:
        """
        Handles double-click events on the data table.
        If the clicked column is 6 (containing value), calls `data_tb_set_value()`, otherwise calls
        `data_tb_open_chart()`.
        
        :return:    nothing
        :rtype:     None
        """
        if self.tables['data_tb'].table.currentIndex().column() == 6:
            self.data_tb_set_value()
        else:
            if self.tables['data_tb'].get_row_data(col_index=10) in [3, 4]:
                self.data_tb_open_chart()

    def data_tb_set_value(self) -> None:
        """
        This method sets a value to a register or a coil of a device.
        
        :return:    nothing
        :rtype:     None
        """
        guid = self.tables['data_tb'].get_row_data(col_index=11)
        address = self.tables['data_tb'].get_row_data(col_index=2)
        fn = self.tables['data_tb'].get_row_data(col_index=10)
        reg_id: str = self.tables['data_tb'].get_row_data(col_index=1)
        register: List = self.config.get_device_register_data(guid=guid, 
                                                              func=None, 
                                                              addr=str(address), 
                                                              reg_id=reg_id)
        cur_value: str = self.tables['data_tb'].get_row_data(col_index=6)
        if fn == 1:
            items: List = [value for item in register['adjustments'] for value in item.values()]
            text, submitted = QInputDialog.getItem(self, 
                                                   'Введите знечение', 
                                                   'Label:', 
                                                   items, 
                                                   items.index(cur_value), 
                                                   False)
            if submitted:
                self.dmn.workers[guid].writeSingleCoil(address=address,
                                                       value=bool(items.index(text)))
        elif fn == 3:
            text, submitted = QInputDialog.getText(self, 
                                                   'Введите знечение', 
                                                   'Label:', 
                                                   QLineEdit.Normal, 
                                                   cur_value)
            if submitted:
                value_format: str = self.tables['data_tb'].get_row_data(col_index=5)

                result = self.dmn.workers[guid].writeRegisters(address=address,
                                                           data_format=value_format,
                                                           adj=register['adjustments'],
                                                           value=text)
                if result is None:
                    msgBox_fn(text='Введён некорректный формат данных.',
                              title='Ошибка формата данных', buttons=QMessageBox.Ok)
    
    def data_tb_open_chart(self) -> None:
        """
        Opens a new `ChartWidget` to display the chart of the selected row. If a chart for the
        selected `reg_id` already exists, it is activated instead of creating a new one.
        
        :return:    nothing
        :rtype:     None
        """
        reg_id: str = self.tables['data_tb'].get_row_data(col_index=1)
        if reg_id in self.widgets['charts']:
            self.widgets['charts'][reg_id].activateWindow()
        else:
            self.widgets['charts'][reg_id] = ChartWidget(self)
            self.widgets['charts'][reg_id].show()

    def devices_tb_context_act(self) -> None:
        """
        Method handles the action taken in response to a user's right-click on a row
        in the "Devices" table of the graphical user interface (GUI). The method retrieves the GUID
        of the selected device from the table and uses the change_device_activity() method of the
        config object to change the activity status of the device. Finally, it reloads the data
        in the "Devices" table.
        
        :return:    nothing
        :rtype:     None
        """
        guid = self.tables['devices_tb'].get_row_data(col_index=0)
        self.config.change_device_activity(guid)
        self.tables['devices_tb'].load()

    def add_device(self) -> None:
        """
        Opens a widget to add a new device.
        
        :return:    nothing
        :rtype:     None
        """
        self.open_device_widget()

    def edit_device(self):
        """
        Opens a widget to edit device parameters.
        
        :return:    nothing
        :rtype:     None
        """
        if self.dmn.is_polling is False:
            guid = self.tables['devices_tb'].get_row_data(col_index=0)
            if guid:
                self.open_device_widget(guid)

    def open_device_widget(self, guid: str = None) -> None:
        """Opens a DeviceWidget to allow adding or editing a device.

        :param guid: The GUID of the device to edit, defaults to None
        :type guid: str, optional
        
        :return:    nothing
        :rtype:     None
        """
        self.widgets['device_widget'] = DeviceWidget(self)
        if guid:
            data = self.config.get_device_data(guid)
            self.widgets['device_widget'].fill_widget(guid, data)
        self.widgets['device_widget'].show()

    def delete_device(self) -> None:
        """
        Deletes the device that is currently selected in the devices table.
        
        :return:    nothing
        :rtype:     None
        """
        guid = self.tables['devices_tb'].get_row_data(col_index=0)
        if guid:
            value = msgBox_fn(text='Вы уверены?', title='Удаление устойства')
            if value == 1024:
                self.config.delete_device_data(guid)
                self.ui.saveConfig.setEnabled(self.config.isChanged())
                self.tables['devices_tb'].load()
                self.tables['registers_tb'].load()

    def registers_tb_context_act(self) -> None:
        """
        Method handles the action taken in response to a user's right-click on a row
        in the "Registers" table of the graphical user interface (GUI).
        It changes the status of the register activity (active or inactive) in the configuration
        and then reloads the registers table.
        
        :return:    nothing
        :rtype:     None
        """
        guid = self.tables['devices_tb'].get_row_data(col_index=0)
        func = self.tables['registers_tb'].get_row_data(col_index=0)
        addr = self.tables['registers_tb'].get_row_data(col_index=2)
        reg_id = self.tables['registers_tb'].get_row_data(col_index=7)
        if guid and func and addr:
            self.config.change_register_activity(guid, func, addr, reg_id)
            self.tables['registers_tb'].load()

    def add_register(self):
        """
        Opens a widget to add a new register.
        
        :return:    nothing
        :rtype:     None
        """
        if self.tables['devices_tb'].get_row_data(col_index=0):
            self.widgets['register_widget'] = RegisterWidget(self)
            self.widgets['register_widget'].show()

    def edit_register(self):
        """
        Opens a widget to edit register parameters.
        
        :return:    nothing
        :rtype:     None
        """
        if self.dmn.is_polling is False:
            guid = self.tables['devices_tb'].get_row_data(col_index=0)
            if guid:
                func = self.tables['registers_tb'].get_row_data(col_index=0)
                addr = self.tables['registers_tb'].get_row_data(col_index=2)
                reg_id = self.tables['registers_tb'].get_row_data(col_index=7)
                if func and addr:
                    data = self.config.get_device_register_data(guid, func, addr, reg_id)
                    if data:
                        self.widgets['register_widget'] = RegisterWidget(self)
                        self.widgets['register_widget'].fill_widget(func, int(addr), data)
                        self.widgets['register_widget'].show()
                    else:
                        self.tables['registers_tb'].load()

    def delete_register(self):
        """
        Deletes the register that is currently selected in the register table.
        
        :return:    nothing
        :rtype:     None
        """
        guid = self.tables['devices_tb'].get_row_data(col_index=0)
        if guid:
            func = self.tables['registers_tb'].get_row_data(col_index=0)
            addr = self.tables['registers_tb'].get_row_data(col_index=2)
            reg_id = self.tables['registers_tb'].get_row_data(col_index=7)
            if func and addr:
                value = msgBox_fn(text='Вы уверены?', title='Удаление регистра')
                if value == 1024:
                    self.config.delete_register(guid, func, addr, reg_id)
                    self.tables['registers_tb'].load()

    @staticmethod
    def get_row_data(table: QTableView, col: int) -> Optional[str]:
        """This method returns the value of a given column for the currently selected row
        in a QTableView object. If there is no row selected, it returns None.

        :param table:   A QTableView object from which to get the data
        :type table:    QTableView
        :param col:     An integer representing the column number of the desired data.
        :type col:      int
        :return:        The value of the desired column for the currently selected row,
                        or None if thereis no row selected.
        :rtype:         Optional[str]
        """
        row_index: int = table.currentIndex().row()
        if row_index > -1:
            model = table.model()
            return model.data(model.index(row_index, col), 0)
        return None

    def _serials_context_menu(self, position: QPoint) -> None:
        """
        Shows the context menu for the serial connections treeview.

        :param table:   The position where the context menu was triggered.
        :type table:    QPoint
        :return:    nothing
        :rtype:     None
        """
        column = self.ui.serials_tw.currentColumn()
        if self.ui.serials_tw.currentItem():
            text = self.ui.serials_tw.currentItem().text(column)
            if text in self.serial.config.keys():
                display_action = QAction("Удалить")
                display_action.triggered.connect(self._delete_serial)
                display_action.setEnabled(not self.dmn.is_polling)

                menu = QMenu(self.ui.serials_tw)
                menu.addAction(display_action)
                menu.exec_(self.ui.serials_tw.mapToGlobal(position))

    def edit_serial(self) -> None:
        """
        Edits the selected serial parameter value for the selected device in the serials table.
        The user is prompted with a list of possible values to choose from. If a new value
        is selected and submitted, the value in the config is changed and the corresponding item
        in the serials table is updated accordingly. If the value is not changed, the item is left
        unchanged. The status of the serial connection is updated in the UI.

        :return:    nothing
        :rtype:     None
        """
        if not self.dmn.is_polling:
            selected = self.ui.serials_tw.selectedItems()
            if selected[0].parent():
                parent_node = selected[0].parent().text(0)
                base_node = selected[0].text(0)
                node_value = selected[0].text(1)
                default_index = 0
                if node_value in self.serial.parameters.get(base_node, {}):
                    default_index = self.serial.parameters[base_node].index(node_value)
                text, submitted = QInputDialog.getItem(
                    self, 
                    'Введите знечение', 
                    f'{base_node.capitalize()}:',
                    self.serial.parameters.get(base_node, {}),
                    default_index, 
                    editable=False
                    )
                if submitted:
                    self.config.set_serial_value(parent_node, base_node, text)
                    selected[0].setText(1, text)
                    self.map_serial_status()
                    self.ui.saveConfig.setEnabled(self.config.isChanged())

    def _delete_serial(self) -> None:
        """
        Deletes a serial port if it is not bound to any device configuration,
        otherwise shows an error message.

        :return:    nothing
        :rtype:     None
        """
        column = self.ui.serials_tw.currentColumn()
        text = self.ui.serials_tw.currentItem().text(column)
        if self.config.serial_is_binded(text):
            msgBox_fn(text='Этот портов связан с конфигурацией одного из устройств.\n'
                      'Переназначьте порт или удалите устройсиво и повторите попытку',
                      title='Не возможно завершить операцию', buttons=QMessageBox.Ok)
        else:
            value = msgBox_fn(text='Вы уверены?', title='Удаление последовательного порта')
            if value == 1024:
                self.config.delete_serial(text)
                self.ui.saveConfig.setEnabled(self.config.isChanged())
                self.load_serials()

    def map_serial_status(self) -> None:
        """
        Maps the status of the serial ports listed in the `serials_tw` table view widget.

        The method iterates through all the child items of the invisible root item of the 
        `serials_tw` table view and checks if the serial port is present in the system or not.
        If the serial port is not present in the system, it is marked red. If the serial port
        is present in the system but not in the configuration, it is marked gray. Otherwise,
        it is marked black.

        :return:    nothing
        :rtype:     None
        """
        root = self.ui.serials_tw.invisibleRootItem()
        for item in range(root.childCount()):
            color = 'black'
            serial = root.child(item)
            if serial.text(0) not in self.serial.fact:
                # если порта в системе нет
                color = 'red'
                self.map_serial_parameters(serial, color)
            elif serial.text(0) not in list(self.serial.config.keys()):
                # если порта в конфиге нет
                if self.map_serial_parameters(serial, 'gray'):
                    color = 'black'
                else:
                    color = 'gray'
            else:
                if self.map_serial_parameters(serial, 'gray'):
                    color = 'black'
                else:
                    color = 'gray'
            serial.setForeground(0, QBrush(QColor(color)))

    def map_serial_parameters(self, serial: QTreeWidgetItem, color: str) -> bool:
        """Maps the parameters of the given serial port and sets the color for the items.

        :param serial: The QTreeWidgetItem representing the serial port.
        :type serial: QTreeWidgetItem
        :param color: The color to set for the items.
        :type color: str
        :return: True if all the parameters are set, False otherwise.
        :rtype: bool
        """
        result = True
        child_count = serial.childCount()
        if child_count:
            for child_index in range(child_count):
                item = serial.child(child_index)
                if item.text(1) != 'None':
                    if serial.text(0) in self.serial.fact:
                        set_color = 'black'
                    else:
                        set_color = 'red'
                else:
                    set_color = color
                    result = False
                item.setForeground(0, QBrush(QColor(set_color)))
                item.setForeground(1, QBrush(QColor(set_color)))
        else:
            # raise Exception
            print('map_serial_parameters -> нет параметров')
        return result

    def save_config(self) -> None:
        """
        This method saves the current configuration to a file

        :return:    nothing
        :rtype:     None
        """
        self.config.save_to_file()
        self.ui.saveConfig.setEnabled(self.config.isChanged())

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handles the window close event by stopping the polling of data, waiting for the
        active threads to finish, and closing any open charts.

        :param event: A QCloseEvent object that represents the window close event
        :type event: QCloseEvent

        :return: nothing
        :rtype: None
        """
        _ = event
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.dmn.is_polling = False
        while self.dmn.threadpool.activeThreadCount():
            pass
        for key in list(self.widgets['charts'].keys()):
            self.widgets['charts'][key].close()
        QApplication.restoreOverrideCursor()
