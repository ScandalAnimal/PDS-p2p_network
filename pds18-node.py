#!/usr/bin/python

import socket
import sys
from parsers import parseNodeArgs

print 'NODE'

args = parseNodeArgs()

class Node:
	def __init__(self, args):
		self.id = args.id
		self.regIp = args.reg_ipv4
		self.regPort = args.reg_port
	def __str__(self):
		return ('Id: ' + str(self.id) + ', regIp: ' + self.regIp + ', regPort: ' + str(self.regPort))	

node = Node(args)
print 'Node:', str(node)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

server_address = ('localhost', 10000)
print >> sys.stderr, 'starting up on %s port %s' % server_address
sock.bind(server_address)


while True:
    print >> sys.stderr, '\nwaiting to receive message'
    data, address = sock.recvfrom(4096)
    
    print >> sys.stderr, 'received %s bytes from %s' % (len(data), address)
    print >> sys.stderr, data
    
    if data:
        sent = sock.sendto(data, address)
        print >> sys.stderr, 'sent %s bytes back to %s' % (sent, address)