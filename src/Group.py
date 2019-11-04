# coding=utf-8
# import Controller


# Acquisition strategy group, consisting of a set of controllers (plc) registers and variables
class Group:
    # Name group name, polling_interval collection interval 5.5 means 5.5 seconds
    # Vars: variable collection, by io (controller's register data)
    # Io: Register of the controller (plc), see ModbusIO class of ModbusIO.py
    def __init__(self, name='', interval=10000, io=None, vars=None):
        self.name = name
        if interval is None or interval <= 0:
            self.interval = 10000
        else:
            self.interval = interval
            
        self.read_backoff = 0

        if io is None:
            self.io = {}
        else:
            self.io = io


class PureGroup:
    def __init__(self, group):
        self.name = group.name
        self.polling_interval = group.interval
        self.uploading_interal = group.interval
        self.vars = group.io.values()

