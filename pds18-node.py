#!/usr/bin/python

import socket
import sys
import signal
import threading
from datetime import datetime, timedelta
from parsers import parseNodeArgs
from util import ServiceException, signalHandler
from protocol import decodeMessage

helloCheckEvent = threading.Event()
printPeerListEvent = threading.Event()

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
	def __str__(self):
		return ("Id: " + str(self.id) + ", regIp: " + self.regIp + ", regPort: " + str(self.regPort) + 
			", Peer count: " + str(self.peerCount) + ", Peer list: " + str(self.peerList))
	def printPeerRecords(self):
		print (str(self.peerList))			

def checkPeerList(peerList):
	while not helloCheckEvent.is_set():
		toDelete = 0
		for k,v in peerList.items():
			now = datetime.now() - timedelta(seconds=30)
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

		helloCheckEvent.wait(3)

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

def main():
	print ("NODE")

	args = parseNodeArgs()

	node = Node(args)
	print ("Node:" + str(node))

	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

	server_address = (node.regIp, node.regPort)
	print ("starting up on %s port %s" % server_address)
	sock.bind(server_address)

	signal.signal(signal.SIGINT, signalHandler)

	try:

		helloCheckThread = threading.Thread(target=checkPeerList, kwargs={"peerList": node.peerList})
		helloCheckThread.start()
		printPeerListThread = threading.Thread(target=printPeerList, kwargs={"node": node})
		printPeerListThread.start()

		while True:
			# print ("\nwaiting to receive message")
			data, address = sock.recvfrom(4096)
			
			print ("ADDRESS: " + str(address))
			# print ("received %s bytes from %s" % (len(data.decode("utf-8")), address))
			message = decodeMessage(data.decode("utf-8")).getVars()
			if message["type"] == "hello":
				handleHello(node, message)
			else:
				print ("DOSTAL som nieco ine")	

			# TODO toto pouzit na ACK
			# if data:
				# sent = sock.sendto(data, address)
				# print ("sent %s bytes back to %s" % (sent, address))


	except ServiceException:
		helloCheckEvent.set()
		helloCheckThread.join()
		printPeerListEvent.set()
		printPeerListThread.join()
		print ("ServiceException")
	finally:
		print ("closing socket")
		sock.close()	        


if __name__ == "__main__":
	main()	