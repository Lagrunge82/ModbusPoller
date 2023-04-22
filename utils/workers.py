"""
This module contains classes for running background tasks with signals to indicate progress and 
completion. The WorkerSignals class defines signals emitted during task execution.

The Worker class is a runnable class that emits signals indicating the progress of a background
task.
The PollingWorker class is a subclass of Worker that implements a polling worker for Modbus
communication.
"""

__author__ = "Ilya Molodkin"
__date__ = "2023-04-22"
__version__ = "1.0"
__license__ = "MIT License"

import time
from datetime import datetime
from typing import Callable, Dict, List, Optional

# import memory_profiler
from PySide6.QtCore import QThread, QObject, Signal, Slot, QRunnable, Property
# from guppy import hpy
# import tracemalloc

from utils.modbus import Poller

class WorkerSignals(QObject):
    """
    WorkerSignals class defines the signals emitted by a QRunnable worker.
    
    Attributes:
    finished (Signal[str]): Signal emitted when the worker has finished its task. The signal
                            parameter is a string containing a message to be passed along.
    error (Signal[tuple]): Signal emitted when an error occurs in the worker. The signal
                           parameter is a tuple containing an error message string and an error
                           code integer.
    result (Signal[dict]): Signal emitted when the worker has produced a result. The signal
                           parameter is a dictionary containing the result data.
    progress (Signal[int]): Signal emitted periodically to indicate the progress of the worker's
                            task. The signal parameter is an integer value between 0 and 100.
    """
    finished = Signal(str)
    error = Signal(tuple)
    result = Signal(dict)
    progress = Signal(int)


class Worker(QRunnable):
    """
    :class:             `Worker` is a runnable class that emits signals indicating the progress of 
                        a background task.

    :param guid:        a unique identifier for the task.
    :type guid:         str
    :param sleep:       the time, in milliseconds, that the task will sleep before finishing.
    :type sleep:        int
    :ivar signals:      an instance of `WorkerSignals` used to emit signals during task execution.
    :type signals:      WorkerSignals
    :ivar _poller:      a reference to a `Poller` instance used to monitor task progress 
                        (optional).
    :type _poller:      Optional[Poller]
    :ivar _exec_time:   the amount of time, in milliseconds, the task has been executing.
    :type _exec_time:   int
    :ivar result:       a dictionary containing the result of the task.
    :type result:       Dict

    .. note::
        To use the `Worker` class, first create an instance with the appropriate arguments, 
        and then submit it to a `QThreadPool` for execution.
    """
    def __init__(self, guid: str, sleep: int) -> None:
        super().__init__()
        self.signals = WorkerSignals()
        self.sleep = sleep
        self.guid = guid
        self._poller: Optional[Poller] = None
        self._exec_time: int = 0
        self.result: Dict = {'guid': self.guid}

    def __del__(self):
        print(f'{self} deleted.')

    @Slot()
    # @memory_profiler.profile
    def run(self):
        # self.signals.result.emit(self.result)
        if self._exec_time > self.sleep:
            self._exec_time = 0
        QThread.msleep(self.sleep - self._exec_time)
        # time.sleep(1)
        self._exec_time = 0


class PollingWorker(Worker):
    """
    :class:         `PollingWorker` is a subclass of :class:`Worker` that implements a polling 
                    worker for Modbus communication.

    :param guid:    A string representing the unique identifier for the worker.
    :type guid:     str
    :param sleep:   An integer representing the number of seconds to sleep between polling 
                    iterations.
    :type sleep:    int
    :param fn:      A callable object that returns a boolean value indicating whether polling should 
                    continue or not.
    :type fn:       Callable

    :ivar poller:   An instance of the :class:`Poller` class that is used to perform Modbus 
                    communication.

    :returns:       An instance of :class:`PollingWorker`.
    """
    def __init__(self, guid: str, sleep: int, fn: Callable) -> None:
        super().__init__(guid, sleep)
        self.polling = fn

    @property
    def poller(self) -> Poller:
        """
        Returns the Poller object associated with this instance.

        :return: A Poller object.
        :rtype: Poller
        """
        return self._poller
    
    @poller.setter
    @Slot(type(Poller))
    def poller(self, poller: Poller) -> None:
        self._poller = poller

    @Slot(int, bool)
    def writeSingleCoil(self, address: int, value: bool) -> None:
        """
        Writes a single coil value to the specified address using the associated Poller object.


        :param address: _descriptThe address of the coil to write to.ion_
        :type address: int
        :param value: The value to write to the coil.
        :type value: bool
        :return: A ModbusResponse object indicating the success or failure of the write operation.
        :rtype: ModbusResponse
        """
        self._poller.writeSingleCoil(address=address, value=value)

    @Slot(int, str, list, str, result=None)
    def writeRegisters(self, address: int, 
                       data_format: str, 
                       adj: List, 
                       value: str) -> None:
        """
        Writes one or more 16-bit registers to the specified address using the associated Poller 
        object.

        :param address: The address of the first register to write to.
        :type address: int
        :param data_format: The format of the data being written.
        :type data_format: str
        :param adj: A list of adjustment values to apply to the data being written.
        :type adj: List
        :param value: The value or values to write to the registers, as a string.
        :type value: str
        :return: A ModbusResponse object indicating the success or failure of the write operation.
        :rtype: ModbusResponse
        """
        encoded_value = self._poller.encode_value(value=value, 
                                                  data_format=data_format, 
                                                  adjustments=adj)
        if encoded_value is not None:
            self._poller.writeRegisters(address=address, value=encoded_value)

    @Slot()
    def run(self):
        self._poller.connect()
        while True:
            started_at = datetime.now()
            result: Dict = {'guid': self.guid,
                            'registers': self._poller.registers}
            # result: Dict = {'guid': self.guid,
            #                 'registers': [['0', '0', '0', '0', '0', '0', '0', '0', '0', True, '0', '0'],
            #                               ['0', '0', '0', '0', '0', '0', '0', '0', '0', True, '0', '0'],
            #                               ['0', '0', '0', '0', '0', '0', '0', '0', '0', True, '0', '0'], ]}
            self.signals.result.emit(result)
            self._exec_time = int(((datetime.now() - started_at).total_seconds()) * 1000)
            super().run()
            if self.polling() is False:
                break

        self._poller.disconnect()
        self.signals.finished.emit(self.guid)
