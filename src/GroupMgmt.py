# -*- coding:utf-8 -*-
import re
import time
import json
import libevent
import modbus_tk.defines as cst

from Utilities import Utility
from MessageChannel import InSub
from Logger import logger
from Cache import FIFOCache


class GroupMgmt(object):
    def __init__(self, base, device, master, groups, mq_publish_callback=None, mode='norm', cloud='inhand'):
        self.base = base
        self.master = master
        self.device = device
        self.groups = groups
        self.readTimerEvt = list()
        self.run_mode = mode
        self.cloud = cloud
        self.mq_publish_callback = mq_publish_callback
        # Register connection callback method
        self.msgWriteMBSub = InSub(self.base)
        self.msgWriteMBSub.addSmsHandle(self._sms_write_mb_data)

        self.init_groups()

    # Initialize the collection policy task
    def init_groups(self):
        is_right = False
        for name, group in self.groups.items():
            logger.debug("ModbusHadle.initGroups:group=" + name)
            mbpoll = GroupExtHandle(self.base, self.device, self.master,
                                    group, self.mq_publish_callback, self.run_mode, self.cloud)
            self.readTimerEvt.append(mbpoll)
            is_right = is_right or True
            for var in group.io.values():
                if var.writeable is not None:
                    logger.info("find writeable var id %s" % var.mb_id)
                else:
                    logger.info("not find writeable var id %s" % var.mb_id)
        return is_right

    def _sms_write_mb_data(self, val):
        try:
            # SMS type: "set SP1=1"
            val = list(val)[1]
            if "set" in val.lower():
                dat = val.split(" ", 1)[1]
                addr = dat.split("=")[0]
                val = dat.split("=")[1]
                time_str = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(time.time()))
                self.writehandle({"timestamp": time_str, "id": addr, "val": val})
        except Exception as e:
            logger.debug("SMS data error in GroupExtHandle:%s" % e)

    # Write controller task
    def writehandle(self, message):
        try:
            for msg in message:
                for mbpoll in self.readTimerEvt:
                    logger.info("write msg is id %s value %s ts %s" % (
                                     msg['id'], msg['val'], msg['timestamp']))
                    mbpoll.write_instant_value(msg)
        except Exception as e:
            logger.debug("write data error in GroupExtHandle:%s" % e)


