#!/usr/bin/python3

import socket
import sys
import signal
import threading
import os
import time
from datetime import datetime, timedelta
from parsers import parseNodeArgs, isCommand
from util import InterruptException, UniqueIdException, signalHandler, getRandomId, printCorrectErr, printDebug
from protocol import decodeMessage, encodeLISTMessage, encodeACKMessage, encodeUPDATEMessage, encodeDISCONNECTMessage, encodeERRORMessage

peerCheckEvent = threading.Event()
readRpcEvent = threading.Event()
getListEvent = threading.Event()
connectEvent = threading.Event()
updateEvent = threading.Event()
disconnectEvent = threading.Event()

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

def printPeerRecords(node):
	print ("-------------------------------------------------------------------")
	print ("|DATABASE")
	print ("|Authoritative: ")
	for k,v in node.peerList.items():
		print ("|Username: %10s, IP address: %15s, Port: %8d " % (v["username"], v["ipv4"], v["port"]))
	print ("|")	
	print ("|All: ")
	for k,v in node.db.items():
		for k1, v1 in v.items():
			if isinstance(v1, datetime):
				continue
			print ("|Username: %10s, IP address: %15s, Port: %8d " % (v1["username"], v1["ipv4"], v1["port"]))
	print ("-------------------------------------------------------------------")

def getAuthoritativeRecordsForUpdateMessage(node):
	items = {}
	for k,v in node.peerList.items():
		items[k] = vars(PeerRecordForMessage(v["username"], v["ipv4"], v["port"]))
	dbName = str(node.regIp) + "," + str(node.regPort)
	node.db[dbName] = items
	db = {str(dbName):items}
	return db

def saveAuthoritativeRecords(node):
	items = {}
	for k,v in node.peerList.items():
		items[k] = vars(PeerRecordForMessage(v["username"], v["ipv4"], v["port"]))
	dbName = str(node.regIp) + "," + str(node.regPort)
	node.db[dbName] = items

def getAllRecordsForUpdateMessage(node):
	items = {}

	for k,v in node.db.items():
		if "time" in v:
			subitems = {}
			for k1, v1 in v.items():
				if k1 != "time":
					subitems[k1] = vars(PeerRecordForMessage(v1["username"], v1["ipv4"], v1["port"]))
			items[k] = subitems		
		else:
			items[k] = v
	return items

def isPeer(node, address):
	for k,v in node.peerList.items():
		if v["ipv4"] == address[0] and v["port"] == address[1]:
			return True
	return False		

def sendUpdate(node):
	while not updateEvent.is_set():
		try:
			saveAuthoritativeRecords(node)

			for k,v in node.neighbors.items():
				splitted = k.split(",")
				ip = splitted[0]
				port = splitted[1]
				if (str(ip) == str(node.regIp)) and (str(port) == str(node.regPort)):
					continue
				printDebug ("UPDATE to: " + str(ip) + "," + str(port))	
				txid = getRandomId()
				message = encodeUPDATEMessage(txid, getAllRecordsForUpdateMessage(node))
				sent = node.sock.sendto(message.encode("utf-8"), (ip, int(port)))
			updateEvent.wait(4)
		except InterruptException:
			printCorrectErr ("InterruptException in sendUpdate")
			updateEvent.set()
			raise InterruptException

def sendConnect(node, args):
	while not connectEvent.is_set():
		try:
			printDebug ("CONNECT to: " + str(args[1]) + "," + str(args[2]))
			txid = getRandomId()
			message = encodeUPDATEMessage(txid, getAuthoritativeRecordsForUpdateMessage(node))
			sent = node.sock.sendto(message.encode("utf-8"), (args[1], int(args[2])))
			connectEvent.set()
		except InterruptException:
			printCorrectErr ("InterruptException in sendConnect")
			connectEvent.set()
			raise InterruptException

