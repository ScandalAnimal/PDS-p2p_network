#!/usr/bin/python

from bencoder import encode, decode
from util import decodeBytes

class Parent:
	def getVars(self):
		return vars(self)
	def toJson(self):
		params = vars(self)
		return {k.encode("utf-8"):v for k,v in params.items()}

class PeerRecord(Parent):
	def __init__(self, username, ipv4, port):
		self.username = username
		self.ipv4 = ipv4
		self.port = port

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

class List(Parent):
	def __init__(self, txid, peers):
		self.type = "list"
		self.txid = txid
		self.peers = peers

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

# TODO co ak pridu spravne typy sprav ale chybne ine hodnoty? napriklad chybajuce, nebude NPE?
def decodeMessage(message):
	decoded = {k.decode("utf-8"):decodeBytes(v) for k,v in decode(message).items()}
	if (decoded["type"] == "hello"):
		return Hello(decoded["txid"], decoded["username"], decoded["ipv4"], decoded["port"])
	elif (decoded["type"] == "getlist"):
		return GetList(decoded["txid"])
	elif (decoded["type"] == "list"):
		return List(decoded["txid"], decoded["peers"])
	elif (decoded["type"] == "message"):
		return Message(decoded["txid"], decoded["from"], decoded["to"], decoded["message"])
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

# DB_RECORD := {"<dotted_decimal_IP>,<ushort_port>":{<PEER_RECORD*>}}
