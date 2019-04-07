#!/usr/bin/python

import socket
import signal
import sys
import threading
import time
import os
from parsers import parsePeerArgs, isCommand
from protocol import encodeHELLOMessage, encodeGETLISTMessage, decodeMessage
from util import ServiceException, UniqueIdException, signalHandler, getRandomId
# , encodeGETLISTMessage, encodeLISTMessage, encodeMESSAGEMessage, encodeUPDATEMessage, encodeDISCONNECTMessage, encodeACKMessage, encodeERRORMessage

helloEvent = threading.Event()
readRpcEvent = threading.Event()
getlistEvent = threading.Event()

def sendHello(sock, nodeAddress, message, username):
	while not helloEvent.is_set():
		print ("sending %s" % message)
		sent = sock.sendto(message.encode("utf-8"), nodeAddress)
		helloEvent.wait(10)
	message = encodeHELLOMessage(getRandomId(), username, "0.0.0.0", 0)
	print ("hello: " + message)
	sent = sock.sendto(message.encode("utf-8"), nodeAddress)

def sendGetList(peer):
	while not getlistEvent.is_set():
		message = encodeGETLISTMessage(getRandomId())
		sent = peer.sock.sendto(message.encode("utf-8"), peer.nodeAddress)
		getlistEvent.wait(2)
		try:
			reply = peer.sock.recv(4096)
			print ("received getlist: " + str(decodeMessage(reply.decode("utf-8")).getVars()))
			getlistEvent.set()
		except socket.timeout:
			print ("error: didnt get list on getlist call")
			getlistEvent.set()	

def handleCommand(command, peer):
	if isCommand("getlist", command):
		try:
			print ("got getlist")
			peer.test = "new"

			getlistThread = threading.Thread(target=sendGetList, kwargs={"peer": peer})
			getlistThread.start()
		except ServiceException:
			print ("ServiceException in handleCommand")
			getlistEvent.set()
			getlistThread.join()
			raise ServiceException

def readRpc(file, peer):
	with open(file, 'r') as f:
		while not readRpcEvent.is_set():
			command = f.readline()
			command = command.replace("\n", "")
			if command != "" and command != '\n':
				print ("x: " + command)
				handleCommand(command, peer)
			readRpcEvent.wait(1)	

class Peer:
	def __init__(self, args):
		self.id = args.id
		self.username = args.username
		self.chatIp = args.chat_ipv4
		self.chatPort = args.chat_port
		self.regIp = args.reg_ipv4
		self.regPort = args.reg_port
		self.sock = None
		self.nodeAddress = None
		self.test = "none"
	def __str__(self):
		return ("Id: " + str(self.id) + ", username: " + self.username + 
			", chatIp: " + self.chatIp + ", chatPort: " + str(self.chatPort) + 
			", regIp: " + self.regIp + ", regPort: " + str(self.regPort))


def main():
	print ("PEER")

	args = parsePeerArgs()

	peer = Peer(args)
	print ("Peer:" + str(peer))

	rpcFilePath = ""
	try:

		rpcFileName = "peer" + str(peer.id)
		if os.path.isfile(rpcFileName):
			raise UniqueIdException
		f = open(rpcFileName, "w+")
		rpcFilePath = os.path.abspath(rpcFileName)
		f.close()

		peer.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		peer.sock.settimeout(2)
		peer.sock.bind((peer.chatIp, peer.chatPort))
		peer.nodeAddress = (peer.regIp, peer.regPort)

		signal.signal(signal.SIGINT, signalHandler)
	
		helloMessage = encodeHELLOMessage(getRandomId(), peer.username, peer.chatIp, peer.chatPort)
		print ("hello: " + helloMessage)
		helloThread = threading.Thread(target=sendHello, args=(peer.sock, peer.nodeAddress), kwargs={"message": helloMessage, "username": peer.username})
		helloThread.start()

		readRpcThread = threading.Thread(target=readRpc, kwargs={"file": rpcFileName, "peer": peer})
		readRpcThread.start()

		# TODO add more functionality (recv?)
		while True:
			# data, server = sock.recvfrom(4096)
			print (str(peer.test))
			time.sleep(2)
	except UniqueIdException:
		print ("UniqueIdException")

	except ServiceException:
		print ("ServiceException")
		helloEvent.set()
		helloThread.join()
		readRpcEvent.set()
		readRpcThread.join()

	finally:
		print ("closing socket")
		if os.path.isfile(rpcFilePath):
			os.remove(rpcFilePath)
		if peer.sock:
			peer.sock.close()	

	# getGETLISTMessage(123)
	# getLISTMessage(123, "peers")
	# getMESSAGEMessage(123, 11, 11, "asd")
	# getUPDATEMessage(123, "db")
	# getDISCONNECTMessage(123)
	# getACKMessage(123)
	# getERRORMessage(123, "asasfad")



	#     # Receive response
	#     print ("waiting to receive")
	#     data, server = sock.recvfrom(4096)
	#     print ("received "%s"" % data.decode("utf-8"))

if __name__ == "__main__":
	main()