def sendDisconnect(node):
	while not disconnectEvent.is_set():
		try:
			for k,v in node.neighbors.items():
				splitted = k.split(",")
				ip = splitted[0]
				port = splitted[1]
				if (str(ip) == str(node.regIp)) and (str(port) == str(node.regPort)):
					continue
				printDebug ("DISCONNECT to: " + str(ip) + "," + str(port))
				txid = getRandomId()
				message = encodeDISCONNECTMessage(txid)
				sent = node.sock.sendto(message.encode("utf-8"), (ip, int(port)))
				node.acks[txid] = datetime.now()

			node.db.clear()
			node.neighbors.clear()
			saveAuthoritativeRecords(node)

			disconnectEvent.set()

		except InterruptException:
			printCorrectErr ("InterruptException in sendDisconnect")
			disconnectEvent.set()
			raise InterruptException			

def handleSync(node):

	try:
		saveAuthoritativeRecords(node)

		for k,v in node.neighbors.items():
			splitted = k.split(",")
			ip = splitted[0]
			port = splitted[1]
			if (str(ip) == str(node.regIp)) and (str(port) == str(node.regPort)):
				continue
			txid = getRandomId()
			message = encodeUPDATEMessage(txid, getAllRecordsForUpdateMessage(node))
			sent = node.sock.sendto(message.encode("utf-8"), (ip, int(port)))
	except InterruptException:
		printCorrectErr ("InterruptException in handleSync")
		raise InterruptException
	finally:
		print ("RPC Sync finished.")

def handleNeighbors(node):
	print ("-------------------------------------------------------------------")
	print ("|NEIGHBORS")
	for k,v in node.neighbors.items():
		splitted = k.split(",")
		if str(splitted[0]) == str(node.regIp) and str(splitted[1]) == str(node.regPort):
			continue
		print ("|IP address: %15s, Port: %8s " % (splitted[0], splitted[1]))
	print ("-------------------------------------------------------------------")
	print ("RPC Neighbors finished.")


def handleCommand(command, node):
	if isCommand("database", command):
		printPeerRecords(node)
		print ("RPC Database finished.")

	elif isCommand("connect", command):
		node.currentCommand = "connect"
		try:
			args = command.split()
			connectThread = threading.Thread(target=sendConnect, kwargs={"node": node, "args": args})
			connectThread.start()
		except InterruptException:
			printCorrectErr ("InterruptException in handleCommand")
			connectEvent.set()
			connectThread.join()
			raise InterruptException
		finally:
			connectEvent.clear()
			print ("RPC Connect finished.")

	elif isCommand("neighbors", command):
		handleNeighbors(node)
	elif isCommand("sync", command):
		handleSync(node)
	elif isCommand("disconnect", command):
		node.currentCommand = "disconnect"
		try:
			disconnectThread = threading.Thread(target=sendDisconnect, kwargs={"node": node})
			disconnectThread.start()
		except InterruptException:
			printCorrectErr ("InterruptException in handleCommand")
			disconnectEvent.set()
			disconnectThread.join()
			raise InterruptException
		finally:
			disconnectEvent.clear()
			print ("RPC Disconnect finished.")

def readRpc(file, node):
	with open(file, 'r') as f:
		while not readRpcEvent.is_set():
			command = f.readline()
			command = command.replace("\n", "")
			if command != "" and command != '\n':
				handleCommand(command, node)
			readRpcEvent.wait(1)		

def checkPeerList(node):
	while not peerCheckEvent.is_set():
		toDelete = 0
		for k,v in node.peerList.items():
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
			now = datetime.now() - timedelta(seconds=12)
			if "time" in v:
				time = v["time"]
				if now > time:
					toDelete = k
					break
		if toDelete != 0:
			del node.db[toDelete]

		peerCheckEvent.wait(1)

def handleAck(node, message, time):

	if message["txid"] in node.acks:
		allowed = time - timedelta(seconds=2)
		if allowed < node.acks[message["txid"]]:
			printDebug ("ACK ok")
		else:
			printDebug ("ACK not ok - after timeout")
		del node.acks[message["txid"]]	

def handleHello(node, message):
	printDebug ("HELLO from: " + str(message["ipv4"]) + "," + str(message["port"]))
				
	duplicity = False
	toDelete = False
	for k,v in node.peerList.items():
		if v["username"] == message["username"]:
			if message["ipv4"] == "0.0.0.0" and message["port"] == 0:
				toDelete = k
				duplicity = True
			else:	
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
	printDebug ("ACK: " + str(ack) + ", to: " + str(address[0]) + "," + str(address[1]))
	sent = node.sock.sendto(ack.encode("utf-8"), address)

