#coding=utf-8
#Alarm trigger condition class
class WarningTrigger:
    def __init__(self):
        #The alarm trigger condition judgment expression is generally used to judge the condition of an IO, such as 'values["hmi.40010"]/10 > 30.0'
        self.expression = None
        #The error code, the application itself defines, when this condition is met, the error code will be uploaded to the platform for platform classification.
        self.code = None
        #Level, 0~5
        self.level = 0
        #Alarm description, used to display the alarm content description on the platform
        self.desc= None
        #Enter dead zone duration Unit: second
        self.duration = 0
        #Time after the alarm is entered, the unit is seconds.
        self.interval = 0;


#Write register setting
class WritingSetting:
    def __init__(self):
        #Corresponding io, the address of the register of plc, such as 'plc1.400010'
        address=None
        #The expression, after the application writes a value, converts the actual data into the register with this expression, such as 'int($var*10)', and $var is replaced with the pre-written value.
        expression=None

        self.read_io_first = False
