# -*- coding:utf-8 -*-

import re
import modbus_tk
import modbus_tk.defines as cst


# General purpose PLC register class
class IO:
    # Address: address
    # _type: The data type stored in the register "bit/<signed/unsigned>word/<signed/unsigned>dword/fload"
    def __init__(self, address='40001', type='word', controller_id=None):
        self.address = address
        self.type = type
        # self.controller_id = controller_id


# PLC register class
class ModbusIO(IO):
    # Address register address
    # Type: The type of data stored in this register
    # controller_id; plc id
    def __init__(self, mb_id, address=40001, mb_type='word', desc='', writeable=None):
        IO.__init__(self, '', mb_type)
        #  获取 寄存器地址和读取寄存器数据的指令
        (self.mb_addr, self.command) = ModbusTools.transfer_addr(address)
        self.address = address
        self.len = ModbusTools.get_block_length(mb_type)
        self.mb_id = mb_id
        self.desc = desc
        self.writeable = writeable
        self.expression = "pass"


# class PureIO:
#     def __init__(self, io):
#         self.address = io.address
#         self.type = io.type


class ModbusTools(object):
    #Get register address and instructions to read register data
    @staticmethod
    def transfer_addr(address):
        var_addr = 0
        mb_type = None
        addr = int(address)
        if addr <= 10000:
            var_addr = addr - 1
            mb_type = cst.READ_COILS
        elif 10000 < addr <= 20000:
            var_addr = addr - 10001
            mb_type = cst.READ_DISCRETE_INPUTS
        elif 30000 < addr <= 40000:
            var_addr = addr - 30001
            mb_type = cst.READ_INPUT_REGISTERS
        elif 40000 < addr <= 50000:
            var_addr = addr - 40001
            mb_type = cst.READ_HOLDING_REGISTERS
        elif 100000 < addr <= 165535:
            var_addr = addr - 100001
            mb_type = cst.READ_DISCRETE_INPUTS
        elif 300000 < addr <= 365535:
            var_addr = addr - 300001
            mb_type = cst.READ_INPUT_REGISTERS
        elif 400000 < addr <= 465535:
            var_addr = addr - 400001
            mb_type = cst.READ_HOLDING_REGISTERS
        return var_addr, mb_type

    # Calculate the number of storage register addresses based on the data storage type
    @staticmethod
    def get_block_length(var_type):
        if var_type == 'word' or var_type == 'unsigned word' or var_type == "signed word":
            return 1
        elif var_type == 'bit':
            return 1
        elif re.match("bits:", var_type, re.M | re.I):
            temp = var_type.split(":")
            return int(temp[1])
        elif var_type == 'int' or var_type == 'unsigned int' or var_type == "signed int":
            return 2
        elif var_type == 'dword' or var_type == 'unsigned dword' or var_type == "signed dword":
            return 2
        elif var_type == 'float':
            return 2
        elif re.match("string", var_type, re.M | re.I):
            temp = var_type.split(":")
            return (int(temp[1]) / 2) + (0 if int(temp[1]) % 2 == 0 else 1)
        elif re.match("bytes", var_type, re.M | re.I):
            temp = var_type.split(":")
            return (int(temp[1]) / 2) + (0 if int(temp[1]) % 2 == 0 else 1)
        elif re.match("words", var_type, re.M | re.I):
            temp = var_type.split(":")
            return int(temp[1])
        elif re.match("dwords", var_type, re.M | re.I):
            temp = var_type.split(":")
            return int(temp[1]) * 2
        elif re.match("floats", var_type, re.M | re.I):
            temp = var_type.split(":")
            return int(temp[1]) * 2
        else:
            return 0

    # Get the length of the representation
    @staticmethod
    def convert_address(address):
        if address >= 10000:
            return str(address)
        else:
            vid = str(address)
            return vid.zfill(5)
