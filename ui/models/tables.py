"""This module provides classes for working with tables."""

__author__ = "Ilya Molodkin"
__date__ = "2023-04-22"
__version__ = "1.0"
__license__ = "MIT License"


from typing import Callable, List, Optional, Tuple
from PySide6.QtCore import Qt, QModelIndex
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QTableView, QHeaderView, QMenu, QFrame
from ui.models.tabmodel import (DataTableModel, DevicesTableModel,
                                RegistersTableModel, StatusTableModel,
                                TableModel, AdjustTableModel)
from ui.widgets import Widget


class BaseTable:
    """
    This module defines the BaseTable class that provides basic functionality to work with Pyside6's
    QTableView widget
    Initializes a QTableView widget and sets some basic properties like hiding the vertical header,
    disabling sorting, setting the default background color of the header to silver, etc.
    The class also provides methods to load, update and hide data in the table, and set the section
    resize mode of columns
    :param parent:      The parent widget that contains the QTableView widget
    :type parent:       Widget
    :param table:       The QTableView widget to initialize
    :type table:        QTableView
    :param header:      The table header data. Default is None
    :type header:       List, optional
    :param data:        The table data as a list of rows. Default is None
    :type data:         List, optional

    :ivar _parent:      The parent widget that contains the QTableView widget
    :ivar table:        The QTableView widget used in the class
    :ivar model:        An instance of the TableModel class that is used as the model of the
                        QTableView widget
    :ivar _header:      A list containing the column names
    :ivar _data:        A list containing the lists of values as rows
    :ivar _index_col:   The index of the column to use as the row index. Default is 0
    """
    def __init__(
            self,
            parent: Widget,
            table: QTableView,
            header: Optional[List] = None,
            data: Optional[List] = None
    ) -> None:
        self._parent = parent
        self.table = table
        self.model: TableModel
        self._header = []
        self._data = []
        self._index_col: int = 0
        self.table.setStyleSheet("QHeaderView::section { background-color:silver }")
        self.table.verticalHeader().setDefaultSectionSize(0)
        self.table.verticalHeader().hide()
        self.table.setSortingEnabled(False)
        self.load(header, data)

    def load(self, header: List = None, data: List = None) -> None:
        """Loads the table with the specified header and data
        :param header:  The table header data. Default is None
        :type header:   List
        :param data:    The table data as a list of rows. Default is None
        :type data:     List

        :return:        None
        :rtype:         None
        """
        self._header = header if header is not None else self._header
        self._data = data if data is not None else self._data
        model = self.model(self._parent, self._data, self._header)
        self.table.setModel(model)

    def update(
            self,
            header: List = None,
            data: List = None,
            columns: Optional[List] = None
    ) -> bool:
        """Updates the table with the specified header and data
        :param header:  The table header data. Default is None.
        :type header:   List
        :param data:    The table data as a list of rows. Default is None
        :type data:     List
        :param columns: List of columns to update
        :type columns:  List

        :return:        True if successful and False otherwise
        :rtype:         bool
        """
        self._header = header if header is not None else self._header
        self._data = data if data is not None else self._data
        model: TableModel = self.table.model()
        return model.update_columns(data=data, columns=columns)
    
    @property
    def header(self) -> List:
        """Gets or sets the table header data"""
        return self._header
    
    @header.setter
    def header(self, header: List) -> None:
        self._header = header

    @property
    def data(self) -> List:
        """Gets or sets the table data as a list of rows."""
        return self._data
    
    @data.setter
    def data(self, data: List) -> None:
        self._data = data
        self.load(data=data)

    @property
    def index(self) -> QModelIndex:
        """Gets the current index of the QTableView widget as QModelIndex instance"""
        return self.table.currentIndex()

    @property
    def isEmpty(self) -> bool:
        """Checks whether the table is empty or not and return True if empty and False otherwise"""
        return self.table.model().rowCount() == 0

    @property
    def row_count(self) -> int:
        """Gets the number of rows in the QTableView widget"""
        return int(self.table.model().rowCount())

    def hide(self, columns: List) -> None:
        """Hides the specified columns from the QTableView widget
        :param columns: A list of column indices to hide
        :type columns:  List

        :return: None
        """
        for column in columns:
            self.table.setColumnHidden(column, True)

    def setSectionResizeMode(self, columns: List, mode: QHeaderView.ResizeMode) -> None:
        """Sets the section resize mode of the specified columns

        :param columns: A list of column indices to set the section resize mode for
        :type columns:  List
        :param mode:    The section resize mode to set for the specified columns
        :type mode:     QHeaderView.ResizeMode

        :return:        nothing
        :rtype:         None
        """
        for column in columns:
            self.table.horizontalHeader().setSectionResizeMode(column, mode)

    def get_row_data(self, index: QModelIndex = None, col_index: int = None) -> Optional[str]:
        """Gets the data of the specified cell index or selected row and specified col_index
        :param index:       The index of the cell to get the data from. Default is None
        :type index:        QModelIndex
        :param col_index:   column index of the selected row to get data from if `index` is not
                            provided
        :type col_index:    int
        
        :return:            value of table cell corresponding to `index` if it is provided,
                            or of table cell corresponding to selected row and the specified column,
                            otherwise returns None
        :rtype:             Optional[str]

        :Example:

        >>> row_data = self.get_row_data(col_index=2)
        >>> if row_data is not None:
        ...     print("Данные из столбца 2: ", row_data)
        ... else:
        ...     print("Текущая строка не выбрана.")
        """
        model = self.table.model()
        if index:
            return model.data(index=index, role=Qt.DisplayRole)
        if col_index is not None:
            if col_index > -1:
                row_index: int = self.table.currentIndex().row()
                if row_index > -1:
                    return model.data(model.index(row_index, col_index), 0)
        return None