# Strategy collection task class
class GroupExtHandle(object):
    def __init__(self, base, device, master, group, mq_publish_callback=None, run_mode='norm', cloud='inhand'):
        self.base = base
        self.timer = libevent.Timer(self.base, self.timer_handler, userdata=None)
        # 要采集的控制器
        self.device = device
        # mb实例
        self.master = master
        # 本地采集任务策略
        self.group = group
        self.mq_publish_callback = mq_publish_callback
        self.run_mode = run_mode
        self.cloud = cloud
        self.rt_data_buffer = FIFOCache(size=60)
        if self.cloud == 'inhand':
            self.upload_vars = self.upload_vars_to_inhand
        else:
            self.upload_vars = self.upload_vars_to_cloud

    # Traversing this group io, reading data from the controller's period register
    def read_instant_value(self, values, timestamp):
        stime = time.time()
        for k, v in self.group.io.items():
            gd = None
            try:
                gd = ModbusHandle.read_value(self.master, self.device, v)

                # transfer modbus to other protocol
                if self.run_mode == "transform":
                    self.mq_publish_callback("transform/modbus/read/%s" % k, json.dumps(gd), 0, False)
                    continue

                logger.debug("Group: %s |Time: %s |Address: %s |Value: %s |TimeUse: %s" %
                             (self.device.id, timestamp, v.address, gd, (time.time() - stime)))

                values["values"][k] = eval(v.expression)
                time.sleep(self.group.read_backoff)
            except Exception as e:
                logger.debug("Read error@%s:%s" % (self.device.address, e))
                continue
        # logger.info("End read, time use: %s" % (time.time()-stime))

    def write_instant_value(self, msg):
        for io in self.group.io.values():
            try:
                if io.mb_id == msg["id"] and io.writeable is not None:
                    logger.debug("find id %s write value %s" % (io.mb_id, msg["val"]))
                    value = msg["val"]
                    ModbusHandle.write_value(io, value, self.master, self.device.id)
                    break
            except Exception as e:
                logger.debug("Write error @ %s: %s" % (io.mb_id, e))

    def mq_publish_recursive(self, topic, payload, qos):
        if not self.mq_publish_callback(topic, payload, qos):
            logger.debug("The session is disconnected, we can not upload the data.")
            self.rt_data_buffer.put(payload)
            return   
        logger.info("Upload data: %s" % payload)
        while not self.rt_data_buffer.isEmpty():
            payload = self.rt_data_buffer.get()
            if self.mq_publish_callback(topic, payload, qos):
                logger.info("Upload data: %s (rt)" % payload)
            else:
                logger.debug("The session is disconnected, we can not upload the rt-data.")
                self.rt_data_buffer.put(payload)
                break
    # 将本次采集io上传或发生断线时缓存到内存
    def upload_vars_to_inhand(self, values, timestamp):
        if len(values['values']) > 0:
            try:
                jstr = json.dumps(values['values'], Utility.serialize_instance)
            except Exception as e:
                jstr = json.dumps(values['values'])
            self.mq_publish_recursive("v1/devices/me/telemetry", jstr, 1)
           
            # Cache to memory when this collection is uploaded or disconnected

    def upload_vars_to_cloud(self, values, timestamp):
        if len(values) > 0:
            try:
                jstr = json.dumps(values["values"], Utility.serialize_instance)
            except Exception as e:
                jstr = json.dumps(values["values"])
            #self.mq_publish_recursive("v1/devices/me/telemetry", jstr, 1)
            self.mq_publish_recursive(self.topic, jstr, 1)

    def timer_handler(self, evt, userdata):
        timestamp = time.time()
        logger.info("### Periodic collection polling: {0} | Group name: {1} | Timestamp: {2} ###".format(self.group.interval, self.group.name, timestamp))
                    # (self.group.interval, self.group.name, timestamp))

        values = {"timestamp": timestamp, "name": self.group.name, "values": dict()}

        self.read_instant_value(values, timestamp)
        
        # values['values']['timestamp'] = Utility.getTimeStr(timestamp)

        if self.run_mode != "transform":
            self.upload_vars(values, timestamp)

        self.timer.add(self.group.interval)