def sendError(node, txid, address, message):
	err = encodeERRORMessage(txid, message)
	printDebug ("ERROR: " + str(err) + ", to: " + str(address[0]) + "," + str(address[1]))
	sent = node.sock.sendto(err.encode("utf-8"), address)

def handleGetList(node, message, address):
	printDebug ("GETLIST from: " + str(address))

	while not getListEvent.is_set():
		if not isPeer(node, address):
			printCorrectErr ("GETLIST is from foreign peer, killing it")
			getListEvent.set()
			sendError(node, message["txid"], address, "You tried to get peer list from node that you are not paired with.")
			break
		sendAck(node, message["txid"], address)	

		listMessage = encodeLISTMessage(message["txid"], getAllRecordsForUpdateMessage(node))
		printDebug ("LIST to: " + str(address))
		sent = node.sock.sendto(listMessage.encode("utf-8"), address)
		node.acks[message["txid"]] = datetime.now()
		getListEvent.set()		

def handleUpdate(node, message, address):
	db = message["db"]
	formattedAddress = str(address[0]) + "," + str(address[1])
	for k,v in db.items():
		if k == formattedAddress:
			v["time"] = datetime.now()
			node.db[k] = v
		node.neighbors[k] = k

def handleDisconnect(node, txid, address):
	disconnectIp = address[0]
	disconnectPort = address[1]
	disconnectAddress = str(disconnectIp) + "," + str(disconnectPort)
	sendAck(node, txid, address)
	toDelete = 0
	for k,v in node.db.items():
		if k == str(disconnectAddress):
			toDelete = k
			break
	if toDelete != 0:
		del node.db[toDelete]	
	toDelete = 0
	for k,v in node.neighbors.items():
		if k == str(disconnectAddress):
			toDelete = k
			break
	if toDelete != 0:
		del node.neighbors[toDelete]

def initSocket(node):
	node.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	node.address = (node.regIp, node.regPort)
	try:
		node.sock.bind(node.address)
	except OSError:
		printCorrectErr ("Port already in use, try another")
		raise UniqueIdException

def main():
	args = parseNodeArgs()
	node = Node(args)
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
		updateThread = threading.Thread(target=sendUpdate, kwargs={"node": node})
		updateThread.start()

		readRpcThread = threading.Thread(target=readRpc, kwargs={"file": rpcFileName, "node": node})
		readRpcThread.start()

		while True:
			data, address = node.sock.recvfrom(4096)
			
			try:
				message = decodeMessage(data.decode("utf-8")).getVars()
			except ValueError:
				sendError(node, message["txid"], address, "Cannot parse message.")
				continue

			if message["type"] == "hello":
				handleHello(node, message)
			elif message["type"] == "getlist":
				try:
					getListThread = threading.Thread(target=handleGetList, kwargs={"node": node, "message": message, "address": address})
					getListThread.start()
				except InterruptException:
					print ("InterruptException")
					getListEvent.set()
					getListThread.join()
					raise InterruptException
				finally:
					getListEvent.clear()	
			elif message["type"] == "ack":
				handleAck(node, message, datetime.now())
			elif message["type"] == "update":
				printDebug("UPDATE from: " + str(address[0]) + "," + str(address[1]))
				handleUpdate(node, message, address)
			elif message["type"] == "disconnect":	
				printDebug ("DISCONNECT from: " + str(address[0]) + "," + str(address[1]))
				handleDisconnect(node, message["txid"], address)
			else:
				printCorrectErr ("Unexpected message: " + str(message))	
	except UniqueIdException:
		printCorrectErr ("UniqueIdException")
	
	except InterruptException:
		peerCheckEvent.set()
		peerCheckThread.join()
		readRpcEvent.set()
		readRpcThread.join()
		connectEvent.set()
		sendDisconnect(node)
		disconnectEvent.set()
		updateEvent.set()
		printCorrectErr ("InterruptException")
	finally:
		if os.path.isfile(rpcFilePath):
			os.remove(rpcFilePath)
		if node.sock:
			node.sock.close()	        


if __name__ == "__main__":
	main()	