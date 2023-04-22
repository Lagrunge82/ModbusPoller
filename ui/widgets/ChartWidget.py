"""This module provides class for working with Chart Widget Window."""

__author__ = "Ilya Molodkin"
__date__ = "2023-04-22"
__version__ = "1.0"
__license__ = "MIT License"

import os
from typing import Optional

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QColorDialog,
                               QGraphicsLineItem, QGraphicsTextItem)
from PySide6.QtGui import QIcon, QCloseEvent, QPainter, QPen, QMouseEvent  # , Qt
from PySide6.QtCore import QDateTime, Qt, QSize
from PySide6.QtCharts import QChart, QChartView, QSplineSeries, QDateTimeAxis, QValueAxis

from ui.widgets import Widget
from ui.widgets.Mixins import LoadUiMixin
from utils.utils import notZero


class ChartWidget(QWidget, LoadUiMixin):
    """The `ChartWidget` class is used to display a chart window
    :param parent: reference to the parent widget in which the class instance is created
    :type parent: Widget
    """
    def __init__(self, parent: Widget = None) -> None:
        super().__init__()
        self.parent: Widget = parent
        self.reg_id: str = self.parent.tables['data_tb'].get_row_data(col_index=1)

        self.ui = self.load_ui(ui_file="ChartWidget.ui")
        self.create_chart()
        self.configure_controls()

    def create_chart(self) -> None:
        """Creates and configures all elements of the chart

        :return:    nothing
        :rtype:     None
        """
        # Create chart
        self.ui.chart_widget.setContentsMargins(0, 0, 0, 0)
        chart_lay = QVBoxLayout(self.ui.chart_widget)
        chart_lay.setContentsMargins(0, 0, 0, 0)
        self.chart = QChart()
        chart_view = QChartView(self.chart)
        chart_view.setRenderHint(QPainter.Antialiasing)  #
        chart_view.setContentsMargins(0, 0, 0, 0)
        chart_lay.addWidget(chart_view)

        # Create series
        name: str = self.parent.tables['data_tb'].get_row_data(col_index=3)
        code: str = self.parent.tables['data_tb'].get_row_data(col_index=4)
        self.series = QSplineSeries()
        self.series.setName(f'[{code}] {name}')
        self.chart.addSeries(self.series)

        # X Axis Settings
        axis_x = QDateTimeAxis()
        axis_x.setTickCount(13)
        axis_x.setLabelsAngle(-90)
        axis_x.setFormat("hh:mm:ss")
        axis_x.setMax(QDateTime.currentDateTime())
        axis_x.setMin(QDateTime.currentDateTime().addSecs(-60))
        self.chart.addAxis(axis_x, Qt.AlignBottom)
        self.series.attachAxis(axis_x)

        # Y1 Axis Settings
        axis_y1 = QValueAxis()
        axis_y1.setTickCount(7)
        axis_y1.setLabelFormat("%i")
        # axis_y1.setTitleText("Температура, C")
        axis_y1.setMin(0)
        axis_y1.setMax(10)
        self.chart.addAxis(axis_y1, Qt.AlignLeft)
        self.series.attachAxis(axis_y1)

        # Configure crosshair
        self.line: Optional[QGraphicsLineItem] = None
        self.label: Optional[QGraphicsTextItem] = None
        chart_view.mouseMoveEvent = self.mouseMoveEvent

    def configure_controls(self) -> None:
        """Configures the user interface controls

        :return:    nothing
        :rtype:     None
        """
        # Configure controls
        self.ui.color_btn.clicked.connect(self.select_color)
        path = os.path.abspath(os.path.join(
            os.path.dirname(os.path.realpath(__file__)), '..', 'img'))
        icon_path = os.path.abspath(os.path.join(path, 'rgb.png'))
        self.ui.color_btn.setIcon(QIcon(icon_path))
        self.ui.color_btn.setIconSize(QSize(32, 32))
    
    @property
    def axis_x(self) -> QDateTimeAxis:
        """Returns the horizontal (X) axis of the chart.

        :return: The horizontal (X) axis of the chart.
        :rtype: QDateTimeAxis
        """
        return self.chart.axes(Qt.Horizontal)[0]
    
    @property
    def axis_y(self) -> QValueAxis:
        """Returns the vertical (Y) axis of the chart.

        :return: The vertical (Y) axis of the chart.
        :rtype: QValueAxis
        """
        return self.chart.axes(Qt.Vertical)[0]

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """
        The method tracks the movement of the cursor within the plotting field and draws a line,
        which helps to determine the value on the y-axis.

        :return:    nothing
        :rtype:     None
        """
        pos = event.pos()
        if (self.chart.plotArea().x() <= pos.x() <= self.chart.plotArea().bottomRight().x() and
            self.chart.plotArea().y() <= pos.y() <= self.chart.plotArea().bottomRight().y()):
            if self.line is None:
                self.line = QGraphicsLineItem(self.chart)  # pylint: disable=attribute-defined-outside-init
                self.line.setPen(QPen('#ff8800'))
                self.line.setZValue(2)
            if self.label is None:
                self.label = QGraphicsTextItem(self.chart)  # pylint: disable=attribute-defined-outside-init
                self.label.setTextWidth(50)
                self.label.setZValue(1000)
                self.label.setHtml(f'<div style="background:#ff8800; color:white;">{0:.2f}</p>')
            # Переводим позицию мыши на координаты графика
            chart_pos = self.chart.mapToValue(pos)
            # Переводим позицию мыши на координаты плота
            plot_pos = self.chart.mapToPosition(chart_pos, self.series)
            # Обновляем положение линии
            self.line.setLine(0, plot_pos.y(), self.chart.plotArea().width(), plot_pos.y())
            self.line.setPos(self.chart.plotArea().x(), 0)
            self.label.setPos(self.chart.plotArea().x(), plot_pos.y() - 25)
            # расчитываем значение по оси Y в точке нахождения курсора
            y_min: int = self.axis_y.min()
            y_max: int = self.axis_y.max()
            plot_h = self.chart.plotArea().height()
            plot_y = self.chart.plotArea().y()
            plot_pos_y = plot_pos.y()
            y_value = y_min + (y_max - y_min) * (plot_h - (plot_pos_y - plot_y)) / plot_h
            self.label.setHtml(f'<div style="background:#ff8800; color:white;">{y_value:.2f}</p>')
        else:
            if self.line is not None:
                scene = self.line.scene()
                if scene is not None:
                    scene.removeItem(self.line)
                    self.line = None  # pylint: disable=attribute-defined-outside-init
            if self.label is not None:
                scene = self.label.scene()
                if scene is not None:
                    scene.removeItem(self.label)
                    self.label = None  # pylint: disable=attribute-defined-outside-init

    def select_color(self) -> None:
        """The method opens the color picker dialog and sets the graphic to the selected color

        :return:    nothing 
        :rtype:     None
        """
        color = QColorDialog.getColor()
        if color.isValid():
            self.series.setColor(color)

    def add_point(self, axis_x_val: float, axis_y_val: float) -> None:
        """
        Add a new data point to the chart and update the chart ranges
        :param axis_x_val: The value for the x-axis of the data point as a float
        :param axis_y_val: The value for the y-axis of the data point as a float
        :return: None

        This method updates the value input and series data for the chart. If there are more than 61
        data points in the series, the oldest data point is removed. Then, the method updates the
        ranges of the x and y axes for the chart. The x-axis range is updated to include the
        current time and the previous 60 seconds. The y-axis range is updated to include the current
        data point as well as any previously existing data points that are within 10% of the new
        maximum y-value.
        """
        # update the value input and series data for the chart
        self.ui.value_input.setText(str(axis_y_val))
        self.series.append(axis_x_val, axis_y_val)

        # remove the oldest data point if there are more than 61 data points
        if self.series.count() > 61:
            self.series.remove(0)

        # update the ranges of the x and y axes for the chart
        x_min = max(QDateTime.currentDateTime().addSecs(-60), self.axis_x.min())
        x_max = max(QDateTime.currentDateTime(), self.axis_x.max())
        y1_min = min(axis_y_val, int(self.axis_y.min()))
        # y1_max = max(axis_y_val * 1.1, int(self.axis_y.max()))
        y1_max = notZero(max(axis_y_val * 1.1,
                             max((point.y() for point in self.series.points())) * 1.1
                             ), int(self.axis_y.max()))

        self.axis_x.setRange(x_min, x_max)
        self.axis_y.setRange(y1_min, y1_max)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handles the window close event, deletes its own instance in parent's variable.

        :param event: A QCloseEvent object that represents the window close event
        :type event: QCloseEvent

        :return: nothing
        :rtype: None
        """
        _ = event
        self.parent.widgets['charts'].pop(self.reg_id)
