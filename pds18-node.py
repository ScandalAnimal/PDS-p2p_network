#!/usr/bin/python

import socket
import sys
import signal
from parsers import parseNodeArgs
from util import ServiceException, signalHandler

print ("NODE")

args = parseNodeArgs()

class Node:
	def __init__(self, args):
		self.id = args.id
		self.regIp = args.reg_ipv4
		self.regPort = args.reg_port
	def __str__(self):
		return ("Id: " + str(self.id) + ", regIp: " + self.regIp + ", regPort: " + str(self.regPort))	

node = Node(args)
print ("Node:" + str(node))

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

server_address = (node.regIp, node.regPort)
print ("starting up on %s port %s" % server_address)
sock.bind(server_address)

signal.signal(signal.SIGINT, signalHandler)

try:

	while True:
		print ("\nwaiting to receive message")
		data, address = sock.recvfrom(4096)
		
		print ("received %s bytes from %s" % (len(data.decode("utf-8")), address))
		print (data.decode("utf-8"))
		
		# TODO toto pouzit na ACK
		# if data:
			# sent = sock.sendto(data, address)
			# print ("sent %s bytes back to %s" % (sent, address))


# except ServiceException:

finally:
	print ("closing socket")
	sock.close()	        