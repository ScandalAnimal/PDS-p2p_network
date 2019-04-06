#!/usr/bin/python

import socket
import signal
import sys
import threading
import time
from parsers import parsePeerArgs
from protocol import encodeHELLOMessage
from util import ServiceException, signalHandler, getRandomId
# , encodeGETLISTMessage, encodeLISTMessage, encodeMESSAGEMessage, encodeUPDATEMessage, encodeDISCONNECTMessage, encodeACKMessage, encodeERRORMessage

helloEvent = threading.Event()

def sendHello(sock, server_address, message, username):
	while not helloEvent.is_set():
		print ("sending %s" % message)
		sent = sock.sendto(message.encode("utf-8"), server_address)
		helloEvent.wait(10)

	# TODO ... Clean shutdown code here ...
	# nulove HELLO pri kille
	message = encodeHELLOMessage(getRandomId(), username, "0.0.0.0", 0)
	print ("hello: " + message)
	sent = sock.sendto(message.encode("utf-8"), server_address)

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


def main():
	print ("PEER")

	args = parsePeerArgs()

	peer = Peer(args)
	print ("Peer:" + str(peer))

	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock.bind((peer.chatIp, peer.chatPort))
	server_address = (peer.regIp, peer.regPort)

	signal.signal(signal.SIGINT, signalHandler)

	try:

		helloMessage = encodeHELLOMessage(getRandomId(), peer.username, peer.chatIp, peer.chatPort)
		print ("hello: " + helloMessage)
		helloThread = threading.Thread(target=sendHello, args=(sock, server_address), kwargs={"message": helloMessage, "username": peer.username})
		helloThread.start()

		# TODO add more functionality (recv?)
		while True:
			data, server = sock.recvfrom(4096)
			print ("FINALLY")
			time.sleep(0.5)


	except ServiceException:

		helloEvent.set()
		helloThread.join()
		print ("ServiceException")

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

if __name__ == "__main__":
	main()