#!/usr/bin/python

import uuid

class ServiceException(Exception):
	pass

class UniqueIdException(Exception):
	pass

def signalHandler(signum, frame):
	print ('Caught signal %d' % signum) # TODO print to stderr
	raise ServiceException

# TODO replace with ushort?
def getRandomId():
	return str(uuid.uuid4()).replace("-","") 	


def decodeBytes(obj):
    if isinstance(obj, bytes):
        return obj.decode("utf-8")
    else:
    	return obj	