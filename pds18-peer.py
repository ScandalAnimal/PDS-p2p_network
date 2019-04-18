#!/usr/bin/python

import socket
import signal
import sys
import threading
import time
import os
from datetime import datetime, timedelta
from parsers import parsePeerArgs, isCommand
from protocol import encodeHELLOMessage, encodeGETLISTMessage, encodeACKMessage, encodeMESSAGEMessage, decodeMessage
from util import InterruptException, UniqueIdException, signalHandler, getRandomId, printErr, printCorrectErr

helloEvent = threading.Event()
readRpcEvent = threading.Event()
getListEvent = threading.Event()
peersEvent = threading.Event()
messageEvent = threading.Event()

def sendHello(peer, message):
	while not helloEvent.is_set():
		printCorrectErr ("HELLO to: " + str((peer.regIp, peer.regPort)))
		sent = peer.sock.sendto(message.encode("utf-8"), (peer.regIp, peer.regPort))
		helloEvent.wait(10)
	message = encodeHELLOMessage(getRandomId(), peer.username, "0.0.0.0", 0)
	printCorrectErr ("HELLO to: " + str((peer.regIp, peer.regPort)))
	sent = peer.sock.sendto(message.encode("utf-8"), (peer.regIp, peer.regPort))

def handleAck(peer, message, time):
	printErr ("DOSTAL SOM ACK")

	if message["txid"] in peer.acks:
		printErr ("KLUC existuje")
		allowed = time - timedelta(seconds=2)
		if allowed < peer.acks[message["txid"]]:
			printErr ("ACK ok")
		else:
			printErr ("ACK not ok - prisiel po limite - ERROR")
		del peer.acks[message["txid"]]	

	else:
		printErr ("KLUC neexistuje - to je asi ok, je nam to jedno")

def sendGetList(peer):
	while not getListEvent.is_set():
		peer.sock.settimeout(2)
		txid = getRandomId()
		message = encodeGETLISTMessage(txid)
		sent = peer.sock.sendto(message.encode("utf-8"), peer.nodeAddress)
		peer.acks[txid] = datetime.now()
		peer.currentPhase = 1
		getListEvent.set()
		printCorrectErr ("GETLIST to: " + str(peer.nodeAddress))

def sendAck(peer, txid, address):
	ack = encodeACKMessage(txid)
	printErr ("ACK: " + str(ack))
	sent = peer.sock.sendto(ack.encode("utf-8"), address)

def sendPeers(peer):

	while not peersEvent.is_set():
		try:
			getListThread = threading.Thread(target=sendGetList, kwargs={"peer": peer})
			getListThread.start()
		except InterruptException:
			printErr ("InterruptException in handleCommand")
			getListEvent.set()
			getListThread.join()
			raise InterruptException
		finally:
			getListEvent.clear()
			peersEvent.set()

		print ("SENT PEERS")
		peer.currentPhase = 2

def findUserInPeerList(peers, user):
	for k,v in peers.items():
		if v["username"] == user:
			return (v["ipv4"], v["port"])
	return None		

def sendMessage(peer, peerList):
	while not messageEvent.is_set():
		to = peer.currentCommandParams[2]
		contents = peer.currentCommandParams[3:]
		recipientAddress = findUserInPeerList(peerList, to)
		if recipientAddress:
			peer.sock.settimeout(2)
			txid = getRandomId()
			message = encodeMESSAGEMessage(txid, peer.username, to, contents)
			print ("sending message: " + str(message))

			sent = peer.sock.sendto(message.encode("utf-8"), recipientAddress)
			peer.acks[txid] = datetime.now()
			peer.currentPhase = 3
		else:
			printErr ("address NOT FOUND in list")	
		messageEvent.set()

def handleMessage(peer, peerList):

	try:
		messageThread = threading.Thread(target=sendMessage, kwargs={"peer": peer, "peerList": peerList})
		messageThread.start()
	except InterruptException:
		printErr ("InterruptException in handleCommand")
		messageEvent.set()
		messageThread.join()
		raise InterruptException
	finally:
		messageEvent.clear()
	
def handleReconnect(peer, args):
	newIp = args[1]
	newPort = args[2]

	nodeAddress = (peer.regIp, peer.regPort)
	message = encodeHELLOMessage(getRandomId(), peer.username, "0.0.0.0", 0)
	sent = peer.sock.sendto(message.encode("utf-8"), nodeAddress)
	peer.regIp = newIp
	peer.regPort = int(newPort)
	nodeAddress = (peer.regIp, peer.regPort)
	message = encodeHELLOMessage(getRandomId(), peer.username, peer.chatIp, peer.chatPort)
	sent = peer.sock.sendto(message.encode("utf-8"), nodeAddress)

