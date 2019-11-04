#coding=utf-8
import yaml


# Equipment class
class Device:
    def __init__(self, id=None, protocol='', address='', port='', machine_address='',
                 param=None, byte_order='abcd', groups=None, interval=10):
        # Communication protocol, mbtcp | mbrtu
        self.protocol = protocol
        # Address Serial port is localhost, Ethernet port is ip
        self.address = address
        # 端Port Serial port is the serial port number RS232: /dev/ttyS1; RS485: /dev/ttyO5, Ethernet: modbus tcp: 502
        self.port = port
        # Slave address modbus protocol family: 1~247
        self.machine_address = machine_address
        # self.polling_interval= polling_interval
        # Communication parameters, serial port is similar: 9600-8-N-1
        self.params = param
        # Register dword store byte order abcd | cdab | dcba | cdab
        self.byte_order = byte_order
        # Controller id
        self.id = id
        # Controller acquisition interval
        # self.interval = interval
        if groups is None:
            self.groups = {}
        else:
            self.groups = groups


class PureController:
    def __init__(self, controller):
        self.name = controller.id
        self.protocol = controller.protocol
        self.address = controller.address
        self.port = controller.port
        self.machine_address = controller.machine_address
        self.params = controller.params
        self.byte_order = controller.byte_order
        self.id = controller.id
        # self.io = {}
        # if controller.io is not None:
        #     for k, v in controller.io.items():
        #         self.io[k] = PureIO(v)
