#coding=utf-8

import shelve
import logging

#Persistent cache class
class InstantDB():
    def __init__(self,dbpath):
        #DBHandle.__init__(dbpath)
        self.dbpath = dbpath

    #Cache the val value of the specified name
    def addDBVal(self, name, val):
        db = None
        try:
            db = shelve.open(self.dbpath)
            if name in db:
                #data = db[name]
                #data.append(val)
                db[name] = val
            else:
                #dbVal = []
                #dbVal.append(val)
                db[name] = val
            logging.debug("InstantDB:save object[key=%s] into %s value:%s",name,self.dbpath,val)
            db.close()
        except:
            logging.debug( "add value: can't open instant db file %s" % self.dbpath)
        if db != None:
            db.close()
    #Delete the value of the specified name
    def delDBVal(self, name):
        db = None
        try:
            db = shelve.open(self.dbpath)
            if name in db:
                del db[name]

        except:
            logging.debug("del value: can't open instant db file %s" % self.dbpath)
        if db != None:
            db.close()

    #Get the value of key as name
    def showDBVal(self, name):
        ret = None
        db = None
        try:
            db = shelve.open(self.dbpath)
            if name in db:
                ret = db[name]
        except:
            logging.debug("show value: can't open instant db file %s" % self.dbpath)
        if db != None:
            db.close()
        return ret

