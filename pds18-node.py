#!/usr/bin/python

import socket
import sys
import signal
import threading
import os
import time
from datetime import datetime, timedelta
from parsers import parseNodeArgs, isCommand
from util import ServiceException, Service2Exception, Service3Exception, UniqueIdException, signalHandler, printErr, getRandomId
from protocol import decodeMessage, encodeLISTMessage, encodeACKMessage, encodeUPDATEMessage

helloCheckEvent = threading.Event()
printPeerListEvent = threading.Event()
readRpcEvent = threading.Event()
getListEvent = threading.Event()
connectEvent = threading.Event()

class PeerRecordForListMessage:
	def __init__(self, username, ipv4, port):
		self.username = username
		self.ipv4 = ipv4
		self.port = port

class PeerRecord:
	def __init__(self, username, ipv4, port, time):
		self.username = username
		self.ipv4 = ipv4
		self.port = port
		self.time = time
	def getRecordForListMessage(self):
		return PeerRecordForListMessage(self.username, self.ipv4, self.port)

class Node:
	def __init__(self, args):
		self.id = args.id
		self.regIp = args.reg_ipv4
		self.regPort = args.reg_port
		self.peerCount = 0
		self.peerList = {}
		self.neighborsPeerList = {}
		self.sock = None
		self.address = None
		self.acks = {}
		self.db = {}
	def __str__(self):
		return ("Id: " + str(self.id) + ", regIp: " + self.regIp + ", regPort: " + str(self.regPort) + 
			", Peer count: " + str(self.peerCount) + ", Peer list: " + str(self.peerList))
	def printPeerRecords(self):
		print ("My Peers: ")
		print (str(self.peerList))
		print ("Neighbors Peers: ")
		print (str(self.neighborsPeerList))
	def getPeerRecordsForListMessage(self):
		items = {}
		for k,v in self.peerList.items():
			if "time" in v:
				del v['time']
			items[k] = v
		return items
	def getAuthoritativeRecordsForUpdateMessage(self):
		items = {}
		for k,v in self.peerList.items():
			if "time" in v:
				del v['time']
			items[k] = v

		dbName = str(self.regIp) + "," + str(self.regPort)
		db = {str(dbName):items}
		return db
	def isPeer(self, address):
		for k,v in self.peerList.items():
			if v["ipv4"] == address[0] and v["port"] == address[1]:
				return True
		return False		

def sendConnect(node, args):
	while not connectEvent.is_set():

		try:
			print 
			printErr ("sending connect to node: " + str((args[1], args[2])))
			txid = getRandomId()
			print (str(node.getAuthoritativeRecordsForUpdateMessage()))
			node.sock.settimeout(None)
			message = encodeUPDATEMessage(txid, node.getAuthoritativeRecordsForUpdateMessage())
			print (str(message))
			sent = node.sock.sendto(message.encode("utf-8"), (args[1], int(args[2])))
			connectEvent.wait(4)
		except ServiceException:
			printErr ("ServiceException in sendConnect")
			connectEvent.set()
			node.sock.settimeout(None)
			raise Service2Exception

def handleCommand(command, node):
	print ("NOVY COMMAND: " + str(command))
	if isCommand("database", command):
		print ("DATABASE: ")
		node.printPeerRecords()
		node.sock.settimeout(None)
	elif isCommand("connect", command):
		node.currentCommand = "connect"
		try:
			args = command.split()
			connectThread = threading.Thread(target=sendConnect, kwargs={"node": node, "args": args})
			connectThread.start()
		except ServiceException:
			printErr ("ServiceException in handleCommand")
			connectEvent.set()
			connectThread.join()
			raise Service3Exception
		finally:
			connectEvent.clear()
			node.sock.settimeout(None)

def readRpc(file, node):
	with open(file, 'r') as f:
		while not readRpcEvent.is_set():
			command = f.readline()
			command = command.replace("\n", "")
			if command != "" and command != '\n':
				print ("command: " + command)
				handleCommand(command, node)
			readRpcEvent.wait(1)		

def checkPeerList(peerList):
	while not helloCheckEvent.is_set():
		toDelete = 0
		for k,v in peerList.items():
			now = datetime.now() - timedelta(seconds=30)
			if "time" in v:
				time = v["time"]
			if now > time:
				toDelete = k
				break
		if toDelete != 0:
			del peerList[toDelete]

		helloCheckEvent.wait(1)

def printPeerList(node):
	while not printPeerListEvent.is_set():
		print ("**")
		node.printPeerRecords()
		print ("**")

		helloCheckEvent.wait(10)

