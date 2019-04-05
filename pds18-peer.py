#!/usr/bin/python

import socket
import signal
import sys
import threading
import time
from parsers import parsePeerArgs
from protocol import getHELLOMessage
# , getGETLISTMessage, getLISTMessage, getMESSAGEMessage, getUPDATEMessage, getDISCONNECTMessage, getACKMessage, getERRORMessage

helloEvent = threading.Event()

def sendHello(sock, server_address, message):
	while not helloEvent.is_set():
		print ("sending %s" % message)
		sent = sock.sendto(message.encode("utf-8"), server_address)
		helloEvent.wait(10)

	# TODO ... Clean shutdown code here ...
	print ("CLEAN")

class ServiceException(Exception):
	pass

def signalHandler(signum, frame):
	print ('Caught signal %d' % signum) # TODO print to stderr
	raise ServiceException

class Peer:
	def __init__(self, args):
		self.id = args.id
		self.username = args.username
		self.chatIp = args.chat_ipv4
		self.chatPort = args.chat_port
		self.regIp = args.reg_ipv4
		self.regPort = args.reg_port
	def __str__(self):
		return ("Id: " + str(self.id) + ", username: " + self.username + 
			", chatIp: " + self.chatIp + ", chatPort: " + str(self.chatPort) + 
			", regIp: " + self.regIp + ", regPort: " + str(self.regPort))	


print ("PEER")

args = parsePeerArgs()

peer = Peer(args)
print ("Peer:" + str(peer))

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_address = (peer.regIp, peer.regPort)

signal.signal(signal.SIGINT, signalHandler)

try:

	helloMessage = getHELLOMessage(123, peer.username, peer.chatIp, peer.chatPort)
	print ("hello: " + helloMessage)
	helloThread = threading.Thread(target=sendHello, args=(sock, server_address), kwargs={"message": helloMessage})
	helloThread.start()

	# TODO add more functionality (recv?)
	while True:
		time.sleep(0.5)


except ServiceException:

	helloEvent.set()
	helloThread.join()

	# nulove HELLO pri kille
	message = getHELLOMessage(123, peer.username, "0.0.0.0", 0)
	print ("hello: " + message)
	sent = sock.sendto(message.encode("utf-8"), server_address)

finally:
	print ("closing socket")
	sock.close()	

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

