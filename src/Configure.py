# -*- coding:utf-8 -*-

import yaml
import json
import re
import Device
import Utilities
import Group
import ModbusIO
import logging


# Configuration parsing class
class Configure:
    # Devices dictionary key:controller id; Value: device class
    # Groups: group dictionary, each group represents a set of collection strategies
    def __init__(self, devices=None, groups=None, config=None):
        if devices is None:
            self.devices = {}
        else:
            self.devices = devices
        # if groups is None:
        #     self.groups = []
        # else:
        #     self.groups = groups
        if config is None:
            self.config = Config()

    # Parsing variable file
    def pars_yaml(self, filename):
        try:
            with open(filename, "r", encoding="utf8") as f:
                s = yaml.load(f)
        except Exception as e:
            logging.warning("open file error, filename : %s, try another method" % filename)
            s = yaml.load(file(filename))
        finally:
        # if True:
            # Initialize configuration information
            if 'config' in s:
                cfg = s['config']
                if 'version' in cfg:
                    self.config.version = cfg['version']
                if 'id' in cfg:
                    self.config.id = cfg['id']
                else:
                    self.config.id = ''
                if 'desc' in cfg:
                    self.config.desc = cfg['desc']
                if 'cloud' in cfg:
                    self.config.cloud = cfg['cloud']
                if 'mode' in cfg:
                    self.config.mode = cfg['mode']
                if 'others' in cfg:
                    self.config.others = cfg['others']
            # Initialize device information
            for dev in s['devices']:
                d = Device.Device()
                d.id = dev['id']
                d.protocol = dev['protocol']
                d.address = dev['address']
                d.port = str(dev['port'])
                d.machine_address = int(dev['machine_address'])
                if 'param' in dev:
                    d.param = dev['param']
                d.byte_order = dev['byte_order']

                for group in dev['groups']:
                    group_name = str(group['name'])
                    g = Group.Group(name=group_name, interval=group['interval'])
                    g.read_backoff = group["read_backoff"]
                    for var in group['vars']:
                        try:
                            address = var['address']
                            var_type = var['type']
                            var_id = var['id']
                            var_desc = var['desc']
                            if 'writeable' in var:
                                writeable = var['writeable']
                            else:
                                writeable = None

                            io = ModbusIO.ModbusIO(mb_id=var_id, address=address, mb_type=var_type,
                                                   desc=var_desc, writeable=writeable)
                            io.expression = var['expression']
                            g.io[var_id] = io
                        except Exception as e:
                            logging.warning('IO setting error:%s', e)
                    d.groups[group_name] = g
                self.devices[d.id] = d

    def findTheIo(self, g, ioMap, ioAddr):
        ioExp = ioAddr.split(".")
        controllerId = ioExp[0]
        ioId = ioExp[1]
        controller = self.devices[controllerId]
        if controllerId is None:
            print('Can not find the controller: %s' % controllerId)
        else:
            theIo = controller.io[ioId]
            if theIo is None:
                print('Can not find the io: ' + controllerId + "." + ioId)
            else:
                ioMap[controllerId + "." + ioId] = theIo

    def findIoInExp(self, group, ioMap, expression):
        if expression is not None or expression != "":
            varibales = re.findall(r'values\[[\"|\'][a-zA-Z0-9\_\-\s]+\.[a-zA-Z0-9\_\-]+[\"|\']\]', expression)
            for v in varibales:
                ioExp = v[8:len(v[0])-3]
                self.findTheIo(group, ioMap, ioExp)

    def toVarsJson(self):
        varsSetting = VarsSetting()
        groups = varsSetting.groups
        for group in self.groups:
            var = VarsGroup()
            var.group = group.name
            var.vars = group.vars
            groups.append(var)
        s = str(groups)  # json.dumps(groups, default=Utilities.Utility.serialize_instance)
        return s

    def toOrigJson(self):
        varsSetting = VarsSetting()
        groups = varsSetting.groups
        for k, v in self.devices.items():
            # print('controller name: ' + k)
            # varsSetting.devices.append(v)
            varsSetting.devices[k] = v
        for group in self.groups:
            var = VarsGroup()
            var.group = group.name
            var.vars = group.vars
            var.io = group.io
            groups.append(var)
        try:
            s = json.dumps(varsSetting, default=Utilities.Utility.serialize_instance)
        except Exception as e:
            s = json.dumps(varsSetting)
        return s

    def to_json(self):
        vs = VarsSetting()
        vs.config = self.config
        for k, d in self.devices.items():
            vs.devices[k] = (Device.PureController(d))

            if d.groups:
                for g in d.groups.values():
                    pg = Group.PureGroup(g)
                    vs.groups.append(pg)
        try:
            s = json.dumps(vs, default=Utilities.Utility.serialize_instance)
        except Exception as e:
            s = json.dumps(vs)
        return s


class Config:
    def __init__(self, version=1.0, id='', desc=None):
        self.version = version
        self.id = id
        self.desc = desc
        self.cloud = 'inhand'
        self.mode = 'mqtt'
        self.others = None

    def has_option(self, section, option):
        return True if self.others and section in self.others and option in self.others[section] else False

    def get(self, section, option, raw=False, vars=None):
        return self.others[section][option]

    def getint(self, section, option, raw=False, vars=None):
        return int(self.others[section][option])


# Variable group, each group
class VarsGroup:
    def __init__(self):
        self.group = ''
        self.vars = []
        self.io = []


class VarsSetting:
    def __init__(self):
        self.devices = {}
        self.groups = []
        self.config = None


if __name__ == '__main__':
    c = Configure()
    c.pars_yaml("../config.yaml")
    # print(json.dumps(c.devices, default=Utilities.Utility.serialize_instance))
    print(c.to_json())
