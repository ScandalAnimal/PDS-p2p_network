#!/usr/bin/python

import sys
import uuid
import random

class ServiceException(Exception):
	pass

class UniqueIdException(Exception):
	pass

def signalHandler(signum, frame):
	print ('Caught signal %d' % signum) # TODO print to stderr
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