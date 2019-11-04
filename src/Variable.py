#coding=utf-8
import logging

#变量类
class Variable:
    def __init__(self,id='temperature',type='float',calc_mode='instant',level=0,unit='',expression=None,trigger=None,warnings=None,writeable=None,desc=''):
        #Globally unique variable identifier
        self.id = id
        #Data type bit | int | float | string
        self.type = type
        #unit
        self.unit=unit
        #Calculate the expression, get the value of this Variable through the expression calculated by IO or other Variable
        self.expression=expression
        #Alarm settings, WarningTrigger array, see the WarningTrigger class in WarningTrigger.py
        self.warnings = warnings
        #Writable settings, see the WritingSetting class in WarningTrigger.py
        self.writeable = writeable
        #Description, generally used to display the Variable
        self.desc = desc
        #Variable importance level
        self.level = level
        #Calculation mode: instant: real-time type, calculated directly from expression; timer: second timer | counter: counter | accumulator: incremental accumulator | complex: complex variable
        #Note that in addition to the instant type, the rest need to be used in conjunction with the trigger attribute (trigger condition). The timer, counter, accumulator represents the statistics in one hour.
        self.calc_mode = calc_mode
        #Statistical variable
        self.trigger = trigger
        
#General purpose PLC register class
class IO:
    #address: address
    #type: The data type stored in this register bit | <signed | unsigned> word | <signed | unsigned> dword | fload | bytes[n] | string[n]
    def __init__(self,address='40001',type='word',controller_id = None):
        self.address = address
        self.type = type
        self.controller_id = controller_id

class PureIO:
    def __init__(self,io):
        self.address=io.address
        self.type=io.type