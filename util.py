#!/usr/bin/python

import sys
import uuid
import random

class ServiceException(Exception):
	pass

class UniqueIdException(Exception):
	pass

def signalHandler(signum, frame):
	printErr ('Caught signal %d' % signum)
	raise ServiceException

def getRandomId():
	return random.randint(1,60000)
	# return str(uuid.uuid4()).replace("-","") 	


def decodeBytes(obj):
    if isinstance(obj, bytes):
        return obj.decode("utf-8")
    else:
    	return obj	

# TODO na konci zmazat decorator
def printErr(message):
	print ("###########################################")
	print("#STDERR: " + message + " #", file=sys.stderr)
	print ("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")    	

def validateIp(s):
    a = s.split('.')
    if len(a) != 4:
        return False
    for x in a:
        if not x.isdigit():
            return False
        i = int(x)
        if i < 0 or i > 255:
            return False
    return True	