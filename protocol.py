#!/usr/bin/python

def getHELLOMessage(txid, username, ipv4, port):
	messageType = "hello"

def getGETLISTMessage(txid):
	messageType = "getlist"

def getLISTMessage(txid, peers):
	messageType = "list"

def getMESSAGEMessage(txid, from, to, message):
	messageType = "message"

def getUPDATEMessage(txid, db):
	messageType = "update"

def getDISCONNECTMessage(txid):
	messageType = "disconnect"

def getACKMessage(txid):
	messageType = "ack"

def getERRORMessage(txid, verbose):
	messageType = "error"


# PEER_RECORD := {"<ushort>":{"username":"<string>", "ipv4":"<dotted_decimal_IP>", "port": <ushort>}}

# DB_RECORD := {"<dotted_decimal_IP>,<ushort_port>":{<PEER_RECORD*>}}
