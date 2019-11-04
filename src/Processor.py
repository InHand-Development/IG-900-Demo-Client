# -*- coding:utf-8 -*-

import time
import json
import os
import uuid
import libevent

from AppTemplate_libevent import AppTemplate
from Configure import Configure

from DevMgmt import DevMgmt
from GroupMgmt import GroupMgmt

import InDB
import Topics
try:
    from Queue import Queue
except Exception as e:
    from queue import Queue
import logging

from Logger import logger
import multiprocessing as mp

# this is the start point of the user application
logger.debug('STARTING DEMO APPLICATION IN PROCESSOR.PY')
#wait a few seconds to allow the user to open the log file 
time.sleep(5)

INPY_APP_PATH = '/var/app/'


# 处理主类
class App(AppTemplate):
    logger.debug('*** Running App ***')
    def __init__(self, vendor_name, app_name):
        AppTemplate.__init__(self, vendor_name, app_name)
        self.app_name = app_name
        self.configure = None

        self.dev_mgmt = None
        self.topic = ""

        # 事件数据
        self.evt_data_tb = None
        # 实时数据
        self.var_data_tb = None
        # 历史数据
        self.his_data_tb = None
        # 事件历史上传数据
        self.evt_his_upload_data_tb = None
        # 默认开启debug，暂时用。
        self.logger = logger
        self.logger._logger.setLevel(logging.DEBUG)
        # 配置上传
        self.config_timer = libevent.Timer(
            self.base, self._config_timer_handler, userdata=None)

    def _init_conf(self):
        logger.debug('*** Running _init_config_ ***')
        self.get_user_config()
        logger.debug('user_conf=%s' % self.user_conf)
        self.running_conf = self.configure.config
        logger.load_config(self.running_conf)
        if self.running_conf.has_option('REMOTE', 'host'):
            self.target_host = self.running_conf.get('REMOTE', 'host').strip()
        else:
            self.target_host = '127.0.0.1'
        if self.running_conf.has_option('REMOTE', 'port'):
            self.target_port = self.running_conf.get('REMOTE', 'port')
        else:
            self.target_port = 1883
        if self.running_conf.has_option('REMOTE', 'username'):
            self.target_username = self.running_conf.get('REMOTE', 'username').strip()
            #self.client_id = 'MQTT_FX_Client'
        else:
            self.target_username = None
        if self.running_conf.has_option('REMOTE', 'passwd'):
            self.target_passwd = self.running_conf.get('REMOTE', 'passwd').strip()
        else:
            self.target_passwd = None
            self.target_passwd = self.target_username
        if self.running_conf.has_option('REMOTE', 'tls'):
            self.target_tls = self.running_conf.get('REMOTE', 'tls').strip()
            if self.running_conf.has_option('REMOTE', 'capath'):
                self.target_capath = self.running_conf.get('REMOTE', 'capath').strip()
            else:
                self.target_capath = '/var/pycore/lib/python2.7/site-packages/requests/cacert.pem'
        else:
            self.target_tls = None
            self.target_capath = None
        
        self.topic = self.running_conf.get('REMOTE', 'topic').strip()

        logger.info("%s |%s |%s |%s |" % (self.target_host, self.target_port, self.target_username, self.target_passwd))

    def on_log(self, client, userdata, level, buf):
        logger.debug('*** Running on_log ***')
        logger.debug('%s' % buf)

    def _proc_init(self, device):
        logger.debug('*** Running _proc_init ***')
        self._preinit()
        self.configure.devices = {device.id: device}
        self._device_init()
        self._end_init()

    def _norm_init(self):
        logger.debug('*** Running _norm_init ***')
        self._preinit()
        self._device_init()
        self._end_init()

    def _device_init(self):
        logger.debug('*** Running _device_init ***')
        self.dev_mgmt = DevMgmt(self.base, self.configure, self.mq_publish_callback)
        self.dev_mgmt.init_devices()

        for device in self.configure.devices.values():
            group_mgmt = GroupMgmt(self.base, device, self.dev_mgmt.masters[device.id], device.groups,
                                   self.mq_publish_callback, self.configure.config.mode, self.configure.config.cloud)
            # Start data collection task
            for g in group_mgmt.readTimerEvt:
                g.timer.add(1)
            self.dev_mgmt.group_mgmts.append(group_mgmt)

        self.mqclient.add_sub("InMB/variable/set", self.variable_set_sub)

    def _end_init(self):
        logger.debug('*** Running _end_init ***')
        self.mqclient.mqtt_client.on_log = self.on_log
        if not self.zero_service:
            self.mqclient.add_sub(Topics.TOP_SERVICE_STATE_UNICAST_FMT %
                                  self.app_info.app_id, self._dep_app_handler, qos=1)
            self.mqclient.add_sub(
                Topics.TOP_SERVICE_STATE_BROADCAST, self._dep_app_handler, qos=1)
        if self.use_bridge:
            self.mqclient.add_sub(Topics.TOP_BRIDGE_STATE, self._bridge_state)
        self.mqclient.connect()
        self.mq_timer.add(1)
        if self.service_keepalive:
            self.ka_timer.add(1)
        self.sig_int.add()
        self.sig_term.add()
        if self.conf_monitor:
            self.sig_hup.add()
        self.sig_usr1.add()

    def create_process(self, device):
        logger.debug('*** Running _create_process ***')
        self.base = libevent.Base()
        self.client_id = str(uuid.uuid4())
        self._init_mqclient()
        self._proc_init(device)
        self.base.dispatch()
        logging.info("Process Exit ...")

    def init(self):
        logger.debug('*** Running init ***')
        self._init_conf()
        self._init_mqclient()
        # if self.configure.config.mode == "transform":
        #     for device in self.configure.devices.values():
        #         p = mp.Process(target=self.create_process, args=(device, ))
        #         p.start()
        #     self._end_init()
        # else:

        self._norm_init()
        # SSSself.config_timer.add(1)
        self.use_bridge = False

    def _preinit(self):
        logger.debug('*** Running _preinit ***')
        pass

    # modbus publish callback
    def mq_publish_callback(self,  topic, payload, qos_level=1, check_bridge=True):
        logger.debug('*** Running mq_publish_callback ***')
        if self.bridge_mqtt_is_ready(check_bridge):
            topic = self.topic
            self.mqclient.publish(topic, payload, qos_level)
            return True
        return False

    def variable_set_sub(self, topic, payload):
        logger.debug('*** Running variable_set_sub ***')
        # Write controller task
        try:
            logger.info("write mbvar value %s" % payload)
            message = json.loads(payload)
            self.group_mgmts.writehandle(message)
        except Exception as e:
            logger.error("write data error in GroupExtHandle:%s" % e)

    def _on_pub_topic_ack_handler(self, topic, userdata):
        logger.debug('*** Running _on_pub_topic_ack_handler ***')
        logger.debug(
            'Msg(topic %s, userdata %s)is sent' % (topic, userdata))

    def bridge_mqtt_is_ready(self, check_bridge=True):
        logger.debug('*** Running bridge_mqtt_is_ready ***')       
        return self.mqclient.is_ready() and self.bridge_ready() if check_bridge and self.use_bridge else True

    def _config_timer_handler(self, evt, userdata):
        logger.debug('*** Running _config_timer_handler ***')        
        self.upload_config_var()

    # Report the variable dictionary to the platform
    def upload_var_dict(self):
        logger.debug('*** Running upload_var_dict ***') 
        topic = 'InMB/controllers_configuration'
        data = self.configure.to_json()
        logger.debug("Send the var dict to the platform: %s" % data)
        self.mqclient.publish(topic, data, 1)

    # Report the variable dictionary to the platform
    def upload_config_var(self):
        logger.debug('*** Running upload_config_var ***')
        if self.bridge_mqtt_is_ready():
            # self.upload_var_dict()
            #  Serial network port configuration upload
            self.dev_mgmt.config_timer.add(1)
            #  Start statistics task
            # self.config_timer.add(5)
        else:
            logger.error("Upload configuration channel is not available.")
            # self.config_timer.add(5)

    # After reading the configuration, start the modbus read task according to the collection policy group (group).
    def get_user_config(self):
        logger.debug('*** Running get_user_config ***')
        try:
            filename = INPY_APP_PATH + 'cfg/' + self.app_name + '/' + self.app_name + '.cfg'
            # filename = INPY_APP_PATH + 'cfg/InModbus/InModbus.cfg'
            if os.path.exists(filename) is False:
                filename = INPY_APP_PATH + self.app_name + '/config.yaml'
            self.configure = Configure()
            logger.debug("filename: %s" % filename)
            self.configure.pars_yaml(filename)
        except Exception as e:
            logger.error('get App config error %s' % (e.__str__()))
            self.get_user_config()
            time.sleep(5)


if __name__ == '__main__':
    app = App('Inhand', 'InModbusSimplify')
    app.init()
    app.run()