class ModbusHandle(object):
    # Calculate the value of the data read from plc according to the variable configuration.
    def __get_value(self, v, r, byte_order):
        if r is None:
            return None

        len = self.__get_block_length(v.type)
        if re.match("words:", v.type, re.M | re.I):
            var = []
            for a in r:
                h = ((a & 0xff00) >> 8)
                l = (a & 0xff)
                if re.search(r'(^ab($|cd$))|(^cdab$)', byte_order) is not None:
                    var.append(h << 8 | l)
                else:
                    var.append(a)
            # for a in Utility.toDoubleList(r):
            #     h0 = ((a[0] & 0xff00) >> 8)
            #     l0 = (a[0] & 0xff)
            #     h1 = ((a[1] & 0xff00) >> 8)
            #     l1 = (a[1] & 0xff)
            #     d = Utility.toDWord(l0, h0, l1, h1, byte_order, v.type)
            #     var.append(((d & 0xffff0000) >> 16))
            #     var.append((d & 0xffff))
            # logger.debug("get words data : %s" % var)
            logger.debug("Get words data.")
            return var
        elif re.match("bytes:", v.type, re.M | re.I):
            var = []
            for a in r:
                h = ((a & 0xff00) >> 8)
                l = (a & 0xff)
                if re.search(r'(^ab($|cd$))|(^cdab$)', byte_order) is not None:
                    var.append(h)
                    var.append(l)
                else:
                    var.append(l)
                    var.append(h)
            # logger.debug("get bytes data : %s" % var)
            logger.debug("Get bytes data.")
            return var
        elif re.match("string:", v.type, re.M | re.I):
            var = []
            for a in r:
                h = ((a & 0xff00) >> 8)
                l = (a & 0xff)
                if re.search(r'(^ab($|cd$))|(^cdab$)', byte_order) is not None:
                    # var.append(chr(h << 8 | l))
                    var.append(chr(h))
                    var.append(chr(l))
                else:
                    # var.append(chr(a))
                    var.append(chr(l))
                    var.append(chr(h))
            # logger.debug("get string data : %s" % ''.join(var))
            logger.debug("Get string data.")
            return ''.join(var)
        elif re.match("bits:", v.type, re.M | re.I):
            var = []
            for a in r:
                var.append(0 if a == 0 else 1)
            # logger.debug("get bits data : %s" % var)
            logger.debug("Get bits data.")
            return var
        elif re.match("dwords:", v.type, re.M | re.I):
            var = []
            for a in Utility.toDoubleList(r):
                h0 = ((a[0] & 0xff00) >> 8)
                l0 = (a[0] & 0xff)
                h1 = ((a[1] & 0xff00) >> 8)
                l1 = (a[1] & 0xff)
                var.append(Utility.toDWord(l0, h0, l1, h1, byte_order, v.type))
            # logger.debug("get dwords data : %s" % var)
            logger.debug("Get dwords data.")
            return var
        elif re.match("floats:", v.type, re.M | re.I):
            var = []
            for a in Utility.toDoubleList(r):
                h0 = ((a[0] & 0xff00) >> 8)
                l0 = (a[0] & 0xff)
                h1 = ((a[1] & 0xff00) >> 8)
                l1 = (a[1] & 0xff)
                var.append(Utility.toFloat(l0, h0, l1, h1, byte_order, v.type))
            # logger.debug("get floats data : %s" % var)
            logger.debug("Get floats data.")
            return var
        else:
            pass

        if len == 1:
            if v.type == 'bit':
                return 0 if r[0] == 0 else 1
            else:
                h = ((r[0] & 0xff00) >> 8)
                l = (r[0] & 0xff)
                if re.search(r'(^ba($|dc$))|(^dcba$)', byte_order) is not None:
                    if re.search('^unsigned', v.type):
                        t = ((l << 8) & 0xff00) | h
                        return t
                    else:
                        t = (((l & 0x7f) << 8) & 0xff00) | h
                        return t if (l & 0x80) == 0 else (t - 32768)
                else:
                    if re.search('^unsigned', v.type):
                        return r[0]
                    else:
                        return r[0] if (r[0] & 0x8000) == 0 else r[0] - 65536

        elif len == 2:
            if re.match("bits:", v.type, re.M | re.I):
                val = []
                for a in r:
                    val.append(0 if a == 0 else 1)
                return val
            else:
                h0 = ((r[0] & 0xff00) >> 8)
                l0 = (r[0] & 0xff)
                h1 = ((r[1] & 0xff00) >> 8)
                l1 = (r[1] & 0xff)
                if v.type == 'float':
                    return Utility.toFloat(l0, h0, l1, h1, byte_order, v.type)  # ieee754 converting,precision:default 2
                else:
                    return Utility.toDWord(l0, h0, l1, h1, byte_order, v.type)
        else:
            var = []
            for a in r:
                    h = ((a & 0xff00) >> 8)
                    l = (a & 0xff)
                    if re.search(r'(^ab($|cd$))|(^cdab$)', byte_order) is not None:
                        var.append(h)
                        var.append(l)
                    else:
                        var.append(l)
                        var.append(h)
            return var

    # 根据数据存储类型计算存储寄存器地址个数
    def __get_block_length(self, varType):
        if re.match("words", varType, re.M | re.I):
            temp = varType.split(":")
            return int(temp[1])
        elif varType == 'word' or varType == 'unsigned word' or varType == "signed word":
            return 1
        elif varType == 'bit':
            return 1
        elif re.match("bits:", varType, re.M | re.I):
            temp = varType.split(":")
            return int(temp[1])
        elif varType == 'int' or varType == 'unsigned int' or varType == "signed int":
            return 2
        elif varType == 'dword' or varType == 'unsigned dword' or varType == "signed dword":
            return 2
        elif varType == 'float':
            return 2
        elif re.match("string", varType, re.M | re.I):
            temp = varType.split(":")
            return (int(temp[1]) / 2) + (0 if int(temp[1]) % 2 == 0 else 1)
        elif re.match("bytes", varType, re.M | re.I):
            temp = varType.split(":")
            return (int(temp[1]) / 2) + (0 if int(temp[1]) % 2 == 0 else 1)
        elif re.match("dwords", varType, re.M | re.I):
            temp = varType.split(":")
            return int(temp[1]) * 2
        elif re.match("floats", varType, re.M | re.I):
            temp = varType.split(":")
            return int(temp[1]) * 2
        else:
            return 0

    # 获取写modbus指令
    def __transfer_write_addr(self, address, v_type):
        # var_addr = 0
        # mb_type = None
        if address <= 10000:
            var_addr = address - 1
            mb_type = cst.WRITE_SINGLE_COIL
        elif 40000 < address <= 50000:
            var_addr = address - 40001
            if v_type == 'int' or v_type == 'unsigned int' or v_type == 'signed int':
                mb_type = cst.WRITE_MULTIPLE_REGISTERS
            elif v_type == 'dword' or v_type == 'unsigned dword' or v_type == 'signed dword':
                mb_type = cst.WRITE_MULTIPLE_REGISTERS
            elif v_type == 'float':
                mb_type = cst.WRITE_MULTIPLE_REGISTERS
            else:
                mb_type = cst.WRITE_MULTIPLE_REGISTERS  # cst.WRITE_SINGLE_REGISTER
        elif 400000 < address <= 465535:
            var_addr = address - 400001
            if v_type == 'int' or v_type == 'unsigned int' or v_type == 'signed int':
                mb_type = cst.WRITE_MULTIPLE_REGISTERS
            elif v_type == 'dword' or v_type == 'unsigned dword' or v_type == 'signed int':
                mb_type = cst.WRITE_MULTIPLE_REGISTERS
            elif v_type == 'float':
                mb_type = cst.WRITE_MULTIPLE_REGISTERS
            else:
                mb_type = cst.WRITE_MULTIPLE_REGISTERS  # cst.WRITE_SINGLE_REGISTER
        else:
            return None, None
        return mb_type, var_addr

    # Traversing this group io, reading data from the controller's period register
    @classmethod
    def read_value(cls, masters, device, v):
        # logger.debug("read group: %s time: %s" % (v.controller_id, str(time.time())))
        try:
            s = masters.execute(device.machine_address, v.command, v.mb_addr, v.len)
            return cls().__get_value(v, s, device.byte_order)
        except Exception as e:
            logger.debug("Read error [modbus] @%s:%s" % (device.address, e))
            return False

    # Write data to the controller's specified register
    @classmethod
    def write_value(cls, io, value, master, device, step=1):
        try:
            address = io.address
            byte_order = device.byte_order
            if 'int' in io.type or 'dword' in io.type or 'float' in io.type:
                (cmd, mb_addr) = cls().__transfer_write_addr(int(address) + (step * 2), io.type)
            else:
                (cmd, mb_addr) = cls().__transfer_write_addr(int(address) + step, io.type)

            if 'int' in io.type:
                value1 = int(value)
                values = Utility.toWords(value1, byte_order)
            elif 'dword' in io.type:
                value1 = int(value)
                if ("unsigned" in io.type and 0 <= value1 <= 4294967295) or \
                        ("unsigned" not in io.type and -2147483648 < value1 < 2147483648):
                    values = Utility.toWords(value1, byte_order)
                else:
                    raise ValueError("Invalid values: %s" % value1)
            elif io.type == 'float':
                value1 = float(value)
                values = Utility.Float2ieee754Words(value1, byte_order)
            elif 'word' in io.type:
                value1 = int(value)
                if ("unsigned" in io.type and 0 <= value1 <= 65535) or \
                        ("unsigned" not in io.type and -32768 <= value1 <= 32767):
                    if re.search(r'(^ba($|dc$))|(^dcba$)', byte_order) is not None:
                        h = ((value1 & 0xff00) >> 8)
                        l = (value1 & 0xff)
                        value1 = ((l << 8) & 0xff00) | h
                    if cmd == cst.WRITE_SINGLE_COIL:
                        values = value1
                    else:
                        values = [value1, ]
                else:
                    raise ValueError("Invalid values: %s" % value1)
            else:
                if cmd == cst.WRITE_SINGLE_COIL:
                    values = value
                else:
                    values = [value, ]
            logger.debug("write ctrl [modbus] id: %s, cmd: %s, mb_addr: %s, value: %s" % (
                         device.id, cmd, mb_addr, values))
            master.execute(device.machine_address, cmd, mb_addr, output_value=values)
        except Exception as e:
            logger.debug("Write error [modbus] @ %s : %s" % (io.mb_id, e))
