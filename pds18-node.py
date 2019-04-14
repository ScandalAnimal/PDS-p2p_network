#!/usr/bin/python

import socket
import sys
import signal
import threading
import os
import time
from datetime import datetime, timedelta
from parsers import parseNodeArgs, isCommand
from util import ServiceException, UniqueIdException, signalHandler, printErr, getRandomId
from protocol import decodeMessage, encodeLISTMessage, encodeACKMessage, encodeUPDATEMessage

peerCheckEvent = threading.Event()
printPeerListEvent = threading.Event()
readRpcEvent = threading.Event()
getListEvent = threading.Event()
connectEvent = threading.Event()
updateEvent = threading.Event()

class PeerRecordForMessage:
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
		return PeerRecordForMessage(self.username, self.ipv4, self.port)

class Node:
	def __init__(self, args):
		self.id = args.id
		self.regIp = args.reg_ipv4
		self.regPort = args.reg_port
		self.peerCount = 0
		self.peerList = {}
		self.sock = None
		self.address = None
		self.acks = {}
		self.db = {}
		self.neighbors = {}
	def __str__(self):
		return ("Id: " + str(self.id) + ", regIp: " + self.regIp + ", regPort: " + str(self.regPort) + 
			", Peer count: " + str(self.peerCount) + ", Peer list: " + str(self.peerList))
	def printPeerRecords(self):
		# print ("")
		print ("My Peers: ")
		print (str(self.peerList))
		print ("Neighbors Peers: ")
		print (str(self.db))
	def getPeerRecordsForListMessage(self):
		items = {}
		for k,v in self.peerList.items():
			items[k] = vars(PeerRecordForMessage(v["username"], v["ipv4"], v["port"]))
		return items
	def getAuthoritativeRecordsForUpdateMessage(self):
		items = {}
		for k,v in self.peerList.items():
			items[k] = vars(PeerRecordForMessage(v["username"], v["ipv4"], v["port"]))
		dbName = str(self.regIp) + "," + str(self.regPort)
		self.db[dbName] = items
		db = {str(dbName):items}
		return db
	def saveAuthoritativeRecords(self):
		items = {}
		# print ("PEERLIST: " + str(self.peerList))
		for k,v in self.peerList.items():
			items[k] = vars(PeerRecordForMessage(v["username"], v["ipv4"], v["port"]))
			# items[k] = v
		# print ("PEERLIST: " + str(self.peerList))
		dbName = str(self.regIp) + "," + str(self.regPort)
		self.db[dbName] = items
			
	def getAllRecordsForUpdateMessage(self):
		items = {}
		for k,v in self.db.items():
			print ("K: " + str(k))
			print ("V: " + str(v))
			if "time" in v:
				for k1, v1 in v.items():
					if k1 != "time":
						items[k] = vars(PeerRecordForMessage(v1["username"], v1["ipv4"], v1["port"]))
			else:
				items[k] = v
		return items

	def isPeer(self, address):
		for k,v in self.peerList.items():
			if v["ipv4"] == address[0] and v["port"] == address[1]:
				return True
		return False		

def sendUpdate(node):
	while not updateEvent.is_set():

		try:
			node.saveAuthoritativeRecords()

			for k,v in node.neighbors.items():
				splitted = k.split(",")
				ip = splitted[0]
				port = splitted[1]
				# print ("MESSAGE TO: " + ip + " " + port)
				# print ("ME: " + str(node.regIp) + " " + str(node.regPort))
				if (str(ip) == str(node.regIp)) and (str(port) == str(node.regPort)):
					# print ("SENDING TO MYSELF")
					continue
				# print ("AFTER")	
				txid = getRandomId()
				message = encodeUPDATEMessage(txid, node.getAllRecordsForUpdateMessage())
				# print ("message: " + str(node.getAllRecordsForUpdateMessage()))
				sent = node.sock.sendto(message.encode("utf-8"), (ip, int(port)))
			updateEvent.wait(4)
		except ServiceException:
			printErr ("ServiceException in sendUpdate")
			updateEvent.set()
			node.sock.settimeout(None)
			raise ServiceException

def sendConnect(node, args):
	while not connectEvent.is_set():

		try:
			# printErr ("sending connect to node: " + str((args[1], args[2])))
			txid = getRandomId()
			# print (str(node.getAuthoritativeRecordsForUpdateMessage()))
			node.sock.settimeout(None)
			message = encodeUPDATEMessage(txid, node.getAuthoritativeRecordsForUpdateMessage())
			# print (str(message))
			sent = node.sock.sendto(message.encode("utf-8"), (args[1], int(args[2])))
			connectEvent.set()
		except ServiceException:
			printErr ("ServiceException in sendConnect")
			connectEvent.set()
			node.sock.settimeout(None)
			raise ServiceException

def handleNeighbors(node):
	print ("NEIGHBORS: " + str(node.neighbors))

def handleCommand(command, node):
	# print ("NOVY COMMAND: " + str(command))
	if isCommand("database", command):
		# print ("DATABASE: ")
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
			raise ServiceException
		finally:
			connectEvent.clear()
			node.sock.settimeout(None)
	elif isCommand("neighbors", command):
		handleNeighbors(node)
		node.sock.settimeout(None)		

def readRpc(file, node):
	with open(file, 'r') as f:
		while not readRpcEvent.is_set():
			command = f.readline()
			command = command.replace("\n", "")
			if command != "" and command != '\n':
				# print ("command: " + command)
				handleCommand(command, node)
			readRpcEvent.wait(1)		