class ContextMenuMixin:
    """
    Mixin class that adds context menu functionality to a table widget.
    It provides a context menu when right-clicking on a table and calling certain functions when
    selecting menu items
    """
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.load_context_menu)
        self.actions: List = []

    def load_context_menu(self, position: Tuple) -> None:
        """Loads a context menu when right-clicking on a table in a GUI application
        :param position:    tuple representing the (x, y) coordinates of the cursor at the time the
                            table was right-clicked
        :type position:     Tuple
        
        :return:            nothing
        :rtype:             None
        """
        data = self.get_context_menu_data()
        menu = QMenu(self.table)
        for action_data in data:
            action = QAction(action_data['context'])
            action.triggered.connect(action_data['function'])
            if 'disabled' in action_data:
                action.setEnabled(not action_data['disabled'])
            self.actions.append(action)
            menu.addAction(action)
        menu.exec_(self.table.mapToGlobal(position))

    def get_context_menu_data(self) -> List:
        """
        This method should be overwritten in the class that uses this the mixin. It returns a list
        of dictionaries representing data for each menu item. Each dictionary must contain a
        'context' key, which represents the menu item's text, and a 'function' key, which represents
        the function that will be called when that menu item is selected. The method can also
        contain additional keys such as 'disabled' which disables the menu item

        :return: list
        of dictionaries representing data for each menu item
        :rtype: List
        """
        return []


class StatusTable(BaseTable):
    """StatusTable class is used to display a table of statuses in an application

    Args:
        parent (Widget): reference to the parent widget in which the class instance is created
        table (QTableView): link to a table of statuses
        data (List[Union[List, Tuple]]): list of table data rows
    """
    def __init__(self, parent: Widget, table: QTableView, data: List = None):
        self.model = StatusTableModel
        header = ['', '']
        super().__init__(parent=parent, table=table, header=header, data=data)
        self.hide([1])
        self.setSectionResizeMode([0], QHeaderView.Stretch)
        self.table.setFrameShape(QFrame.NoFrame)


class DataTable(ContextMenuMixin, BaseTable):
    """DataTable class is used to display a table with data in an application

    Args:
        parent (Widget): reference to the parent widget in which the class instance is created
        table (QTableView): link to a table with data
        data (List[Union[List, Tuple]]): list of table data rows
    """
    def __init__(self, parent: Widget, table: QTableView, data: List = None):
        self.model = DataTableModel
        header = ['Устройство', 'ID', 'Адрес', 'Наименование параметра', 'Код',
                  'Формат', 'Значение', 'Raw', 'Обновлено', 'changed', 'Ф-ия', 'GUID']
        super().__init__(parent=parent, table=table, header=header, data=data)
        self._index_col: int = 1
        self.table.setFrameShape(QFrame.NoFrame)
        self.hide([1, 2, 5, 7, 8, 9, 10, 11])
        self.setSectionResizeMode([2, 3], QHeaderView.Stretch)
        self.setSectionResizeMode([4, 6, 8], QHeaderView.ResizeToContents)
        self.table.doubleClicked.connect(self._parent.data_tb_doubleclicked)
        model = self.table.model()
        model.dataChanged.connect(lambda: print('Data changed'))

    def get_context_menu_data(self) -> List:
        """Returns a list of two dictionaries that are used to create a context menu in a data table

        :return: list of two dictionaries, representing data for each menu item
        :rtype: List
        """
        row_index = self.table.currentIndex().row()
        if row_index > -1:
            model = self.table.model()
            open_chart_disabled = model.data(
                model.index(row_index, 10), 0) in [1, 2]
            set_value_disabled = model.data(
                model.index(row_index, 10), 0) in [2, 4]
            return [{'context': 'Открыть график',
                     'function': self._parent.data_tb_open_chart,
                     'disabled': open_chart_disabled},
                    {'context': 'Задать значение',
                     'function': self._parent.data_tb_set_value,
                     'disabled': set_value_disabled}, ]
        return []


