#!/usr/bin/python

import socket
import sys
import signal
import threading
import os
import time
from datetime import datetime, timedelta
from parsers import parseNodeArgs
from util import ServiceException, UniqueIdException, signalHandler
from protocol import decodeMessage, encodeLISTMessage

helloCheckEvent = threading.Event()
printPeerListEvent = threading.Event()
readRpcEvent = threading.Event()
listEvent = threading.Event()

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
		self.sock = None
		self.address = None
	def __str__(self):
		return ("Id: " + str(self.id) + ", regIp: " + self.regIp + ", regPort: " + str(self.regPort) + 
			", Peer count: " + str(self.peerCount) + ", Peer list: " + str(self.peerList))
	def printPeerRecords(self):
		print (str(self.peerList))
	def getPeerRecordsForListMessage(self):
		items = {}
		for k,v in self.peerList.items():
			print ("V: " + str(v))
			del v['time']
			items[k] = v
		return items

def readRpc(file):
	with open(file, 'r') as f:
		while not readRpcEvent.is_set():
			i = f.readline()
			if i != "" and i != '\n':
				print ("x: " + i)
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

def handleGetList(node, message, address):
	print ("DOSTAL SOM GETLIST: " + str(message))

	while not listEvent.is_set():
		listMessage = encodeLISTMessage(message["txid"], node.getPeerRecordsForListMessage())

		print ("message: " + str(listMessage))
		sent = node.sock.sendto(listMessage.encode("utf-8"), address)
		# getlistEvent.wait(2)
		# try:
			# reply = peer.sock.recv(4096)
			# print ("received getlist: " + reply)	
		# except socket.timeout:
			# print ("error: didnt get list on getlist call")
			# getlistEvent.set()	
		listEvent.set()	

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

		node.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

		node.address = (node.regIp, node.regPort)
		print ("starting up on %s port %s" % node.address)
		node.sock.bind(node.address)

		signal.signal(signal.SIGINT, signalHandler)
	
		helloCheckThread = threading.Thread(target=checkPeerList, kwargs={"peerList": node.peerList})
		helloCheckThread.start()
		printPeerListThread = threading.Thread(target=printPeerList, kwargs={"node": node})
		printPeerListThread.start()

		readRpcThread = threading.Thread(target=readRpc, kwargs={"file": rpcFileName})
		readRpcThread.start()

		while True:
			# print ("\nwaiting to receive message")
			data, address = node.sock.recvfrom(4096)
			
			print ("ADDRESS: " + str(address))
			# print ("received %s bytes from %s" % (len(data.decode("utf-8")), address))
			message = decodeMessage(data.decode("utf-8")).getVars()
			if message["type"] == "hello":
				handleHello(node, message)
			elif message["type"] == "getlist":
				try:
					listThread = threading.Thread(target=handleGetList, kwargs={"node": node, "message": message, "address": address})
					listThread.start()
				except ServiceException:
					print ("ServiceException 2")
					listEvent.set()
					listThread.join()
					raise ServiceException
			else:
				print ("DOSTAL som nieco ine")	

			# TODO toto pouzit na ACK
			# if data:
				# sent = sock.sendto(data, address)
				# print ("sent %s bytes back to %s" % (sent, address))

	except UniqueIdException:
		print ("UniqueIdException")
	
	except ServiceException:
		helloCheckEvent.set()
		helloCheckThread.join()
		printPeerListEvent.set()
		printPeerListThread.join()
		readRpcEvent.set()
		readRpcThread.join()
		print ("ServiceException")
	finally:
		print ("closing socket")
		if os.path.isfile(rpcFilePath):
			os.remove(rpcFilePath)
		if node.sock:
			node.sock.close()	        


if __name__ == "__main__":
	main()	