# coding=utf-8
'''
Alarm
'''
import Utilities
import json
from abc import abstractmethod
import time


# 报警类
class Alarm:
    # Copy the variable alarm settings
    def __init__(self, variable, timestamp):
        # level
        self.level = variable.level
        # Alarm id
        self.id = variable.id
        # Status False: Restore, True: Generate
        self.state = False  # normal
        # Alarm content
        self.desc = variable.desc # alarm content
        # At the time of this alarm, if the same alarm is generated and the state is unchanged, the timestamp will be updated, but start is unchanged for alarm suppression.
        self.timestamp = timestamp  # 
        # Alarm start time
        self.start = timestamp
        # error code
        self.code=None
        # Last reported time
        self.last=0

    # Read from dictionary
    def unwrap(self, dict):
        self.level = dict['level']
        self.id = dict['id']
        self.state = dict['state']
        self.desc = dict['desc']
        self.timestamp = dict['timestamp']
        self.start = dict['start']
        if 'last' in dict:
            self.last = dict['last']

    # Package dictionary
    def wrap(self):
        dict = {}
        dict['level'] = self.level
        dict['id'] = self.id
        dict['state'] = self.state
        dict['desc'] = self.desc
        dict['timestamp'] = self.timestamp
        dict['start'] = self.start
        dict['last'] = self.last
        return dict

    # Generate an alarm json for the reporting platform
    def createAlarm_old(self, state=None, value=None, level=0, desc=None, code=None, timestamp=None, duration=0.0, interval=0):
        # Judgment and change in the previous state, the change generates an alarm
        if self.state != state:
            jsonstr = self.newAlarmInfo(state, value, level, desc, code, timestamp)
            return jsonstr
        else:
            self.timestamp = timestamp
            if self.state == True and self.timestamp - self.last > interval:
                jsonstr = self.newAlarmInfo(state, value, level, desc, code, timestamp)
            return None
    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
    # 
    #    To-DO: Consider the state machine mode to refactor
    #    Alarm generation -> Continuous alarm -> Alarm elimination -> Normal -> Alarm generation
    #                            |-> Continuous Alarm |->Normal
    # 
    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

    # Generate an alarm json for the reporting platform
    def createAlarm(self, state=None, value=None, level=0, desc=None, code=None,
                    timestamp=None, duration=0.0, interval=0):
        # Judgment and change in the previous state, the change generates an alarm
        ts = timestamp
        jsonstr = None
        if desc is not None:
            self.desc = desc
        self.code = code
        self.level = level

        if state is True:
            if self.state == state:
                if self.last is None or self.last == 0:
                    # If it is an alarm,
                    # If the dead time is greater than 0, and the abnormal start time (start) is greater than the dead time according to the current time, the alarm is reported.
                    if duration is not None and ts - self.start >= duration > 0:
                        jsonstr = self.newAlarmInfo(state, value, level, desc, code, timestamp)
                    # else Do nothing, until the dead time arrives

                    # When the dead time is not set, the alarm is uploaded when the status changes.
                else:
                    if interval is not None and interval > 0:
                        if ts-self.last >= interval:
                            jsonstr = self.newAlarmInfo(state, value, level, desc, code, timestamp)
                        # else: Do nothing
                            #  Case 2: no alarm interval
                    # else Do nothing
                    # Case 1: If there is no alarm interval setting, the alarm will be uploaded when the status changes. interval =0 | None;

            else:
                # The state is changed, so set start = ts.
                # The state is cleared from the fault -> is generated, remember the time point when the change starts. start = ts
                self.start = ts
                self.last = 0
                # If the dead time is not set, report the alarm immediately
                if duration is None or duration <=0:
                    jsonstr = self.newAlarmInfo(state, value, level, desc, code, timestamp)
                # else Because it is the first time, because the dead time is >0, and start - the current time is 0, so the alarm is not uploaded for the time being.
                    # Wait for the fault to last longer than the dead time (duration) and then report the alarm
        else:
            if self.state != state:
                # The state is generated from the fault -> eliminated, remember the point in time when the change started start = ts
                jsonstr = self.newAlarmInfo(state, value, level, desc, code, timestamp)
                # Wait until the alarm is generated before setting start to the current time. So that the same alarm can be generated and eliminated by site+varid+code+start.
                self.start = ts
                self.last = 0

        self.timestamp = timestamp
        self.state = state
        return jsonstr

    def newAlarmInfo(self, state=None, value=None, level=0, desc=None, code=None, timestamp=None):
        alarm = {}
        alarm['timestamp'] = Utilities.Utility.getTimeStr(timestamp)  # self.start)

        alarm['content'] = self.desc + '[' + self.id + ':' + str(value) + "]"
        alarm['group'] = self.id
        alarm['type'] = self.code
        alarm['level'] = self.level
        alarm['start'] = Utilities.Utility.getTimeStr(self.start)

        if state is True:
            alarm['state'] = 'on'
        else:
            alarm['state'] = 'off'
        jsonstr = json.dumps(alarm)
        # json = Utilities.Utility.serialize_instance(alarm)
        alarm = {}
        return jsonstr


