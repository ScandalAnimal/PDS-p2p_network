#!/usr/bin/python

import uuid

class ServiceException(Exception):
	pass

def signalHandler(signum, frame):
	print ('Caught signal %d' % signum) # TODO print to stderr
	raise ServiceException

# TODO replace with ushort?
def getRandomId():
	return str(uuid.uuid4()).replace("-","") 	