class DeviceTable(ContextMenuMixin, BaseTable):
    """DeviceTable class is used to display a table with devices in an application

    Args:
        parent (Widget): reference to the parent widget in which the class instance is created
        table (QTableView): link to a table of statuses
        data (List[Union[List, Tuple]]): list of table data rows, default is None
    """
    def __init__(self, parent: Widget, table: QTableView, data: List = None):
        self.model = DevicesTableModel
        header = ['GUID', 'Устройство', 'Протокол', 'Активирован', 'Интерфейс', ]
        data = parent.config.get_devices_data() if data is None else data
        super().__init__(parent=parent, table=table, header=header, data=data)
        self.table.doubleClicked.connect(self._parent.edit_device)
        self.setSectionResizeMode([1], QHeaderView.Stretch)
        self.hide([0, 3, 4])

    def load(self, header: List = None, data: List = None) -> None:
        """Loads the table with the specified header and data
        :param header:  The table header data. Default is None
        :type header:   List
        :param data:    The table data as a list of rows. Default is None
        :type data:     List

        :return:        nothing
        :rtype:         None
        """
        data = self._parent.config.get_devices_data() if data is None else data
        super().load(header=header, data=data)
        self.table.selectionModel().selectionChanged.connect(self.load_registers)
        self._parent.ui.saveConfig.setEnabled(self._parent.config.isChanged())

    def load_registers(self) -> None:
        """
        Checks if register table is already created and if it is - runs the load() method of the
        register table to update its contents
        """
        if 'registers_tb' in self._parent.tables:
            self._parent.tables['registers_tb'].load()

    def get_context_menu_data(self) -> List:
        """
        Returns a list of three dictionaries that are used to create a context menu in a device
        table

        :return: list of three dictionaries, representing data for each menu item
        :rtype: List
        """
        row_index = self.table.currentIndex().row()
        if row_index > -1:
            model = self.table.model()
            activate_context: str = 'Деактивировать' if model.data(
                model.index(row_index, 3), 0) else 'Активировать'
            # if application is polling - disable menu items
            disabled: bool = self._parent.dmn.is_polling

            return [{'context': activate_context,
                     'function': self._parent.devices_tb_context_act, 
                     'disabled': disabled},
                    {'context': 'Изменить',
                     'function': self._parent.edit_device,
                     'disabled': disabled},
                    {'context': 'Удалить',
                     'function': self._parent.delete_device, 
                     'disabled': disabled}, ]
        return []


class RegisterTable(ContextMenuMixin, BaseTable):
    """RegisterTable class is used to display a table with registers in an application

    Args:
        parent (Widget): reference to the parent widget in which the class instance is created
        table (QTableView): link to a table of statuses
        data (List[Union[List, Tuple]]): list of table data rows, default is None
    """
    def __init__(self, parent: Widget, table: QTableView, data: List = None):
        self.model = RegistersTableModel
        header = ['Название функции', 'Код ф-ии', 'Регистр', 'Формат', 'Код',
                  'Наименование', 'Активирован', 'ID', ]
        super().__init__(parent=parent, table=table, header=header, data=data)
        self.table.doubleClicked.connect(self._parent.edit_register)
        self.setSectionResizeMode([0, 2, 4], QHeaderView.ResizeToContents)
        self.setSectionResizeMode([5], QHeaderView.Stretch)
        self.hide([1, 3, 6, 7])

    def load(self, header: List = None, data: List = None) -> None:
        """Loads the table with the specified header and data
        :param header:  The table header data. Default is None
        :type header:   List
        :param data:    The table data as a list of rows. Default is None
        :type data:     List

        :return:        nothing
        :rtype:         None
        """
        if data is None:
            guid = self._parent.tables['devices_tb'].get_row_data(col_index=0)
            data = self._parent.config.get_device_registers_data(guid) if guid else []
        super().load(header=header, data=data)
        self._parent.ui.saveConfig.setEnabled(self._parent.config.isChanged())

    def get_context_menu_data(self) -> List:
        """
        Returns a list of three dictionaries that are used to create a context menu in a register
        table

        :return: list of three dictionaries, representing data for each menu item
        :rtype: List
        """
        row_index = self.table.currentIndex().row()
        if row_index > -1:
            model = self.table.model()
            activate_context = 'Деактивировать' if model.data(
                model.index(row_index, 6), 0) else 'Активировать'
            disabled: bool = self._parent.dmn.is_polling

            return [{'context': activate_context,
                     'function': self._parent.registers_tb_context_act, 
                     'disabled': disabled},
                    {'context': 'Изменить',
                     'function': self._parent.edit_register,
                     'disabled': disabled},
                    {'context': 'Удалить',
                     'function': self._parent.delete_register, 
                     'disabled': disabled}, ]
        return []

class AdjustTable(BaseTable):
    """Defines a table for displaying a list of operations for adjustments"""
    def __init__(self, parent: Widget, table: QTableView, edit_adjustment_fn: Callable):
        self.model = AdjustTableModel
        header = ['Исходное', 'Преобразованное']
        data = []
        super().__init__(parent, table, header, data)
        self.setSectionResizeMode([0, 1], QHeaderView.Stretch)
        self.table.doubleClicked.connect(edit_adjustment_fn)
