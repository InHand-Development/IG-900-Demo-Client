#coding=utf-8
import json
import Utilities
import time
#Statistical variable class
class StatisticsVar:
    #id : Variable id
    #current： Current statistic
    #value： The current value, through this value, is calculated and summarized to current
    #timestamp： Timestamp of this data
    #last： Time error of last statistics
    def __init__(self,id=None,current=0,value=None,timestamp=0,last=0):
        self.id = id
        self.current = current
        self.value = value
        self.timestamp = int(timestamp/3600)*3600
        self.endTime = timestamp + 3600 #hourly
        self.last = last

    #Json deserialization
    def unwrap(self,str):
        #u = Utilities.Utility()
        s = json.loads(bytes.decode(str))
        self.current = s['current']
        self.value = s['value']
        self.timestamp = s['timestamp']
        self.endTime = s['endTime']
        if 'last' in s:
            self.last = s['last']

    #Serialized into json
    def wrap(self):
        try:
            return json.dumps(self, default=Utilities.Utility.serialize_instance)
        except Exception as e:
            return json.dumps(self)

    #statistics
    def calc(self,current,value,last):
        self.current = current
        self.count = self.cout +1
        self.last = last
        self.value = value
        #self.timestamp = timestamp

    #Clear
    def reset(self,timestamp):
        self.value = 0
        self.timestamp = timestamp
        # 'current' and 'last' could not reset

if __name__ == '__main__':
    ts = int(time.time())
    sv = StatisticsVar()
    sv.current = 1
    sv.value = 232
    sv.timestamp = ts
    str = sv.wrap()
    print(str)
    sv1 = StatisticsVar()
    sv1.unwrap(str)
    print(sv1.value)
    sv.value = 128
    print(str)
    str = sv.wrap()
    print(str)
    sv1 = StatisticsVar()
    sv1.unwrap(str)
    print(sv1.value)
    value ='128'