# State machine mode
class TwoStateEvent:
    def __init__(self, name, timestamp):
        self.name = name
        # The time of the last acquisition test
        self.timestamp = timestamp
        # produce
        self.onState = OnState(self, timestamp)
        # eliminate
        self.offState = OffState(self, timestamp)
        # Current state
        self.current = InitState(self, timestamp)
        # Last state
        self.last = None
        self.isChanged = False

    def toOnState(self, timestamp):
        self.timestamp=timestamp
        self.isChanged = self.current.toOnState(timestamp)

    def toOffState(self, timestamp):
        self.timestamp = timestamp
        self.isChanged = self.current.toOffState(timestamp)

    def getChangedState(self):
        if self.isChanged:
            return self.last
        else:
            if self.last == None:
                self.last = self.current
                initState = OnState(self, self.timestamp)
                return initState
            else:
                return None

    # Read from dictionary
    def unwrap(self, dict):
        self.timestamp = dict['timestamp']
        # Current state
        if 'current' in dict:
            if dict['current'] is True:
                self.current = self.onState
            else:
                self.current = self.offState
        if 'last' in dict:
            if dict['last'] is True:
                self.last = self.onState
            else:
                self.last = self.offState
            if 'start_on' in dict:
                self.onState.start = dict['start_on']
            if 'end_on' in dict:
                self.onState.end = dict['end_on']
            if 'start_off' in dict:
                self.offState.start = dict['start_off']
            if 'end_off' in dict:
                self.offState.end = dict['end_off']

    # Package dictionary
    def wrap(self):
        dict = dict()
        dict['timestamp'] = self.timestamp
        dict['last'] = self.last == self.onState
        dict['current'] = self.current == self.onState
        dict['start_on'] = self.onState.start
        dict['end_on'] = self.onState.end
        dict['start_off'] = self.offState.start
        dict['end_off'] = self.offState.end
        return dict


# State machine interface
class AlarmState:
    def __init__(self, event, timestamp, state):
        self.event = event
        self.start = timestamp
        self.end = None
        self.state = state

    @abstractmethod
    def toOnState(self, timestamp):
        pass
    @abstractmethod
    def toOffState(self, timestamp):
        pass


# Production state
class OnState(AlarmState):
    def __init__(self, event, timestamp):
        AlarmState.__init__(self, event, timestamp, 'on')

    def toOnState(self, timestamp):
        return False

    def toOffState(self, timestamp):
        self.start =self.event.current.start
        self.end = timestamp
        self.event.last = self
        self.event.current = self.event.offState
        self.event.current.start = timestamp
        return True


# Eliminate state
class OffState(AlarmState):
    def __init__(self, event, timestamp):
        AlarmState.__init__(self, event, timestamp, 'off')

    def toOnState(self, timestamp):
        self.start =self.event.last.start
        self.end = timestamp
        self.event.last = self
        self.event.current = self.event.onState
        self.event.current.start = timestamp
        return True

    def toOffState(self, timestamp):
        return False