def checkPeerList(node):
	while not peerCheckEvent.is_set():
		toDelete = 0
		# print (str(node.peerList))
		for k,v in node.peerList.items():
			# print ("checking: " + str(v))
			now = datetime.now() - timedelta(seconds=30)
			if "time" in v:
				time = v["time"]
				if now > time:
					toDelete = k
					break
		if toDelete != 0:
			del node.peerList[toDelete]

		toDelete = 0
		for k,v in node.db.items():
			# print ("checking: " + str(v))
			now = datetime.now() - timedelta(seconds=12)
			if "time" in v:
				time = v["time"]
				if now > time:
					toDelete = k
					break
		if toDelete != 0:
			del node.db[toDelete]

		peerCheckEvent.wait(5)

def printPeerList(node):
	while not printPeerListEvent.is_set():
		print ("**PEERS**")
		node.printPeerRecords()
		print ("**")

		peerCheckEvent.wait(10)

def handleAck(node, message, time):
	# print ("DOSTAL SOM ACK")

	if message["txid"] in node.acks:
		# print ("KLUC existuje")
		allowed = time - timedelta(seconds=2)
		if allowed < node.acks[message["txid"]]:
			print ("ACK ok")
		else:
			print ("ACK not ok - prisiel po limite - ERROR")
		del node.acks[message["txid"]]	

	else:
		print ("KLUC neexistuje - to je asi ok, je nam to jedno")

def handleHello(node, message):
	# print ("DOSTAL SOM HELLO")
				
	duplicity = False
	toDelete = False
	for k,v in node.peerList.items():
		if v["username"] == message["username"]:
			if message["ipv4"] == "0.0.0.0" and message["port"] == 0:
				toDelete = k
				duplicity = True
			else:	
				print ("ALREADY")
				duplicity = True
				v["time"] = datetime.now()
				node.peerList[k] = v
				break	
	if toDelete != False:
		del node.peerList[toDelete]

	if not duplicity:
		node.peerList[str(node.peerCount)] = vars(PeerRecord(message["username"], message["ipv4"], message["port"], datetime.now()))
		node.peerCount += 1

def sendAck(node, txid, address):
	ack = encodeACKMessage(txid)
	# print ("ACK: " + str(ack))
	sent = node.sock.sendto(ack.encode("utf-8"), address)

def handleGetList(node, message, address):
	# print ("DOSTAL SOM GETLIST: " + str(message))

	while not getListEvent.is_set():
		node.sock.settimeout(2)
		if not node.isPeer(address):
			# print ("dostal som GETLIST od cudzieho peera")
			getListEvent.set()
			node.sock.settimeout(None)
			break
		sendAck(node, message["txid"], address)	

		try:
			listMessage = encodeLISTMessage(message["txid"], node.getPeerRecordsForListMessage())

			# print ("LIST: " + str(listMessage))
			sent = node.sock.sendto(listMessage.encode("utf-8"), address)
			node.sock.settimeout(2)
			node.acks[message["txid"]] = datetime.now()
			getListEvent.set()		
		except socket.timeout:
			print ("error: didnt get ack on list call")
			getListEvent.set()
			node.sock.settimeout(None)
			break		

def handleUpdate(node, message, address):
	db = message["db"]
	formattedAddress = str(address[0]) + "," + str(address[1])
	# print ("formattedAddress: " + str(formattedAddress))
	for k,v in db.items():
		print( "K: " + str(k))
		if k == formattedAddress:
			v["time"] = datetime.now()
			node.db[k] = v
		node.neighbors[k] = k

				
def initSocket(node):
	node.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	node.address = (node.regIp, node.regPort)
	# print ("starting up on %s port %s" % node.address)
	node.sock.bind(node.address)

def main():
	# print ("NODE")

	args = parseNodeArgs()

	node = Node(args)
	# print ("Node:" + str(node))

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
	
		peerCheckThread = threading.Thread(target=checkPeerList, kwargs={"node": node})
		peerCheckThread.start()
		printPeerListThread = threading.Thread(target=printPeerList, kwargs={"node": node})
		printPeerListThread.start()
		updateThread = threading.Thread(target=sendUpdate, kwargs={"node": node})
		updateThread.start()

		readRpcThread = threading.Thread(target=readRpc, kwargs={"file": rpcFileName, "node": node})
		readRpcThread.start()

		while True:
			try:
				data, address = node.sock.recvfrom(4096)
				
				# print ("ADDRESS: " + str(address))
				message = decodeMessage(data.decode("utf-8")).getVars()
				if message["type"] == "hello":
					handleHello(node, message)
				elif message["type"] == "getlist":
					try:
						getListThread = threading.Thread(target=handleGetList, kwargs={"node": node, "message": message, "address": address})
						getListThread.start()
					except ServiceException:
						print ("ServiceException")
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
					# print ("DOSTAL som UPDATE: ")
					# print (str(message))
					handleUpdate(node, message, address)
				else:
					print ("DOSTAL som nieco ine")	
			except socket.timeout:	
				print ("error: didnt get ack call")
				node.sock.settimeout(None)
	except UniqueIdException:
		print ("UniqueIdException")
	
	except ServiceException:
		peerCheckEvent.set()
		peerCheckThread.join()
		printPeerListEvent.set()
		printPeerListThread.join()
		readRpcEvent.set()
		readRpcThread.join()
		connectEvent.set()
		updateEvent.set()
		print ("ServiceException")
	finally:
		print ("closing socket")
		if os.path.isfile(rpcFilePath):
			os.remove(rpcFilePath)
		if node.sock:
			node.sock.close()	        


if __name__ == "__main__":
	main()	