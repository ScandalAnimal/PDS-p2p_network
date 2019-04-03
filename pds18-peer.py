#!/usr/bin/python

import socket
import sys
from parsers import parsePeerArgs

print ('PEER')

args = parsePeerArgs()

class Peer:
	def __init__(self, args):
		self.id = args.id
		self.username = args.username
		self.chatIp = args.chat_ipv4
		self.chatPort = args.chat_port
		self.regIp = args.reg_ipv4
		self.regPort = args.reg_port
	def __str__(self):
		return ('Id: ' + str(self.id) + ', username: ' + self.username + 
			', chatIp: ' + self.chatIp + ', chatPort: ' + str(self.chatPort) + 
			', regIp: ' + self.regIp + ', regPort: ' + str(self.regPort))	

peer = Peer(args)
print ('Peer:' + str(peer))


sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

server_address = (peer.regIp, peer.regPort)
message = "This is the message.  It will be repeated."

try:

    # Send data
    print ('sending "%s"' % message)
    sent = sock.sendto(message.encode('utf-8'), server_address)

    # Receive response
    print ('waiting to receive')
    data, server = sock.recvfrom(4096)
    print ('received "%s"' % data.decode('utf-8'))

finally:
    print ('closing socket')
    sock.close()