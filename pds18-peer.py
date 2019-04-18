#!/usr/bin/python

import socket
import signal
import sys
import threading
import time
import os
from datetime import datetime, timedelta
from parsers import parsePeerArgs, isCommand
from protocol import encodeHELLOMessage, encodeGETLISTMessage, encodeACKMessage, encodeMESSAGEMessage, decodeMessage, encodeERRORMessage
from util import InterruptException, UniqueIdException, signalHandler, getRandomId, printCorrectErr, printDebug

helloEvent = threading.Event()
readRpcEvent = threading.Event()
messageEvent = threading.Event()

def sendHello(peer, message):
	while not helloEvent.is_set():
		printDebug ("HELLO to: " + str((peer.regIp, peer.regPort)))
		sent = peer.sock.sendto(message.encode("utf-8"), (peer.regIp, peer.regPort))
		helloEvent.wait(10)
	message = encodeHELLOMessage(getRandomId(), peer.username, "0.0.0.0", 0)
	printDebug ("HELLO to: " + str((peer.regIp, peer.regPort)))
	sent = peer.sock.sendto(message.encode("utf-8"), (peer.regIp, peer.regPort))

def handleAck(peer, message, time):
	if message["txid"] in peer.acks:
		allowed = time - timedelta(seconds=2)
		if allowed < peer.acks[message["txid"]]:
			printDebug ("ACK ok")
		else:
			printDebug ("ACK not ok")
		del peer.acks[message["txid"]]

def sendGetList(peer):
	txid = getRandomId()
	message = encodeGETLISTMessage(txid)
	sent = peer.sock.sendto(message.encode("utf-8"), peer.nodeAddress)
	peer.acks[txid] = datetime.now()
	peer.currentPhase = 1
	printDebug ("GETLIST to: " + str(peer.nodeAddress))

def sendAck(peer, txid, address):
	ack = encodeACKMessage(txid)
	printDebug ("ACK: " + str(ack) + ", to: " + str(address[0]) + "," + str(address[1]))
	sent = peer.sock.sendto(ack.encode("utf-8"), address)

def sendError(node, txid, address, message):
	err = encodeERRORMessage(txid, message)
	printDebug ("ERROR: " + str(err) + ", to: " + str(address[0]) + "," + str(address[1]))
	sent = peer.sock.sendto(err.encode("utf-8"), address)

def sendPeers(peer):
	sendGetList(peer)
	peer.currentPhase = 2

def findUserInPeerList(peers, user):

	for k,v in peers.items():
		for k1,v1 in v.items():
			if v1["username"] == user:
				return (v1["ipv4"], v1["port"])
	return None		

def sendMessage(peer, peerList):
	while not messageEvent.is_set():
		to = peer.currentCommandParams[2]
		contents = peer.currentCommandParams[3:]
		recipientAddress = findUserInPeerList(peerList, to)
		if recipientAddress:
			txid = getRandomId()
			message = encodeMESSAGEMessage(txid, peer.username, to, contents)
			printDebug ("MESSAGE to: " + str(recipientAddress))
			sent = peer.sock.sendto(message.encode("utf-8"), recipientAddress)
			peer.acks[txid] = datetime.now()
			peer.currentPhase = 3
		else:
			printCorrectErr ("Trying to send message to nonexistent peer")	
		messageEvent.set()

def handleMessage(peer, peerList):

	try:
		messageThread = threading.Thread(target=sendMessage, kwargs={"peer": peer, "peerList": peerList})
		messageThread.start()
	except InterruptException:
		printCorrectErr ("InterruptException in handleCommand")
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
	printDebug ("RPC command: " + str(command))
	if isCommand("getlist", command):
		peer.currentCommand = "getlist"
		sendGetList(peer)
	elif isCommand("peers", command):
		peer.currentCommand = "peers"
		sendPeers(peer)
	elif isCommand("message", command):
		peer.currentCommand = "message"
		args = command.split()
		peer.currentCommandParams = args
		if peer.username != args[1]:
			printCorrectErr ("You are trying to send message from different peer than this one")
		else:
			try:
				messageThread = threading.Thread(target=sendPeers, kwargs={"peer": peer})
				messageThread.start()
			except InterruptException:
				printCorrectErr ("InterruptException in handleCommand")
				messageEvent.set()
				messageThread.join()
				raise InterruptException
			finally:
				messageEvent.clear()
	elif isCommand("reconnect", command):
		args = command.split()
		handleReconnect(peer, args)
	else:
		printDebug ("Command not recognized: " + str(command))	

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
def initSocket(peer):
	peer.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	try:
		peer.sock.bind((peer.chatIp, peer.chatPort))
	except OSError:
		printCorrectErr ("Port already in use, try another")
		raise UniqueIdException
	peer.nodeAddress = (peer.regIp, peer.regPort)

def main():

	args = parsePeerArgs()
	peer = Peer(args)
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
		helloThread = threading.Thread(target=sendHello, kwargs={"peer": peer, "message": helloMessage})
		helloThread.start()

		readRpcThread = threading.Thread(target=readRpc, kwargs={"file": rpcFileName, "peer": peer})
		readRpcThread.start()

		while True:
			data, address = peer.sock.recvfrom(4096)
			
			try:
				message = decodeMessage(data.decode("utf-8")).getVars()
			except ValueError:
				sendError(node, message["txid"], address, "Cannot parse message.")
				continue

			if message["type"] == 'ack':
				if peer.currentCommand == "getlist" and peer.currentPhase == 1:
					printDebug ("ACK for GETLIST")
					handleAck(peer, message, datetime.now())
				elif peer.currentCommand == "message" and peer.currentPhase == 3:
					handleAck(peer, message, datetime.now())	
			elif message["type"] == 'list':
				if peer.currentCommand == "peers" and peer.currentPhase == 2:
					printDebug ("LIST from: " + str(address))
					print ("-------------------------------------------------------------------")
					print ("|PEERS")
					for k,v in message["peers"].items():
						for k1,v1 in v.items():
							print ("|Username: %10s, IP address: %15s, Port: %8d " % (v1["username"], v1["ipv4"], v1["port"]))
					print ("-------------------------------------------------------------------")

					sendAck(peer, message["txid"], address)
				elif peer.currentCommand == "message" and peer.currentPhase == 2:
					handleMessage(peer, message['peers'])
			elif message["type"] == 'message':
				if message["to"] == peer.username:
					printDebug ("MESSAGE from: " + str(address[0]) + "," + str(address[1]) + ": " + message["message"])
					sendAck(peer, message["txid"], address)
				else:
					printCorrectErr ("You got message for different recipient")
					sendError(peer, message["txid"], address, "You sent message to wrong peer.")
			else:
				printCorrectErr ("Unexpected message: " + message)	

	except UniqueIdException:
		printCorrectErr ("UniqueIdException")

	except InterruptException:
		printCorrectErr ("InterruptException")
		helloEvent.set()
		helloThread.join()
		readRpcEvent.set()
		readRpcThread.join()

	finally:
		if os.path.isfile(rpcFilePath):
			os.remove(rpcFilePath)
		if peer.sock:
			peer.sock.close()	

if __name__ == "__main__":
	main()