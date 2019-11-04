# coding=utf-8
import logging

#Time period (once per hour) statistical class variable class
class PTData:
    # Id: variable identifier
    # Type: timer: second timer | counter: counter | accumulator: incremental accumulator | complex: complex variable
    # timestamp： Timestamp
    def __init__(self, id, state, type, timestamp):
        self.id = id
        # State, used to compare the next state to determine if a rollover has occurred
        self.state = state
        # Current real-time value
        self.current = 0
        # Current real-time value
        self.value = 0
        self.timestamp = 0
        # Start time, hour
        self.start = int(timestamp /3600) *3600
        # End time, 1 hour from the start
        self.end = self.start + 3600
        # Types of,
        self.type = type
        self.quality = 0
        self.total_times = 0
        self.ok_times = 0
        self.quality = 0
        self.last = 0

    # 判断输入时间戳是否在本统计时间段内
    def validation(self, timestamp):
        if timestamp >= self.start < self.end:
            return True
        else:
            return False

    # Determine if the state has flipped
    def isStateChanged(self, state):
        return self.state != state  # != state

    # statistics
    def count(self, state, current, timestamp):
        # if self.state == False:
        #     if state == True:
        #         self.value =self.value + current
        # else:
        #     if state == False:
        #         self.value = current
        if self.type == "timer":
            self.count_time(state, current, timestamp)
        elif self.type == "counter":
            self.count_counter(state, current, timestamp)
        elif self.type == "accumulator":
            self.sum(state, current, timestamp)
        else:
            self.count_default(state, current, timestamp)
        self.ok_times = self.ok_times +1

    # Simple statistics, covering the original value
    def count_default(self, state, current, timestamp):
        # logging.debug("--------------called the PTData.count(...), self.type="+self.type)
        self.value = current# self.value # + current
        self.state = True
        self.current = current
        self.timestamp = timestamp

    # Parsing dictionary
    def unwrap(self, dict):
        self.id = dict['id']
        self.state = (dict['state'] == 1)
        self.current = dict['current']
        self.value = dict['value']
        self.timestamp = dict['timestamp']
        self.start = dict['start']
        self.end = dict['end']
        self.type = dict['type']
        if 'total_times' in dict:
            self.total_times = dict['total_times']
        if 'ok_times' in dict:
            self.ok_times = dict['ok_times']

    # Packaged into a dictionary
    def wrap(self):
        dict = {}
        dict['value'] = self.value
        dict['id'] = self.id
        dict['state'] = 1 if self.state else 0
        dict['type']=self.type
        dict['current'] = self.current
        dict['timestamp'] = self.timestamp
        dict['start'] = self.start
        dict['end'] = self.end
        dict['total_times'] = self.total_times
        dict['ok_times'] = self.ok_times
        return dict

    def incTimes(self, timestamp):
        self.total_times = self.total_times + 1
        self.last = timestamp

    def getQuality(self):
        if self.total_times == 0:
            return 0
        else:
            return int(100.0*self.ok_times/self.total_times)

    #Add the number of this acquisition and the increment of the last number to the statistical value.
    def sum(self, state, current, timestamp):
        # if self.state == False:
        #     if state == True:
        #        self.value = self.value + (current - self.current)
        dif = current - self.current
        # logging.debug("---------Accumulator.diff="+str(dif))
        if dif >=0:
            self.value = self.value + dif
        else:
            self.value = self.value + current
        self.state = state
        self.current = current
        self.timestamp = timestamp

    # If the state occurs, the timing starts, and the current is the duration, usually the collection interval.
    def count_time(self, state, current, timestamp):
        # if self.state == False:
        #     if state == True:

        #         self.value = self.value + interval
        if state == True:
            self.value = self.value + current
        self.state = state
        self.current = current
        self.timestamp = timestamp

    # If the state occurs, it starts timing, and the current is passed in times, usually 1 time.
    def count_counter(self, state, current, timestamp):
        if self.state is False:
            if state is True:
                self.value = self.value + current
        self.state = state
        self.current = current
        self.timestamp = timestamp


if __name__ == '__main__':
     import Utilities
     t =1479365180.8
     print(Utilities.Utility.getTimeStr(t))
     x = int(t/3600)*3600
     print(Utilities.Utility.getTimeStr(x))


# str = time.strftime('%Y-%m-%dT%H:%M:%S%Z')