def handleCommand(command, peer):
	printErr ("NOVY COMMAND: " + str(command))
	if isCommand("getlist", command):
		peer.currentCommand = "getlist"
		try:
			getListThread = threading.Thread(target=sendGetList, kwargs={"peer": peer})
			getListThread.start()
		except InterruptException:
			printErr ("InterruptException in handleCommand")
			getListEvent.set()
			getListThread.join()
			raise InterruptException
		finally:
			getListEvent.clear()
	elif isCommand("peers", command):
		peer.currentCommand = "peers"
		try:
			peersThread = threading.Thread(target=sendPeers, kwargs={"peer": peer})
			peersThread.start()
		except InterruptException:
			printErr ("InterruptException in handleCommand")
			peersEvent.set()
			peersThread.join()
			raise InterruptException
		finally:
			peersEvent.clear()
	elif isCommand("message", command):
		peer.currentCommand = "message"
		args = command.split()
		peer.currentCommandParams = args
		if peer.username != args[1]:
			printErr ("ERROR - pokusas sa poslat spravu z ineho peera ako sam od seba")
		else:
			try:
				messageThread = threading.Thread(target=sendPeers, kwargs={"peer": peer})
				messageThread.start()
			except InterruptException:
				printErr ("InterruptException in handleCommand")
				messageEvent.set()
				messageThread.join()
				raise InterruptException
			finally:
				messageEvent.clear()
	elif isCommand("reconnect", command):
		args = command.split()
		handleReconnect(peer, args)
		printErr ("DID reconnect")
	else:
		print ("ZIADNY COMMAND")	

def resetPeerState(peer):
	peer.currentCommand = None
	peer.currentCommandParams = []
	peer.currentPhase = None

def readRpc(file, peer):
	with open(file, 'r') as f:
		while not readRpcEvent.is_set():
			command = f.readline()
			command = command.replace("\n", "")
			if command != "" and command != '\n':
				printErr ("command: " + command)
				resetPeerState(peer)
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
		self.acks = {}
		self.currentCommand = None
		self.currentCommandParams = []
		self.currentPhase = None
	def __str__(self):
		return ("Id: " + str(self.id) + ", username: " + self.username + 
			", chatIp: " + self.chatIp + ", chatPort: " + str(self.chatPort) + 
			", regIp: " + self.regIp + ", regPort: " + str(self.regPort))

def initSocket(peer):
	peer.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	peer.sock.settimeout(2)
	try:
		peer.sock.bind((peer.chatIp, peer.chatPort))
	except OSError:
		printErr ("Port already in use")
		raise UniqueIdException
	peer.nodeAddress = (peer.regIp, peer.regPort)

def main():
	printErr ("PEER")

	args = parsePeerArgs()

	peer = Peer(args)
	printErr ("Peer:" + str(peer))

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
		# printErr ("hello: " + helloMessage)
		helloThread = threading.Thread(target=sendHello, kwargs={"peer": peer, "message": helloMessage})
		helloThread.start()

		readRpcThread = threading.Thread(target=readRpc, kwargs={"file": rpcFileName, "peer": peer})
		readRpcThread.start()

		while True:
			try:
				data, address = peer.sock.recvfrom(4096)
				
				message = decodeMessage(data.decode("utf-8")).getVars()
				if message["type"] == 'ack':
					if peer.currentCommand == "getlist" and peer.currentPhase == 1:
						peer.sock.settimeout(None)
						print ("ACK NA GETLIST")
						handleAck(peer, message, datetime.now())
					elif peer.currentCommand == "message" and peer.currentPhase == 3:
						peer.sock.settimeout(None)
						handleAck(peer, message, datetime.now())	
				elif message["type"] == 'list':
					if peer.currentCommand == "peers" and peer.currentPhase == 2:
						printErr ("GOT LIST: " + str(message['peers']))
						sendAck(peer, message["txid"], address)
					elif peer.currentCommand == "message" and peer.currentPhase == 2:
						handleMessage(peer, message['peers'])
				elif message["type"] == 'message':
					if message["to"] == peer.username:
						print ("GOT MESSAGE: " + str(message))
						sendAck(peer, message["txid"], address)
					else:
						printErr ("dostal som spravu pre niekoho ineho")	
				else:
					printErr ("DOSTAL som nieco ine")	
			except socket.timeout:	
				printErr ("TIMEOUT")
				peer.sock.settimeout(None)


	except UniqueIdException:
		printErr ("UniqueIdException")

	except InterruptException:
		printErr ("InterruptException")
		helloEvent.set()
		helloThread.join()
		readRpcEvent.set()
		readRpcThread.join()

	finally:
		printErr ("closing socket")
		if os.path.isfile(rpcFilePath):
			os.remove(rpcFilePath)
		if peer.sock:
			peer.sock.close()	

if __name__ == "__main__":
	main()