# Eliminate state
class InitState(AlarmState):
    def __init__(self, event, timestamp):
        AlarmState.__init__(self, event, timestamp, 'init')

    def toOnState(self, timestamp):
        self.start =self.event.last.start
        self.end = timestamp
        self.event.last = self
        self.event.current = self.event.onState
        self.event.current.start = timestamp
        return True

    def toOffState(self, timestamp):
        self.start =self.event.last.start
        self.end = timestamp
        self.event.last = self
        self.event.current = self.event.onState
        self.event.current.start = timestamp
        return True


if __name__ == '__main__':
    timestamp = time.time()
    event = TwoStateEvent('Controller1', timestamp)
    state = event.getChangedState()
    print('Event state: Changed ?%s and exist state ?%s' % (event.isChanged, (state != None)))
    if state != None:
        print('init -> off----Event:state = '+state.state +' start='+Utilities.Utility.getTimeStr(state.start)+' end='+Utilities.Utility.getTimeStr(state.end))
    event.toOffState(time.time()+10)
    state = event.getChangedState()
    print('off -> off----Event state: Changed ?%s and exist state ?%s' % (event.isChanged, (state != None)))
    if state != None:
        print('Event:state = '+state.state +' start='+Utilities.Utility.getTimeStr(state.start)+' end='+Utilities.Utility.getTimeStr(state.end))
    event.toOffState(time.time()+20)
    state = event.getChangedState()
    print('off -> off----Event state: Changed ?%s and exist state ?%s' % (event.isChanged, (state != None)))
    if state != None:
        print('Event:state = '+state.state +' start='+Utilities.Utility.getTimeStr(state.start)+' end='+Utilities.Utility.getTimeStr(state.end))
    event.toOnState(time.time()+30)
    state = event.getChangedState()
    print('off -> on ----Event state: Changed ?%s and exist state ?%s' % (event.isChanged, (state != None)))
    if state != None:
        print('Event:state = '+state.state +' start='+Utilities.Utility.getTimeStr(state.start)+' end='+Utilities.Utility.getTimeStr(state.end))
    event.toOffState(time.time()+40)
    state = event.getChangedState()
    print('on  -> off----Event state: Changed ?%s and exist state ?%s' % (event.isChanged, (state != None)))
    if state != None:
        print('Event:state = '+state.state +' start='+Utilities.Utility.getTimeStr(state.start)+' end='+Utilities.Utility.getTimeStr(state.end))
    event.toOffState(time.time()+110)
    state = event.getChangedState()
    print('off -> off----Event state: Changed ?%s and exist state ?%s' % (event.isChanged, (state != None)))
    if state != None:
        print('Event:state = '+state.state +' start='+Utilities.Utility.getTimeStr(state.start)+' end='+Utilities.Utility.getTimeStr(state.end))
    event.toOffState(time.time()+120)
    state = event.getChangedState()
    print('off -> off----Event state: Changed ?%s and exist state ?%s' % (event.isChanged, (state != None)))
    if state != None:
        print('Event:state = '+state.state +' start='+Utilities.Utility.getTimeStr(state.start)+' end='+Utilities.Utility.getTimeStr(state.end))
    event.toOnState(time.time()+130)
    state = event.getChangedState()
    print('off -> on ----Event state: Changed ?%s and exist state ?%s' % (event.isChanged, (state != None)))
    if state != None:
        print('Event:state = '+state.state +' start='+Utilities.Utility.getTimeStr(state.start)+' end='+Utilities.Utility.getTimeStr(state.end))
    event.toOffState(time.time()+140)
    state = event.getChangedState()
    print('on  -> off----Event state: Changed ?%s and exist state ?%s' % (event.isChanged, (state != None)))
    if state != None:
        print('Event:state = '+state.state +' start='+Utilities.Utility.getTimeStr(state.start)+' end='+Utilities.Utility.getTimeStr(state.end))

