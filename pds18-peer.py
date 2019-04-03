#!/usr/bin/python

import socket
import sys
from parsers import parsePeerArgs

print 'PEER'

args = parsePeerArgs()
print 'ARGS: ', str(args)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

server_address = ('localhost', 10000)
message = 'This is the message.  It will be repeated.'

try:

    # Send data
    print >> sys.stderr, 'sending "%s"' % message
    sent = sock.sendto(message, server_address)

    # Receive response
    print >> sys.stderr, 'waiting to receive'
    data, server = sock.recvfrom(4096)
    print >> sys.stderr, 'received "%s"' % data

finally:
    print >> sys.stderr, 'closing socket'
    sock.close()