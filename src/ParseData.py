# -*- coding:utf-8 -*-

import time
import libevent
import json
from Utilities import Utility
from Cache import FIFOCache
from MessageChannel import MessagePublish
# from InstantDB import InstantDB
from Alarm import Alarm
from PeriodTimeData import PTData

import sys
try:
    reload(sys)
    sys.setdefaultencoding('utf8')
except Exception as e:
    pass


class ParseData(object):
    def __init__(self, parent):
        self.base = parent.base
        self.queue = parent.r_queue
        self.groups = parent.controllers.groups
        self.db = parent.db
        self.logger = parent.logger
        self.parent = parent
        self.run_mode = parent.controllers.config.mode
        self.mq_publish_callback = parent.mq_publish_callback
        self.timer = libevent.Timer(self.base, self.timer_handler, userdata=None)

        self.rt_data_buffer = FIFOCache(size=60)

        self.send_data_to_vartab = MessagePublish(self.base, 'tcp://127.0.0.1:12328')


    # Get the length of the representation
    def __convertAddress(self, address):
        if address >= 10000:
            return str(address)
        else:
            vid = str(address)
            return vid.zfill(5)

    # Calculate instant variables
    def calc_instant_vars(self, values, name, timestamp):
        for group in self.groups:
            if name != group.name:
                continue
            for var in group.vars:
                if var.calc_mode == 'instant':
                    try:
                        if var.expression:
                            values[var.id] = eval(var.expression)
                        else:
                            values[var.id] = values[self.__convertAddress(var.address)]
                        self.logger.debug("Expression: %s >>> Result: %s = %s " % (var.expression, var.id, values[var.id]))
                    except Exception as e:
                        self.logger.warn('[Calc Instant vars] id: %s | expression: %s | Error: %s' %
                                         (var.id, var.expression, e))
                        continue

    def generator_fix_length_vars(self, values, name, timestamp, length=200):
        vals = []
        pkg_length = 0
        for group in self.groups:
            if name != group.name:
                continue
            for var in group.vars:
                key = var.id if var.calc_mode == 'instant' else "%s.%s" % (group.name, var.id)
                if key in values.keys():
                    val = dict()
                    val['value'] = values[key]
                    val['id'] = var.id
                    val['timestamp'] = Utility.getTimeStr(timestamp)
                    val['endTime'] = Utility.getTimeStr(timestamp)
                    vals.append(val)
                    pkg_length += 1
                if pkg_length >= length:
                    pkg_length = 0
                    yield vals, group.name
                    vals = self.clear_list(vals)
            yield vals, group.name
            pkg_length = 0
            vals = self.clear_list(vals)

    def clear_list(self, vals):
        for val in vals:
            val.clear()
        return list()

    # 将本次采集io，计算得到varaible的值集合上传或发生断线时缓存到内存
    def upload_vars(self, values, group_name, timestamp):
        # self.logger.info("values data: %s" % values)
        for vals, name in self.generator_fix_length_vars(values, group_name, timestamp, 200):
            if len(vals) > 0:
                try:
                    jstr = json.dumps(vals, Utility.serialize_instance)
                except Exception as e:
                    jstr = json.dumps(vals)
                for var in vals:
                    var['timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))
                    var['value'] = str(var['value'])
                self.send_data_to_vartab.write("vals:%s:=%s" % (name, json.dumps(vals)))
                if self.parent.bridge_mqtt_is_ready():
                    self.logger.info("Upload data: %s" % jstr)
                    topic = "InMB/series"
                    self.parent.mqclient.publish(topic, jstr, 1)
                    while not self.rt_data_buffer.isEmpty():
                        oldjstr = self.rt_data_buffer.get()
                        self.parent.mqclient.publish(topic, oldjstr, 1)
                        if not self.parent.bridge_mqtt_is_ready():
                            self.rt_data_buffer.put(oldjstr)
                            break
                else:
                    self.logger.debug("The session is diconnected, we can not upload the rt-data")
                    self.rt_data_buffer.put(jstr)

    def timer_handler(self, evt, userdata):
        while not self.queue.empty():

            values = self.queue.get()

            self.logger.info("Got queue data: %s" % values)

            timestamp = values["timestamp"]
            group_name = values["id"]

            self.calc_instant_vars(values["values"], group_name, timestamp)

            self.upload_vars(values["values"], group_name, timestamp)

        self.timer.add(1)
