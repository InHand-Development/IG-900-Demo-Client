# -*- coding:utf-8 -*-

import serial
import json
import libevent
from RouterInfo import RouterInfo
from Logger import logger
from modbus_tk import modbus_tcp, modbus_rtu, modbus

RS232_PORT = '/dev/ttyO1'
RS485_PORT = '/dev/ttyO3'


class CtrlMgmt(object):
    def __init__(self, base, controllers, _pub_callback):
        self.masters = dict()
        self.base = base
        self.controllers = controllers
        self._pub_callback = _pub_callback
        self.siteinfo = []
        self.rs232 = None
        self.rs485 = None
        # Configuration upload
        self.config_timer = libevent.Timer(
            self.base, self._config_timer_handler, userdata=None)
        self.init_controller()

    # Initialize controller communication tasks
    def init_controller(self):
        # isright = False
        for k, v in self.controllers.items():
            controller = v
            if controller.protocol == 'mbtcp':
                try:
                    self.register_ethernet_device(controller.protocol, controller.id, ip=controller.address,
                                                          port=controller.port, description=controller.name)
                    #Establish modubs tcp collection task
                    self.masters[controller.id] = modbus_tcp.TcpMaster(controller.address, int(controller.port), 10)
                    logger.debug(
                        "A Connection is eastablished with the mbtcp controller:" + controller.address)
                except modbus.ModbusError as exc:
                    logger.debug("error %s- Code=%d", exc, exc.get_exception_code())
            elif controller.protocol == 'mbrtu':
                try:
                    # Establish modbus rtu collection task
                    params = controller.param.split("-")
                    baudrate = int(params[0])
                    bs = int(params[1])
                    parity = str(params[2])
                    stopbits = int(params[3])
                    self.register_serial_device(controller.protocol, controller.id, controller.name,
                                                controller.port, speed=baudrate, databit=bs,
                                                stopbit=stopbits, parity=parity, xonxoff="off")
                    logger.debug(':%d %d %s %d', baudrate, bs, parity, stopbits)
                    if controller.port == RS232_PORT:
                        if self.rs232 is None:
                            self.rs232 = serial.Serial(port=RS232_PORT,
                                                       baudrate=baudrate,
                                                       bytesize=bs,
                                                       parity=parity,
                                                       stopbits=stopbits,
                                                       xonxoff=0)
                        master = modbus_rtu.RtuMaster(self.rs232)
                        master.set_timeout(1.0)
                        master.set_verbose(True)
                        self.masters[controller.id] = master
                    elif controller.port == RS485_PORT:
                        if self.rs485 is None:
                            self.rs485 = serial.Serial(port=RS485_PORT,
                                                       baudrate=baudrate,
                                                       bytesize=bs,
                                                       parity=parity,
                                                       stopbits=stopbits,
                                                       xonxoff=0)
                        master = modbus_rtu.RtuMaster(self.rs485)
                        master.set_timeout(1.0)
                        master.set_verbose(True)
                        self.masters[controller.id] = master

                    logger.debug("A Connection is eastablished with the mbrtu controller:" + controller.port)
                except modbus.ModbusError as exc:
                    logger.debug("error %s- Code=%d", exc, exc.get_exception_code())

    def _config_timer_handler(self, evt, userdata):
        topic = "InMB/site/info"
        if self._pub_callback(topic, json.dumps(self.siteinfo), 1):
            logger.info("Send registered device information: %s" % self.siteinfo)
        else:
            self.config_timer.add(10)

    def register_ethernet_device(self, protocol, id, ip, port, description=None):
        try:
            device_info = dict()
            device_info['type'] = "Ethernet"
            device_info['protocol'] = protocol
            device_info['description'] = description
            device_info['id'] = id
            device_prop = dict()
            device_prop['status'] = "down"
            device_prop['ip'] = ip
            device_prop['port'] = port
            if description is None:
                device_prop['description'] = ""
            else:
                device_prop['description'] = description
            device_info['property'] = device_prop

            ri = RouterInfo(self.base)
            conn_sites = json.loads(ri.get_connect_device())
            if len(conn_sites):
                for conn_site in conn_sites:
                    if conn_site['ip'] == device_info['property']['ip']:
                        device_info['property']['status'] = "up"
                        if device_info['property']['description'] is None and conn_site['hostname'] != "":
                            device_info['property']['description'] = conn_site['hostname']
            self.siteinfo.append(device_info)
            return True
        except Exception as e:
            logger.warn("register ethernet device error %s, payload %s" % (e.__str__(), device_info))
            return False

    def register_serial_device(self, protocol, id, description, dev, speed=9600, databit=8, stopbit=1, parity="N",
                               xonxoff="off"):
        try:
            if dev == '/dev/ttyO1':
                type = 'RS232'
            elif dev == '/dev/ttyO3':
                type = 'RS485'
            else:
                logger.info("serial dev is incorrect, %s", dev)
                return False
            device_info = dict()
            device_info['type'] = type
            device_info['protocol'] = protocol
            device_info['description'] = description
            device_info['id'] = id
            device_prop = dict()
            device_prop['databit'] = databit
            device_prop['stopbit'] = stopbit
            device_prop['parity'] = parity
            device_prop['xonxoff'] = xonxoff
            device_prop['speed'] = speed
            device_prop['dev'] = dev
            device_info['property'] = device_prop
            self.siteinfo.append(device_info)
            return True
        except Exception as e:
            logger.warn("register serial device error %s, payload %s" % (e.__str__(), device_info))
            return False
