"""This module provides classes for working with table models."""

__author__ = "Ilya Molodkin"
__date__ = "2023-04-22"
__version__ = "1.0"
__license__ = "MIT License"


import os
import re
import operator
from typing import List, Optional

from PySide6 import QtGui
from PySide6.QtCore import QAbstractTableModel, Qt, SIGNAL, QModelIndex
from ui.widgets import Widget


class TableModel(QAbstractTableModel):
    """The TableModel class is used to display and modify data in a table
    :param parent: reference to the parent widget in which the class instance is created
    :type parent: Widget
    :param data: list of table data rows
    :type data: List
    :param header: The table header data
    :type header: List
    """
    def __init__(self, parent: Widget, data: List, header: List[str], *args) -> None:
        super().__init__(parent, *args)
        self._parent = parent
        self._data: List = data if data is not None else [[]]
        self.header = header if header is not None else []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """The rowCount method returns the number of rows in the data model
        :param parent:  PySide6.QtCore.QModelIndex
        :type parent:   PySide6.QtCore.QModelIndex

        :return:        Returns the number of rows under the given parent. When the parent is valid
                        it means that rowCount is returning the number of children of parent.
        :rtype:         int
        """
        _ = parent
        return len(self._data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """The columnCount method returns the number of columns in the data model
        :param parent:  PySide6.QtCore.QModelIndex
        :type parent:   PySide6.QtCore.QModelIndex

        :return:        Returns the number of columns for the children of the given parent. 
                        In most subclasses, the number of columns is independent of the parent.
        :rtype:         int

        """
        _ = parent
        return len(self.header)

    def data(self, index: QModelIndex, role: Qt.ItemDataRole) -> Optional[object]:
        """Returns the data stored in the data model for the specified index for display in a
        provided data view
        :param index:   Table cell index
        :type index:    QModelIndex
        :param role:    role of an item's data in a data model
        :type role:     Qt.ItemDataRole

        :return:        the data stored under the given role for the item referred to by the index.
        :rtype:         Optional[object]
        """
        if index.isValid():
            if role == Qt.DisplayRole:
                if len(self._data):
                    return self._data[index.row()][index.column()]
        return None

    def setData(self, index: QModelIndex, value, role: Qt.EditRole) -> bool:
        """Sets the role data for the item at index to value.

        :param index:   Table cell index
        :type index:    QModelIndex
        :param role:    role of an item's data in a data model
        :type role:     Qt.ItemDataRole

        :return:        true if successful; otherwise false.
        :rtype:         bool

        """
        if index.isValid():
            if role == Qt.EditRole:
                if self._data[index.row()][index.column()] != value:
                    self._data[index.row()][index.column()] = value
                    self.dataChanged.emit(index, index)
                return True
        return False

    def headerData(self,
                   section: int,
                   orientation: Qt.Orientation,
                   role: Qt.ItemDataRole) -> object:
        """Provides data for the horizontal and vertical headers of a table model
        :param section:     column id
        :type section:      int
        :param orientation: indicates whether the request is for a horizontal or vertical header
        :type orientation:  Qt.Orientation
        :param role:        specifies the type of data to be provided, default is DisplayRole
        :type role:         Qt.ItemDataRole

        :return:            data for the given role and section in the header with the specified 
                            orientation.
        :rtype:             object

        .. note:: the headerData method can be used to provide different types of data for different
            roles. E.g., you could provide tooltip text for the ToolTipRole or font information for
            the FontRole.
        """
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.header[section]
        return None

    def sort(self, column: int, order: Qt.SortOrder) -> None:
        """Sorts the model by column in the given order

        :param column:  column id to sort by
        :type column:   int
        :param order:   sorting order, Qt.AscendingOrder by default or Qt.DescendingOrder
        :type order:    Qt.SortOrder

        :return:        nothing
        :rtype:         None
        """
        self.emit(SIGNAL("layoutAboutToBeChanged()"))
        self._data = sorted(self._data, key=operator.itemgetter(column))
        if order == Qt.DescendingOrder:
            self._data.reverse()
        self.emit(SIGNAL("layoutChanged()"))

    def update_columns(self, data: List, columns: Optional[List[int]]) -> bool:
        """Update the values of the specified columns  in model data and emit a `dataChanged` signal
        :param data: A list of rows, where each row is a list of values
        :type data: List
        :param columns: A list of column indices to update
        :type columns: List[int]

        :return: True if the update was successful
        :rtype: bool
        """
        if columns is None:
            return False
        segments: List[List[QModelIndex], ] = []
        for col_index in columns:
            for row_index, row in enumerate(data):
                if self._data[row_index][col_index] != row[col_index]:
                    if not segments or \
                            segments[-1][1].column() != col_index or \
                            segments[-1][1].row() != row_index - 1:
                        segments.append([self.createIndex(row_index, col_index),
                                         self.createIndex(row_index, col_index)])
                    else:
                        segments[-1][1] = self.createIndex(row_index, col_index)
                    self._data[row_index][col_index] = row[col_index]
        for segment in segments:
            self.dataChanged.emit(*segment, [Qt.DisplayRole])
        return True


class StatusTableModel(TableModel):
    """The StatusTableModel class is used to display and modify data in status table"""
    def data(self, index: QModelIndex, role: Qt.ItemDataRole) -> Optional[object]:
        """
        Returns the data stored in the data model for the specified index for display in a
        provided data view
        :param index:   Table cell index
        :type index:    QModelIndex
        :param role:    role of an item's data in a data model
        :type role:     Qt.ItemDataRole

        :return:        the data stored under the given role for the item referred to by the index.
        :rtype:         Optional[object]
        """
        if index.isValid():
            if role == Qt.DecorationRole:
                path = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                    '..', 
                                                    'img'))
                if self._data[index.row()][1] is True:
                    filename = 'checkmark.png'
                elif self._data[index.row()][1] is False:
                    filename = 'ellipsis.png'
                else:
                    filename = 'cross.png'
                icon_path = os.path.abspath(os.path.join(path, filename))
                return QtGui.QIcon(icon_path)
            if role == Qt.TextAlignmentRole:
                return int(Qt.AlignCenter | Qt.AlignVCenter)
        return None


