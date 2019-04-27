#!/usr/bin/python3

import argparse
from util import validateIp

def peerUsage(name=None):                                                            
	return '''pds18-peer.py	[-h] --id <id> --username <string> --chat-ipv4 <ip> --chat-port <int> --reg-ipv4 <ip> --reg-port <int> '''

def parsePeerArgs():
	parser = argparse.ArgumentParser(usage=peerUsage(),allow_abbrev=False)
	parser.add_argument("--id", type=str, required=True, help="Unique peer identificator", metavar="id")
	parser.add_argument("--username", type=str, required=True, help="Peer username", metavar="username")
	parser.add_argument("--chat-ipv4", type=str, required=True, help="Address where peer is listening", metavar="chat-ipv4")
	parser.add_argument("--chat-port", type=int, required=True, help="Port where peer is listening", metavar="chat-port")
	parser.add_argument("--reg-ipv4", type=str, required=True, help="Address of reg node", metavar="reg-ipv4")
	parser.add_argument("--reg-port", type=int, required=True, help="Port of reg node", metavar="reg-port")
	args = parser.parse_args()
	if (not validateIp(args.chat_ipv4)) or (not validateIp(args.reg_ipv4)):
		parser.error("Invalid parameters")	
	return args

def nodeUsage(name=None):                                                            
	return '''pds18-node.py	[-h] --id <id> --reg-ipv4 <ip> --reg-port <int> '''

def parseNodeArgs():
	parser = argparse.ArgumentParser(usage=nodeUsage(),allow_abbrev=False)
	parser.add_argument("--id", type=str, required=True, help="Unique node identificator", metavar="id")
	parser.add_argument("--reg-ipv4", type=str, required=True, help="Address of reg node", metavar="reg-ipv4")
	parser.add_argument("--reg-port", type=int, required=True, help="Port of reg node", metavar="reg-port")
	args = parser.parse_args()
	if not validateIp(args.reg_ipv4):
		parser.error("Invalid parameters")	
	return args	

def rpcUsage(name=None):                                                            
	return '''pds18-rpc.py
	[-h] --id <id>
	(--peer --command message --from <name1> --to <name2> --message <text> |
	--peer --command getlist |
	--peer --command peers |
	--peer --command reconnect --reg-ipv4 <ip> --reg-port <int> |
	--node --command database |
	--node --command neighbors |
	--node --command connect --reg-ipv4 <ip> --reg-port <int> |
	--node --command disconnect |
	--node --command sync)
	
	note: if you want to send message with more than 1 word, surround text with double qoutes
	'''

def parseRpcArgs():
	parser = argparse.ArgumentParser(usage=rpcUsage(),allow_abbrev=False)
	parser.add_argument("--id", type=str, required=True, help="Unique node/peer identificator", metavar="id")
	pngroup = parser.add_mutually_exclusive_group(required=True)
	pngroup.add_argument('--peer', help="Target is peer", action='store_true', dest='peer')
	pngroup.add_argument('--node', help="Target is node", action='store_true', dest='node')
	parser.add_argument("--command", required=True, help="Command", choices=['message','getlist','peers','reconnect','database','neighbors','connect','disconnect','sync'], metavar="command")
	parser.add_argument("--from", help="Message from", type=str, dest="fromName")
	parser.add_argument("--to", help="Message to", type=str, dest="toName")
	parser.add_argument("--message", help="Message string", type=str, metavar="message")
	parser.add_argument("--reg-ipv4", help="Registration ip address", type=str, metavar="reg-ipv4")
	parser.add_argument("--reg-port", help="Registration port", type=str, metavar="reg-port")
	args = parser.parse_args()

	if args.peer and (args.command != 'message' and args.command != 'getlist' and args.command != 'peers' and args.command != 'reconnect'):
		parser.error("Invalid parameters")

	if args.node and (args.command != 'database' and args.command != 'neighbors' and args.command != 'connect' and args.command != 'disconnect' and args.command != 'sync'):
		parser.error("Invalid parameters")

	if args.command == 'message' and (args.fromName is None or args.toName is None or args.message is None):
		parser.error("Invalid parameters")
	
	if (args.command == 'getlist' or args.command == 'peers' or args.command == 'database' or args.command == 'neighbors' or args.command == 'disconnect' or args.command == 'sync') and (args.fromName or args.toName or args.message or args.reg_ipv4 or args.reg_port):
		parser.error("Invalid parameters")

	if (args.command == 'reconnect' or args.command == 'connect') and (args.reg_ipv4 is None or args.reg_port is None):
		parser.error("Invalid parameters")	

	if args.reg_ipv4 != None:
		if not validateIp(args.reg_ipv4):
			parser.error("Invalid parameters")	

	return args

def isCommand(commandName, commandString):

	if commandName == "getlist":
		return commandString == "getlist"
	elif commandName == "peers":
		return commandString == "peers"
	elif commandName == "message":
		args = commandString.split()
		return args[0] == "message"
	elif commandName == "reconnect":
		args = commandString.split()
		return len(args) == 3 and args[0] == "reconnect"
	elif commandName == "database":
		return commandString == "database"
	elif commandName == "connect":
		args = commandString.split()
		return len(args) == 3 and args[0] == "connect"
	elif commandName == "neighbors":
		return commandString == "neighbors"	
	elif commandName == "sync":
		return commandString == "sync"
	elif commandName == "disconnect":
		return commandString == "disconnect"				

	return False		





