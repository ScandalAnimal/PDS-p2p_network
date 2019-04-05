#!/usr/bin/python

from bencoder import encode

class Parent:
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

def getHELLOMessage(txid, username, ipv4, port):
	message = Hello(txid, username, ipv4, port)
	return (encode(message.toJson()).decode())

def getGETLISTMessage(txid):
	message = GetList(txid)
	print (encode(message.toJson()).decode())

def getLISTMessage(txid, peers):
	message = List(txid, peers)
	print (encode(message.toJson()).decode())

def getMESSAGEMessage(txid, fromIp, to, message):
	message = Message(txid, fromIp, to, message)
	print (encode(message.toJson()).decode())

def getUPDATEMessage(txid, db):
	message = Update(txid, db)
	print (encode(message.toJson()).decode())

def getDISCONNECTMessage(txid):
	message = Disconnect(txid)
	print (encode(message.toJson()).decode())

def getACKMessage(txid):
	message = Ack(txid)
	print (encode(message.toJson()).decode())

def getERRORMessage(txid, verbose):
	message = Error(txid, verbose)
	print (encode(message.toJson()).decode())


# PEER_RECORD := {"<ushort>":{"username":"<string>", "ipv4":"<dotted_decimal_IP>", "port": <ushort>}}

# DB_RECORD := {"<dotted_decimal_IP>,<ushort_port>":{<PEER_RECORD*>}}
