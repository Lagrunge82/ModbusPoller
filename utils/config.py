"""
This module provides class for working with configuration and configuration file.

Minimal requirements
--------------------
* Python 3.8
"""

__author__ = "Ilya Molodkin"
__date__ = "2023-04-22"
__version__ = "1.0"
__license__ = "MIT License"



import traceback
import uuid
from typing import Dict, Tuple, List, Optional
import yaml

from utils.network import serial_ports


class Config:
    """
    A class that represents a configuration file.

    :param path: A string that represents the path to the configuration file.
    :type path: str

    :ivar _path: A string that represents the path to the configuration file.
    :ivar _config: A dictionary that stores the configuration file.
    :ivar _serial: A dictionary that stores serial ports configuration.
    :ivar _devices: A dictionary that stores devices configuration.

    :raises yaml.YAMLError: If the configuration file has YAML syntax errors.

    :return: An instance of the Config class.

    """
    def __init__(self, path: str):
        self._path = path
        self._config: Dict = self.get_config()
        if not self._config:
            self._config = {}

        self._serial: Dict = {}

        if 'network' not in self._config:
            self._config['network'] = {}
            self._config['network']['serial'] = {}
            for serial in serial_ports():
                self._serial[serial] = {'baud': None,
                                        'bits': None,
                                        'parity': None,
                                        'stop': None, }
        else:
            self._serial: Dict = self._config['network']['serial']

        if 'devices' not in self._config:
            self._config['devices'] = {}
        self._config['devices']: Dict = self._config['devices']
        # print(json.dumps(self._config, indent=2))

    def get_config(self) -> Dict:
        """
        Loads and returns the configuration file.

        :return: A dictionary that represents the configuration file
        :rtype: Dict
        """
        with open(self._path, "r", encoding='utf8') as stream:
            try:
                return yaml.safe_load(stream)
            except yaml.YAMLError as e:
                print(e)
                return None

    def set_serial_value(self, serial: str, parameter:str, value: str) -> None:
        """
        Sets the value of a serial port parameter.


        :param serial:      A string that represents the name of the serial port.
        :type serial:       str
        :param parameter:   A string that represents the name of the parameter to set.
        :type parameter:    str
        :param value:       The value to set.
        :type value:        str
        :return:            nothing
        :rtype:             None
        """
        if serial not in self._serial:
            self._serial[serial] = {}
        self._serial[serial][parameter.lower()] = value
        return True

    def delete_serial(self, serial: str) -> None:
        """
        Deletes a serial port.

        :param serial:  A string that represents the name of the serial port to delete.
        :type serial:   str
        :return:        nothing
        :rtype:         None
        """
        if serial in self._serial.keys():
            self._serial.pop(serial)
            print(True)
        else:
            print(False)

    def get_devices_data(self) -> List[List]:
        """
        Returns a list of lists containing the devices data in the following order:
        GUID, Устройство, Протокол, Активирован, Интерфейс.

        :return:    A list of lists with the devices parameters:
                    - name
                    - protocol
                    - active
                    - interface
        :rtype:     List[List]
        """
        result: List = []
        if self._config['devices']:
            for key, value in self._config['devices'].items():
                result.append((key,
                               value['name'],
                               value['protocol'],
                               value['active'],
                               value['interface'],))
        return sorted(result, key=lambda x: x[1])

    def get_device_data(self, guid: str) -> Optional[Dict]:
        """
        Retrieves the device information associated with the given GUID.

        :param guid:        The GUID of the device to retrieve information for.
        :type guid:         str
        :raises ValueError: If the specified GUID is not found in the configuration.
        :return:            A dictionary containing the device information if the GUID is found,
                            otherwise None.
        :rtype:             Optional[Dict]

        :Example:

        >>> device_data = self.get_device_data(guid)
        >>> print(device_data)
        {
            "active": true,
            "address": 1,
            "interface": null,
            "ip": "127.0.0.1",
            "name": "MBus Tools test",
            "protocol": "Modbus TCP",
            "registers": {
                "01 Read Coils": {
                    "0": {
                        "active": true,
                        "adjustments": [
                            {
                                "0": "No"
                            },
                            {
                                "1": "Yes"
                            }
                        ],
                        "code": "TCP0",
                        "format": "Signed",
                        "id": "8182d55d-3531-4594-b430-a643d8f3bc4c",
                        "name": "Test0"
                    },
                    ...
                },
                ...
            }
        }
        """
        try:
            if guid in self._config['devices'].keys():
                return self._config['devices'][guid]
            raise ValueError(
                'Error@Config.get_device_data.',
                f'Переданный guid {guid} не найден в конфиге'
            )
        except ValueError as e:
            print(f'{type(e).__name__} occurred, args={str(e.args)}\n{traceback.format_exc()}')
            return None

    def create_device_data(self, data: Dict) -> Optional[str]:
        """
        Creates a device data record in the _devices dictionary.

        :param data: A dictionary containing the following keys:
                    - protocol: A string representing the protocol used by the device.
                    - interface: A string representing the interface name.
                    - ip: A string representing the device IP address.
                    - address: A string representing the device address.
        :type data: Dict
        :return:    If successful, returns None. If a device with the same GUID already exists, 
                    returns a string indicating that the device already exists.
        :rtype:     Optional[str]
        """
        guid: str = str(
            uuid.uuid5(uuid.NAMESPACE_X500,
                       f"{data['protocol']}{data['interface']}{data['ip']}{data['address']}"))
        if self._config['devices']:
            if guid in self._config['devices'].keys():
                return 'Устройство с такими параметрами уже существует.'
        else:
            self._config['devices'] = {}
        # self._config['devices'][guid] = data
        self._config['devices'][guid] = data
        print('self._config--->>>', self._config)
        return None

    def change_device_data(self, guid: str, data: Dict) -> Optional[str]:
        """
        Changes the device data for the given `guid` with the provided `data`.

        :param guid:        The unique identifier of the device.
        :type guid:         str
        :param data:        A dictionary containing the updated device data.
        :type data:         Dict
        :raises ValueError: If the given `guid` is not found in the config.
        :raises ValueError: If device with the provided parameters already exists 
        :return:            Returns `None` if the device data is updated successfully, 
                            otherwise returns an error message.
        :rtype:             Optional[str]
        """
        result: Optional[str] = None
        rehashed_guid: str = str(
            uuid.uuid5(uuid.NAMESPACE_X500,
                       f"{data['protocol']}{data['interface']}{data['ip']}{data['address']}"))
        try:
            if guid == rehashed_guid:
                if guid in self._config['devices'].keys():
                    self._config['devices'][guid].update(data)
                    return None
                result = f'Переданный guid {guid} не найден в конфиге'
                raise ValueError(
                    'Error@Config.change_device_data.',
                    result
                )
            if rehashed_guid in self._config['devices'].keys():
                result = 'Устройство с такими параметрами уже существует.'
                raise ValueError(
                    'Error@Config.change_device_data.',
                    result
                )
            self._config['devices'][rehashed_guid] = self._config['devices'].pop(guid)
            self._config['devices'][rehashed_guid].update(data)
        except ValueError as e:
            print(f'{type(e).__name__} occurred, args={str(e.args)}\n{traceback.format_exc()}')
            return result
        return None

    def delete_device_data(self, guid: str) -> None:
        """
        Delete device data with specified guid from the internal _devices dictionary.

        :param guid: GUID of the device to delete.
        :type guid: str
        :return:    nothing
        :rtype:     None
        """
        self._config['devices'].pop(guid)

    def change_device_activity(self, guid: str) -> None:
        """
        Change the activity status of the device with the specified GUID.

        :param guid:    GUID of the device to change the activity status.
        :type guid:     str
        :return:        nothing
        :rtype:         None
        """
        self._config['devices'][guid]['active'] = not self._config['devices'][guid]['active']

    def get_device_registers_data(self, guid: str) -> List[Tuple]:
        """
        Get a list of tuples containing the register data for a device.

        :param guid: The GUID of the device to get the register data for.
        :type guid: str
        :raises ValueError: If a function retrieved from the config is not found in `funcs`.
        :return: A list of tuples containing the register data for the device:
                    - function name
                    - function number
                    - register address
                    - register data format
                    - unique code (unique notation for schemas, database fields, etc.)
                    - name
                    - active
                    - register id
        :rtype: List[Tuple]
        """
        registers = self.get_device_data(guid)['registers']
        funcs: List = ['01 Read Coils',
                       '02 Read Discrete Inputs',
                       '03 Read Holding Registers',
                       '04 Read Input Registers', ]

        data: List[Tuple] = []
        if registers:
            for func, func_registers in registers.items():
                if func_registers:
                    if func in funcs:
                        for reg_addr, reg_data in func_registers.items():
                            data.append((func,
                                         int(func[1:2]),
                                         reg_addr,
                                         reg_data['format'],
                                         reg_data['code'],
                                         reg_data['name'],
                                         reg_data['active'],
                                         reg_data['id'], ))
                    else:
                        raise ValueError(
                            'Error@Config.get_device_registers.',
                            f'Полученной из конфига функции {func} нет в func_dict'
                        )
        return sorted(data)

    def get_device_register_data(self, 
                                 guid: str, 
                                 func: str, 
                                 addr: int, 
                                 reg_id: str) -> Optional[Dict]:
        """
        Returns register data by the specified register ID from the device with the given GUID.

        :param guid: GUID of the device.
        :type guid: str
        :param func: _description_
        :type func: str
        :param addr: register address
        :type addr: int
        :param reg_id: register ID to search for.
        :type reg_id: str
        :return: dictionary containing the register data if found, otherwise None.
        :rtype: Optional[Dict]
        """
        device_data = self.get_device_data(guid)
        # if `func` provided
        if func:
            # if `addr` provided
            if addr:
                return device_data['registers'].get(func, {}).get(addr)
            # if `addr` is not provided
            for register in device_data['registers'].get(func, {}).values():
                if register['id'] == reg_id:
                    return register
        # if `addr` provided without `func`
        if addr:
            for registers in device_data['registers'].values():
                if registers.get(addr, {}).get('id') == reg_id:
                    return registers[addr]
        # if nothing provided
        for registers in device_data['registers'].values():
            for register in registers.values():
                if register['id'] == reg_id:
                    return register
        return None

    def create_register(self, guid: str, func: str, addr: int, data: Dict) -> bool:
        """
        Creates a new register for a given device and function.

        :param guid:        The GUID of the device to create the register for.
        :type guid:         str
        :param func:        The function of the register to create.
        :type func:         str
        :param addr:        The address of the register to create.
        :type addr:         int
        :param data:        The data of the register to create.
        :type data:         Dict
        :raises ValueError: If a register with the same address already exists for 
                            the given function and device.
        :return:            True if the register was created successfully, False otherwise.
        :rtype:             bool
        """
        registers = self._config['devices'][guid]['registers']
        if registers[func]:
            if addr in registers[func]:
                raise ValueError(
                    'Error@Config.create_register.',
                    f'Регистр с номером {addr} в функции {func} устройства {guid} уже существует.'
                )
        else:
            registers[func] = {}
        data['id'] = str(uuid.uuid4())
        registers[func][addr] = data
        return True

    def update_register(self, guid: str, func: str, addr: int, data: Dict) -> bool:
        """
        Updates the register data for a device with the given GUID, function code,
        and address, using the new register data provided. Returns True if the register
        was successfully updated, False otherwise.

        :param guid:        the GUID of the device containing the register to be updated.
        :type guid:         str
        :param func:        the function code of the register to be updated.
        :type func:         str
        :param addr:        the address of the register to be updated.
        :type addr:         int
        :param data:        the new register data to be used for the update.
        :type data:         Dict
        :raises ValueError: if the register with the given address already exists for
                            a different register ID.
        :return:            True if the register was successfully updated, False otherwise.
        :rtype:             bool
        """
        registers = self._config['devices'][guid]['registers']
        if not registers[func]:
            registers[func] = {}
        if addr not in registers[func]:
            registers[func][addr] = {}
        else:
            if data['id'] != registers[func][addr]['id']:
                raise ValueError(
                    'Error@Config.update_register.',
                    f'Регистр с номером {addr} в функции {func} устройства {guid} уже существует.'
                )
            if registers[func][addr] == data:
                print(
                    'Изменения не были  внесены.', 'data', data, 'register', registers[func][addr]
                )
                return False

        reg_addr_to_delete = ''
        for registers in self._config['devices'][guid]['registers'].values():
            if registers:
                for reg_addr, reg_data in registers.items():
                    if reg_data:
                        if reg_data['id'] == data['id']:
                            reg_addr_to_delete = reg_addr
                            break
                if reg_addr_to_delete:
                    del registers[reg_addr_to_delete]
                    break

        self._config['devices'][guid]['registers'][func][addr] = data
        return True

    def delete_register(self, guid: str, func: str, addr: str, reg_id: str) -> Optional[bool]:
        """
        Delete a register of the device with the given parameters from the configuration.

        :param guid:    A string representing the globally unique identifier of the device.
        :type guid:     str
        :param func:    A string representing the function of the register.
        :type func:     str
        :param addr:    A string representing the address of the register.
        :type addr:     str
        :param reg_id:  A string representing the globally unique identifier of the register.
        :type reg_id:   str
        :return:        A boolean value representing whether the register was deleted successfully,
                        None if the register was not found in the configuration.
        :rtype:         Optional[bool]
        """
        if self._config['devices'][guid]['registers'][func]:
            registers = self._config['devices'][guid]['registers'][func]
            if addr in registers:
                if registers[addr]['id'] == reg_id:
                    self._config['devices'][guid]['registers'][func].pop(addr)
                    return True
                # TODO `raise Exception` pylint: disable=fixme
        return None

    def change_register_activity(self, guid: str, func: str, addr: int, reg_id: int) -> bool:
        """
        Toggles the activity status of a register.


        :param guid:    The globally unique identifier of the device that contains the register.
        :type guid:     str
        :param func:    The function name.
        :type func:     str
        :param addr:    The address of the register.
        :type addr:     int
        :param reg_id:  The identifier of the register.
        :type reg_id:   int
        :return:        True if the register was found and its activity status was successfully
                        toggled, False otherwise.
        :rtype:         bool
        """
        if self._config['devices'][guid]['registers'][func]:
            if addr in self._config['devices'][guid]['registers'][func]:
                register = self._config['devices'][guid]['registers'][func][addr]
                if register['id'] == reg_id:
                    register = self._config['devices'][guid]['registers'][func][addr]
                    register['active'] = not register['active']
                    return True
                # raise Exception
        return False

    def isChanged(self) -> bool:
        """
        Check if the current config has been changed from the original configuration.

        :return:    A boolean value indicating if the current config has been changed from 
                    the original configuration.
        :rtype:     bool
        """
        return not self.get_config() == self._config

    def serial_is_binded(self, serial: str) -> bool:
        """
        Check if any device is binded to the given `serial` interface in the configuration.

        :param serial: The serial number to check.
        :type serial: str
        :return: `True` if any device is binded to the given `serial`, `False` otherwise.
        :rtype: bool
        """
        for device in self._config['devices'].values():
            if serial == device['interface']:
                return True
        return False

    def check_code_unique(self, code: str, reg_id: str = None) -> bool:
        """
        Check if the given code is unique in the registers of any device.

        :param code: The code to be checked.
        :type code: str
        :param reg_id: ID of the register to be ignored in the check, defaults to None
        :type reg_id: str, optional
        :return: True if the code is unique, False otherwise.
        :rtype: bool
        """
        code_list = [register['code'].lower() for device in self._config['devices'].values()
                     for registers in device['registers'].values() if registers
                     for register in registers.values() if reg_id != register['id']]

        return code.lower() in code_list

    def get_pollers(self) -> Dict:
        """
        Returns a dictionary containing all active devices and their respective poller settings
        and registers.

        :return: A dictionary containing device poller settings and their respective registers.
        :rtype: Dict

        :Example:

        >>> pollers = config.get_pollers()
        >>> print(pollers)
        {
            'device_guid_1': {
                'name': 'device_name_1',
                'settings': {
                    'protocol': 'RTU',
                    'port': '/dev/ttyS1',
                    'slave_id': 1,
                    'baud': 9600,
                    'bytesize': 8,
                    'parity': 'N',
                    'stopbits': 1,
                    'timeout': 1000},
                    'registers': {
                        1: [
                            {
                                'device': 'device_name_1',
                                'guid': 'device_guid_1',
                                'address': 0,
                                'id': 'register_id_1',
                                'code': 'register_code_1',
                                'name': 'register_name_1',
                                'format': 'register_format_1',
                                'adjustments': []
                            }
                        ]
                    }
                }
            },
            'device_guid_2': {
                'name': 'device_name_2',
                'settings': {
                    'protocol': 'TCP',
                    'ip': '192.168.1.1'
                },
                'registers': {
                    2: [
                        {
                            'device': 'device_name_2',
                            'guid': 'device_guid_2',
                            'address': 1,
                            'id': 'register_id_2',
                            'code': 'register_code_2',
                            'name': 'register_name_2',
                            'format': 'register_format_2',
                            'adjustments': []
                        }
                    ]
                }
            }
        }
        """
        result: Dict = {}
        for guid, device in self._config['devices'].items():
            if not device['active']:
                continue
            
            # get poller's registers
            registers = {}
            for func, raw_registers in device['registers'].items():
                if not raw_registers:
                    continue
                index = int(func[1])
                registers[index] = [register for addr, raw_register in raw_registers.items() if
                                    raw_register['active'] and (register := {
                                        'device': device['name'],
                                        'guid': guid,
                                        'address': addr,
                                        'id': raw_register['id'],
                                        'code': raw_register['code'],
                                        'name': raw_register['name'],
                                        'format': raw_register['format'],
                                        'adjustments': raw_register['adjustments']
                                    })]
                registers[index] = sorted(registers[index], key=lambda d: d['address'])
            
            # get poller's connection settings
            serial: Dict = self._serial.get(device['interface'], {})
            settings = {}
            if device['interface']:
                settings = {'protocol': 'RTU',
                            'port': device['interface'],
                            'slave_id': device['address'],
                            'baud': int(serial['baud']),
                            'bytesize': int(serial['bits'][0]),
                            'parity': serial['parity'][0],
                            'stopbits': int(serial['stop'][0]),
                            'timeout': 1000}
            elif device['ip']:
                settings = {'protocol': 'TCP', 'ip': device['ip']}
            result[guid] = {'name': device['name'],
                            'settings': settings,
                            'registers': registers}
        return result

    def save_to_file(self) -> bool:
        """
        Saves the current configuration to a YAML file.

        :return: True if the configuration is successfully saved, False otherwise.
        :rtype: bool
        """
        result: bool = False
        try:
            with open(self._path, "w", encoding='utf8') as stream:
                yaml.dump(self._config, stream, allow_unicode=True)
            result = True
        except yaml.YAMLError as e:
            print(f'{type(e).__name__} occurred, args={str(e.args)}\n{traceback.format_exc()}')
        return result
