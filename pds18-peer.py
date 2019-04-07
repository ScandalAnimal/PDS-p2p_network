#!/usr/bin/python

import socket
import signal
import sys
import threading
import time
import os
from parsers import parsePeerArgs, isCommand
from protocol import encodeHELLOMessage, encodeGETLISTMessage, encodeACKMessage, decodeMessage
from util import ServiceException, UniqueIdException, signalHandler, getRandomId

helloEvent = threading.Event()
readRpcEvent = threading.Event()
getListEvent = threading.Event()
peersEvent = threading.Event()

def sendHello(sock, nodeAddress, message, username):
	while not helloEvent.is_set():
		print ("sending %s" % message)
		sent = sock.sendto(message.encode("utf-8"), nodeAddress)
		helloEvent.wait(10)
	message = encodeHELLOMessage(getRandomId(), username, "0.0.0.0", 0)
	print ("hello: " + message)
	sent = sock.sendto(message.encode("utf-8"), nodeAddress)

def sendGetList(peer):
	while not getListEvent.is_set():
		peer.sock.settimeout(2)
		message = encodeGETLISTMessage(getRandomId())
		sent = peer.sock.sendto(message.encode("utf-8"), peer.nodeAddress)
		while True:
			try:
				reply = peer.sock.recv(4096)
				decodedReply = decodeMessage(reply.decode("utf-8")).getVars()
				if decodedReply["type"] == 'ack':
					print ("GETLIST correctly acked")
					getListEvent.set()
					break
			except socket.timeout:
				print ("error: didnt get ack on getlist call")
				getListEvent.set()	
				peer.sock.settimeout(None)
				break

def sendAck(peer, txid):
	ack = encodeACKMessage(txid)
	print ("ACK: " + str(ack))
	sent = peer.sock.sendto(ack.encode("utf-8"), peer.nodeAddress)

def sendPeers(peer):
	print ("1")
	while not peersEvent.is_set():
		print ("2")
		peer.sock.settimeout(2)
		message = encodeGETLISTMessage(getRandomId())
		sent = peer.sock.sendto(message.encode("utf-8"), peer.nodeAddress)
		while True:
			try:
				reply = peer.sock.recv(4096)
				decodedReply = decodeMessage(reply.decode("utf-8")).getVars()
				if decodedReply["type"] == 'ack':
					print ("GETLIST correctly acked")
					peer.sock.settimeout(None)
					while True:
						reply = peer.sock.recv(4096)
						decodedReply = decodeMessage(reply.decode("utf-8")).getVars()
						print ("REPLY: " + str(decodedReply))
						if decodedReply["type"] == 'list':
							print ("GOT LIST: " + str(decodedReply))
							sendAck(peer, decodedReply["txid"])
							peersEvent.set()
							break
						else:
							continue
					print ("sended ack")			
					break		
				else:
					continue

			except socket.timeout:
				print ("error: didnt get ack on getlist call")
				peersEvent.set()
				peer.sock.settimeout(None)
				break

def handleCommand(command, peer):
	print ("NOVY COMMAND: " + str(command))
	if isCommand("getlist", command):
		try:
			getListThread = threading.Thread(target=sendGetList, kwargs={"peer": peer})
			getListThread.start()
		except ServiceException:
			print ("ServiceException in handleCommand")
			getListEvent.set()
			getListThread.join()
			raise ServiceException
		finally:
			getListEvent.clear()
	elif isCommand("peers", command):
		try:
			peersThread = threading.Thread(target=sendPeers, kwargs={"peer": peer})
			peersThread.start()
		except ServiceException:
			print ("ServiceException in handleCommand")
			peersEvent.set()
			peersThread.join()
			raise ServiceException
		finally:
			peersEvent.clear()

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
	def __str__(self):
		return ("Id: " + str(self.id) + ", username: " + self.username + 
			", chatIp: " + self.chatIp + ", chatPort: " + str(self.chatPort) + 
			", regIp: " + self.regIp + ", regPort: " + str(self.regPort))

def initSocket(peer):
	peer.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	peer.sock.settimeout(2)
	peer.sock.bind((peer.chatIp, peer.chatPort))
	peer.nodeAddress = (peer.regIp, peer.regPort)

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

		initSocket(peer)

		signal.signal(signal.SIGINT, signalHandler)
	
		helloMessage = encodeHELLOMessage(getRandomId(), peer.username, peer.chatIp, peer.chatPort)
		print ("hello: " + helloMessage)
		helloThread = threading.Thread(target=sendHello, args=(peer.sock, peer.nodeAddress), kwargs={"message": helloMessage, "username": peer.username})
		helloThread.start()

		readRpcThread = threading.Thread(target=readRpc, kwargs={"file": rpcFileName, "peer": peer})
		readRpcThread.start()

		while True:
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

if __name__ == "__main__":
	main()