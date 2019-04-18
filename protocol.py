#!/usr/bin/python

from bencoder import encode, decode
from util import decodeBytes

class Parent:
	def getVars(self):
		return vars(self)
	def toJson(self):
		params = vars(self)
		return {k.encode("utf-8"):v for k,v in params.items()}

class Hello(Parent):
	def __init__(self, txid, username, ipv4, port):
		self.type = "hello"
		self.txid = txid
		self.username = username
		self.ipv4 = ipv4
		self.port = port

class GetList(Parent):
	def __init__(self, txid):
		self.type = "getlist"
		self.txid = txid

def customEncode(params):
	items = {}
	for k,v in params.items():
		if isinstance(v, dict):
			items[k.encode("utf-8")] = customEncode(v)
		else:
			items[k.encode("utf-8")] = v
	return items			

def customDecode(params):
	items = {}
	for k,v in params.items():
		if isinstance(v, dict):
			if isinstance (k, bytes):
				items[k.decode("utf-8")] = customDecode(v)
			else:
				items[k] = customDecode(v)
		else:
			if isinstance (k, bytes):
				if isinstance (v, bytes):
					items[k.decode("utf-8")] = v.decode("utf-8")
				else:
					items[k.decode("utf-8")] = v
			else:
				if isinstance (v, bytes):
					items[k] = v.decode("utf-8")
				else:
					items[k] = v
	return items

class List(Parent):
	def __init__(self, txid, peers):
		self.type = "list"
		self.txid = txid
		self.peers = peers
	def toJson(self):
		params = vars(self)
		return customEncode(params)
	def getVars(self):
		params = vars(self)
		return customDecode(params)	

class Message(Parent):
	def __init__(self, txid, fromIp, to, message):
		self.type = "message"
		self.txid = txid
		self.fromIp = fromIp
		self.to = to
		self.message = message
	def toJson(self):
		params = vars(self)
		return {k.replace("fromIp","from").encode("utf-8"):v for k,v in params.items()}	

class Update(Parent):
	def __init__(self, txid, db):
		self.type = "update"
		self.txid = txid
		self.db = db
	def toJson(self):
		params = vars(self)
		return customEncode(params)
	def getVars(self):
		params = vars(self)
		return customDecode(params)		

class Disconnect(Parent):
	def __init__(self, txid):
		self.type = "disconnect"
		self.txid = txid

class Ack(Parent):
	def __init__(self, txid):
		self.type = "ack"
		self.txid = txid

class Error(Parent):
	def __init__(self, txid, verbose):
		self.type = "error"
		self.txid = txid
		self.verbose = verbose

def encodeHELLOMessage(txid, username, ipv4, port):
	message = Hello(txid, username, ipv4, port)
	return (encode(message.toJson()).decode())

def encodeGETLISTMessage(txid):
	message = GetList(txid)
	return (encode(message.toJson()).decode())

def encodeLISTMessage(txid, peers):
	message = List(txid, peers)
	return (encode(message.toJson()).decode())

def encodeMESSAGEMessage(txid, fromIp, to, message):
	message = Message(txid, fromIp, to, message)
	return (encode(message.toJson()).decode())

def encodeUPDATEMessage(txid, db):
	message = Update(txid, db)
	return (encode(message.toJson()).decode())

def encodeDISCONNECTMessage(txid):
	message = Disconnect(txid)
	return (encode(message.toJson()).decode())

def encodeACKMessage(txid):
	message = Ack(txid)
	return (encode(message.toJson()).decode())

def encodeERRORMessage(txid, verbose):
	message = Error(txid, verbose)
	return (encode(message.toJson()).decode())

def decodeMessage(message):
	decoded = {k.decode("utf-8"):decodeBytes(v) for k,v in decode(message).items()}
	if (decoded["type"] == "hello"):
		return Hello(decoded["txid"], decoded["username"], decoded["ipv4"], decoded["port"])
	elif (decoded["type"] == "getlist"):
		return GetList(decoded["txid"])
	elif (decoded["type"] == "list"):
		return List(decoded["txid"], decoded["peers"])
	elif (decoded["type"] == "message"):
		mes = ""
		for v in decoded["message"]:
			if mes != "":
				mes = mes + " " + v.decode("utf-8")
			else:	
				mes = mes + v.decode("utf-8")
		return Message(decoded["txid"], decoded["from"], decoded["to"], mes)
	elif (decoded["type"] == "update"):
		return Update(decoded["txid"], decoded["db"])
	elif (decoded["type"] == "disconnect"):
		return Disconnect(decoded["txid"])
	elif (decoded["type"] == "ack"):
		return Ack(decoded["txid"])
	elif (decoded["type"] == "error"):
		return Error(decoded["txid"], decoded["verbose"])
	else:
		raise ValueError("Allowed types are hello, getlist, list, message, update, disconnect, ack, error; not %s", decoded["type"])
