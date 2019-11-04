#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
MQClient
Created on 2017/12/26
@author: Zhengyb
'''
import ssl
import paho.mqtt.client as mqtt
import time
import Logger

MQ_NOT_READY = 0
MQ_READY = 1


class LocalBrokerBadConfError(ValueError):
    pass


class LocalPublishError(ValueError):
    pass


class MQClient():

    def __init__(self, client_id,
                 broker_host='127.0.0.1', broker_port=1883, username=None, passwd=None, tls=False, capath=None, max_queue_size=100,
                 after_connect=None, on_connected=None, on_disconnected=None,
                 logger=None):
        self.client_id = client_id
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.username = username
        self.passwd = passwd
        self.tls = tls
        self.capath = capath
        self.mqtt_client = mqtt.Client(self.client_id, clean_session=False, userdata=None,
                                       protocol=mqtt.MQTTv311)
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_disconnect = self._on_disconnect
        #self.mqtt_client.on_subscribe = self._on_subscribe
        self.mqtt_client.on_publish = self._on_publish
        self.mqtt_client.on_message = self._on_message
        self.max_queue_size = max_queue_size
        self.mqtt_client.max_queued_messages_set(self.max_queue_size)
        self.mqtt_client.max_inflight_messages_set(1)  # force in-order
        self._on_connected = on_connected
        self._on_disconnected = on_disconnected
        self._after_connect = after_connect
        self._state = MQ_NOT_READY
        self.subs = dict()
        self.pub_acks = dict()
        self.pub_topic_cbs = dict()
        self.logger = logger

    def connect(self):
        '''This function should be called once after MQClient object is created'''
        try:
            if self.username and self.passwd:
                self.mqtt_client.username_pw_set(self.username, self.passwd)
            if self.tls is True and self.capath:
                self.mqtt_client.tls_set(ca_certs=self.capath, tls_version=ssl.PROTOCOL_TLSv1_2)
            ret = self.mqtt_client.connect(self.broker_host, self.broker_port)
            if self._after_connect is not None:
                self._after_connect(self.mqtt_client)
            return ret
        except Exception as e:
            self.logger.exception('%s' % e.__str__())

    def reconnect(self):
        try:
            ret = self.mqtt_client.reconnect()
            if self._after_connect is not None:
                self._after_connect(self.mqtt_client)
            return ret
        except Exception as e:
            self.logger.exception('%s' % e.__str__())

    def disconnect(self):
        return self.mqtt_client.disconnect()

    def loop(self):
        '''This function could be called in a while True loop'''
        self.mqtt_client.loop()

    def loop_misc(self):
        '''This function could be called every some seconds to handle retry and ping'''
        self.mqtt_client.loop_misc()

    def loop_read(self):
        '''This function could be called while the read IO is valid'''
        self.mqtt_client.loop_read()

    def loop_write(self):
        '''This function could be called while the write IO is valid'''
        if self.mqtt_client.want_write():
            self.mqtt_client.loop_write()

    def socket(self):
        return self.mqtt_client.socket()

    def get_state(self):
        return self._state

    def is_ready(self):
        return self._state == MQ_READY

    def add_sub(self, topic, callback, qos=1):
        '''
            This function should be call after MQClient object is created
            callback is a function(payload)
        '''
        d = dict()
        d['callback'] = callback
        d['qos'] = qos
        self.subs[topic] = d

    def add_pub_topic_callback(self, topic, on_publish_callback):
        self.pub_topic_cbs[topic] = on_publish_callback

    def publish(self, topic, payload, qos=1, userdata=None):
        if self.get_state() == MQ_READY:
            try:
                mqttc_msg_info = self.mqtt_client.publish(topic, payload, qos)
                if (mqttc_msg_info.rc is mqtt.MQTT_ERR_QUEUE_SIZE):
                    self.logger.error("publish() return error: %d(%s)" % (
                        mqttc_msg_info.rc, 'local queue overflow'))
                elif (mqttc_msg_info.rc is not mqtt.MQTT_ERR_SUCCESS) \
                        and (mqttc_msg_info.rc is not mqtt.MQTT_ERR_NO_CONN):
                    self.logger.error("publish() return error: %d(%s)" % (
                        mqttc_msg_info.rc, mqtt.error_string(mqttc_msg_info.rc)))
                    raise LocalPublishError(
                        'Local publish error, %s' % mqtt.error_string(mqttc_msg_info.rc))
                else:
                    # self.logger.debug('mid %d' % mqttc_msg_info.mid)
                    if qos > 0 and userdata is not None and self.pub_topic_cbs.has_key(topic):
                        d = dict()
                        d['topic'] = topic
                        d['userdata'] = userdata
                        self.pub_acks[mqttc_msg_info.mid] = d
                    # schedule loop write when msg is queued. If fail, wait for
                    # loop_misc() to retry
                    self.mqtt_client.loop_write()
            except Exception as e:
                self.logger.exception(
                    "publish() exception: %s topic %s  payload %s" % (e.__str__(), topic, payload))

    def _subscribe_topics(self):
        for topic in self.subs.keys():
            qos = self.subs[topic]['qos']
            self.logger.debug('key %s, value %s' % (topic, qos))
            self.mqtt_client.subscribe(topic, qos)

    def _on_connect(self, client, userdata, flags, rc):
        self.logger.debug("_on_connect: rc = %d." % rc)
        if rc == mqtt.CONNACK_ACCEPTED:
            #if self._state == MQ_NOT_READY:
            self._state = MQ_READY
            self._subscribe_topics()
            if self._on_connected is not None:
                self._on_connected(client)
        elif rc == mqtt.CONNACK_REFUSED_SERVER_UNAVAILABLE:
            if self._state == MQ_READY:
                #self._state = MQ_NOT_READY
                if self._on_disconnected is not None:
                    self._on_disconnected(client)
                self.reconnect()
        else:
            if self._state == MQ_READY:
                #self._state = MQ_NOT_READY
                if self._on_disconnected is not None:
                    self._on_disconnected(client)
                raise LocalBrokerBadConfError(mqtt.connack_string(rc))

    def _on_disconnect(self, client, userdata, rc):
        self.logger.debug("_on_disconnect: rc = %d." %
                          (rc))
        if rc == mqtt.MQTT_ERR_SUCCESS:
            self.logger.debug('disconnected on disconnect() call')
            self._state = MQ_NOT_READY
            if self._on_disconnected is not None:
                self._on_disconnected(client)
        else:
            #self._state = MQ_NOT_READY
            if self._on_disconnected is not None:
                self._on_disconnected(client)
            self.reconnect()

    def _on_subscribe(self, client, userdata, mid, granted_qos):
        pass

    def _on_publish(self, client, userdata, mid):
        if mid in self.pub_acks:
            topic = self.pub_acks[mid]['topic']
            self.logger.debug('on_publish topic %s, mid %d' % (topic, mid))
            if (topic is not None) and topic in self.pub_topic_cbs:
                callback = self.pub_topic_cbs[topic]
                if callback is not None:
                    callback(self.pub_acks[mid]['topic'],
                             self.pub_acks[mid]['userdata'])
            del self.pub_acks[mid]

    def _on_message(self, client, userdata, msg):
        found = False
        # self.logger.debug('MQ Client receives message, topic %s...' % msg.topic)
        for sub in self.subs.keys():
            if mqtt.topic_matches_sub(sub, msg.topic):
                found = True
                callback = self.subs[sub]['callback']
                if callback is not None:
                    try:
                        callback(msg.topic, msg.payload)
                    except Exception as e:
                        self.logger.exception('%s' % e.__str__())
                break
        if not found:
            self.logger.debug('I donot care about this topic, %s' % msg.topic)


if __name__ == '__main__':
    import libevent
    import signal
    from Logger import Logger

    class ClientApp():

        def __init__(self, client_id):
            self.base = libevent.Base()
            self.logger = Logger()
            self.mqclient = MQClient(
                client_id,
                max_queue_size=10,
                after_connect=self._after_connect, on_connected=self._on_connected, on_disconnected=self._on_disconnected,
                logger=self.logger)
            self.readEvt = None
            self.writeEvt = None
            self.timer = libevent.Timer(
                self.base, self._timerHandle, userdata=None)
            self.sig = libevent.Signal(
                self.base, signal.SIGINT, self._on_signal_handler)
            self.topic = 'local/py/test'
            self.msg_id = 0

        def init(self):
            self.mqclient.add_sub(self.topic, self._on_test_sub)
            self.mqclient.add_pub_topic_callback(
                self.topic, self._on_msg_published)
            self.mqclient.connect()
            self.timer.add(1)
            self.sig.add()

        def run(self):
            try:
                # self.base.dispatch()
                self.base.loop()
            except Exception as e:
                print('%s' % e.__str__())

        def _on_signal_handler(self, evt, fd, userdata):
            self.logger.info("receive sigInt, exit")
            self.base.loopexit(0)

        def _on_test_sub(self, topic, payload):
            self.logger.debug('received test msg: %s' % payload)

        def _on_msg_published(self, topic, userdata):
            self.logger.debug(
                'msg topic %s userdata %s is published' % (topic, userdata))

        def _timerHandle(self, evt, userdata):
            #self.logger.debug('to publish %d' % self.msg_id)
            #self.mqclient.publish(self.topic, 'hello MQ, id:%d' % self.msg_id, qos=2, userdata=self.msg_id)
            #self.msg_id = self.msg_id + 1
            try:
                if self.readEvt is not None:
                    self.mqclient.loop_misc()
                else:
                    self.mqclient.reconnect()
            except Exception as e:
                print('%s' % e.__str__())
            self.timer.add(5)

        def _mq_do_read(self, evt, fd, what, userdata):
            self.mqclient.loop_read()

        def _mq_do_write(self, evt, fd, what, userdata):
            self.mqclient.loop_write()

        def _after_connect(self, client):
            if (self.mqclient.socket() is not None):
                if self.readEvt is not None:
                    self.readEvt.delete()
                if self.writeEvt is not None:
                    self.writeEvt.delete()
                self.readEvt = libevent.Event(self.base, client.socket().fileno(
                ), libevent.EV_READ | libevent.EV_PERSIST, self._mq_do_read)
                self.writeEvt = libevent.Event(self.base, client.socket(
                ).fileno(), libevent.EV_WRITE, self._mq_do_write)
                self.readEvt.add()
                self.writeEvt.add()

        def _on_connected(self, client):
            pass
            '''
            self.readEvt = libevent.Event(self.base, client.socket().fileno(
            ), libevent.EV_READ | libevent.EV_PERSIST, self._mq_do_read)
            self.writeEvt = libevent.Event(self.base, client.socket(
            ).fileno(), libevent.EV_WRITE, self._mq_do_write)
            self.readEvt.add()
            self.writeEvt.add()
            # self.timer.add(10)
            '''

        def _on_disconnected(self, client):
            self.readEvt.delete()
            self.writeEvt.delete()
            # self.timer.delete()
            self.readEvt = None
            self.readEvt = None
    try:
        app = ClientApp('vendor', 'app1')
        print('start testing')
        app.init()
        print('connecting, run...')
        app.run()
        print('exit')

    except Exception as e:
        print('%s' % e.__str__())
