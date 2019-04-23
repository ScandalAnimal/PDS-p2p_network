#!/usr/bin/python3

import sys
import uuid
import random

class AckRecord:
	def __init__(self, time, ip, port, messageType):
		self.time = time
		self.ip = ip
		self.port = port
		self.type = messageType
	def __str__(self):
		return ("TIME: " + str(self.time) + ", IP: " + str(self.ip) + ", PORT: " + str(self.port) + ", TYPE: " + str(self.type))	

class InterruptException(Exception):
	pass

class UniqueIdException(Exception):
	pass

def signalHandler(signum, frame):
	raise InterruptException

def getRandomId():
	return random.randint(1,60000)
	# return str(uuid.uuid4()).replace("-","") 	


def decodeBytes(obj):
    if isinstance(obj, bytes):
        return obj.decode("utf-8")
    else:
    	return obj	

def printCorrectErr(message):
	print("#STDERR: " + message, file=sys.stderr)

def printDebug(message):
	print("#DEBUG: " + message, file=sys.stderr)	

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