def handleAck(node, message, time):
	print ("DOSTAL SOM ACK")

	if message["txid"] in node.acks:
		print ("KLUC existuje")
		allowed = time - timedelta(seconds=2)
		if allowed < node.acks[message["txid"]]:
			print ("ACK ok")
		else:
			print ("ACK not ok - prisiel po limite - ERROR")
		del node.acks[message["txid"]]	

	else:
		print ("KLUC neexistuje - to je asi ok, je nam to jedno")

def handleHello(node, message):
	print ("DOSTAL SOM HELLO")
				
	duplicity = False
	toDelete = 0
	for k,v in node.peerList.items():
		if v["username"] == message["username"]:
			if message["ipv4"] == "0.0.0.0" and message["port"] == 0:
				toDelete = k
				duplicity = True
			else:	
				duplicity = True
				v["time"] = datetime.now()
				break	
	if toDelete != 0:
		del node.peerList[toDelete]

	if not duplicity:
		node.peerList[str(node.peerCount)] = vars(PeerRecord(message["username"], message["ipv4"], message["port"], datetime.now()))
		node.peerCount += 1

def sendAck(node, txid, address):
	ack = encodeACKMessage(txid)
	print ("ACK: " + str(ack))
	sent = node.sock.sendto(ack.encode("utf-8"), address)

def handleGetList(node, message, address):
	print ("DOSTAL SOM GETLIST: " + str(message))

	while not getListEvent.is_set():
		node.sock.settimeout(2)
		if not node.isPeer(address):
			print ("dostal som GETLIST od cudzieho peera")
			getListEvent.set()
			node.sock.settimeout(None)
			break
		sendAck(node, message["txid"], address)	

		try:
			listMessage = encodeLISTMessage(message["txid"], node.getPeerRecordsForListMessage())

			print ("LIST: " + str(listMessage))
			sent = node.sock.sendto(listMessage.encode("utf-8"), address)
			node.sock.settimeout(2)
			node.acks[message["txid"]] = datetime.now()
			getListEvent.set()		
		except socket.timeout:
			print ("error: didnt get ack on list call")
			getListEvent.set()
			node.sock.settimeout(None)
			break		

def handleUpdate(node, message):
	db = message["db"]
	for k,v in db.items():
		print( "K: " + str(k))
		for k1, v1 in v.items():
			print ("peer: " + str(v1))

				
def initSocket(node):
	node.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	node.address = (node.regIp, node.regPort)
	print ("starting up on %s port %s" % node.address)
	node.sock.bind(node.address)

def main():
	print ("NODE")

	args = parseNodeArgs()

	node = Node(args)
	print ("Node:" + str(node))

	rpcFilePath = ""
	try:

		rpcFileName = "node" + str(node.id)
		if os.path.isfile(rpcFileName):
			raise UniqueIdException
		f = open(rpcFileName, "w+")
		rpcFilePath = os.path.abspath(rpcFileName)
		f.close()

		initSocket(node)

		signal.signal(signal.SIGINT, signalHandler)
	
		helloCheckThread = threading.Thread(target=checkPeerList, kwargs={"peerList": node.peerList})
		helloCheckThread.start()
		printPeerListThread = threading.Thread(target=printPeerList, kwargs={"node": node})
		printPeerListThread.start()

		readRpcThread = threading.Thread(target=readRpc, kwargs={"file": rpcFileName, "node": node})
		readRpcThread.start()

		while True:
			try:
				data, address = node.sock.recvfrom(4096)
				
				print ("ADDRESS: " + str(address))
				message = decodeMessage(data.decode("utf-8")).getVars()
				if message["type"] == "hello":
					handleHello(node, message)
				elif message["type"] == "getlist":
					try:
						getListThread = threading.Thread(target=handleGetList, kwargs={"node": node, "message": message, "address": address})
						getListThread.start()
					except ServiceException:
						print ("ServiceException 2")
						getListEvent.set()
						getListThread.join()
						raise ServiceException
					finally:
						getListEvent.clear()	
				elif message["type"] == "ack":
					node.sock.settimeout(None)
					handleAck(node, message, datetime.now())
				elif message["type"] == "update":
					node.sock.settimeout(None)
					print ("DOSTAL som UPDATE: ")
					print (str(message))
					handleUpdate(node, message)
				else:
					print ("DOSTAL som nieco ine")	
			except socket.timeout:	
				print ("error: didnt get ack call")
				node.sock.settimeout(None)
	except UniqueIdException:
		print ("UniqueIdException")
	
	except ServiceException:
		helloCheckEvent.set()
		helloCheckThread.join()
		printPeerListEvent.set()
		printPeerListThread.join()
		readRpcEvent.set()
		readRpcThread.join()
		connectEvent.set()
		print ("ServiceException")
	finally:
		print ("closing socket")
		if os.path.isfile(rpcFilePath):
			os.remove(rpcFilePath)
		if node.sock:
			node.sock.close()	        


if __name__ == "__main__":
	main()	