class DataTableModel(TableModel):
    """The DataTableModel class is used to display and modify data in data table
    :param parent: reference to the parent widget in which the class instance is created
    :type parent: Widget
    :param data: list of table data rows
    :type data: List
    :param header: The table header data
    :type header: List
    """
    def __init__(self, parent: Widget, data: List, header: List, *args, **kwargs) -> None:
        super().__init__(parent, data, header, *args, **kwargs)
        self.dataChanged.connect(self.dataChangedEvent)

    def dataChangedEvent(self, index: QModelIndex) -> None:
        """Method called when the data in the table changes

        :param index:  the index of the cell in which the change was committed
        :type index:   QModelIndex

        :return:        nothing
        :rtype:         None
        """

    def data(self, index: QModelIndex, role: Qt.ItemDataRole) -> Optional[object]:
        """Returns the data stored in the data model for the specified index for display in a
        provided data view
        :param index:   Table cell index
        :type index:    QModelIndex
        :param role:    role of an item's data in a data model
        :type role:     Qt.ItemDataRole

        :return:        the data stored under the given role for the item referred to by the index.
        :rtype:         Optional[object]
        """
        if index.isValid():
            if role == Qt.DisplayRole:
                if len(self._data):
                    return self._data[index.row()][index.column()]
            if role == Qt.TextAlignmentRole:
                if self._data[index.row()][6] is not None:
                    is_numerical: bool = re.match(r'^-?\d+(?:\.\d+)$', self._data[index.row()][5])
                    if index.column() == 6 and is_numerical:
                        return int(Qt.AlignRight | Qt.AlignVCenter)
                    if index.column() in [6]:
                        return int(Qt.AlignCenter | Qt.AlignVCenter)
        return None


class DevicesTableModel(TableModel):
    """The DevicesTableModel class is used to display and modify data in device table"""
    def data(self, index: QModelIndex, role: Qt.ItemDataRole) -> Optional[object]:
        """Returns the data stored in the data model for the specified index for display in a
        provided data view
        :param index:   Table cell index
        :type index:    QModelIndex
        :param role:    role of an item's data in a data model
        :type role:     Qt.ItemDataRole

        :return:        the data stored under the given role for the item referred to by the index.
        :rtype:         Optional[object]
        """
        if index.isValid():
            if role == Qt.DisplayRole:
                return self._data[index.row()][index.column()]
            if role == Qt.ForegroundRole:
                if not self._data[index.row()][3]:
                    return QtGui.QColor('silver')
            if role == Qt.BackgroundRole:
                if self._data[index.row()][4]:
                    if self._data[index.row()][4] not in self._parent.serial.fact:
                        return QtGui.QColor(255, 232, 232)
        return None


class RegistersTableModel(TableModel):
    """The RegistersTableModel class is used to display and modify data in register table"""
    def data(self, index: QModelIndex, role: Qt.ItemDataRole) -> Optional[object]:
        """Returns the data stored in the data model for the specified index for display in a
        provided data view
        :param index:   Table cell index
        :type index:    QModelIndex
        :param role:    role of an item's data in a data model
        :type role:     Qt.ItemDataRole

        :return:        the data stored under the given role for the item referred to by the index.
        :rtype:         Optional[object]
        """
        if index.isValid():
            if role == Qt.DisplayRole:
                return self._data[index.row()][index.column()]
            if role == Qt.TextAlignmentRole and index.column() == 2:
                return int(Qt.AlignCenter | Qt.AlignVCenter)
            if role == Qt.ForegroundRole:
                if not self._data[index.row()][6]:
                    return QtGui.QColor('silver')
        return None


class AdjustTableModel(TableModel):
    """The AdjustTableModel class is used to display and modify data in adjustment table"""
    def data(self, index: QModelIndex, role: Qt.ItemDataRole) -> Optional[object]:
        """Returns the data stored in the data model for the specified index for display in a
        provided data view
        :param index:   Table cell index
        :type index:    QModelIndex
        :param role:    role of an item's data in a data model
        :type role:     Qt.ItemDataRole

        :return:        the data stored under the given role for the item referred to by the index.
        :rtype:         Optional[object]
        """
        if index.isValid():
            if role == Qt.DisplayRole:
                value = self._data[index.row()][index.column()]
                if isinstance(value, float):
                    return f'{value:.2f}'
                return value
            if role == Qt.TextAlignmentRole and index.column() == 0:
                return int(Qt.AlignCenter | Qt.AlignVCenter)
        return None
