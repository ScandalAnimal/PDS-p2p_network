#!/usr/bin/python

import os
from parsers import parseRpcArgs

def main():
	print ("RPC")

	args = parseRpcArgs()
	print (args)

	fileName = ""
	if args.peer and args.id:
		fileName = "peer" + str(args.id)
	if args.node and args.id:
		fileName = "node" + str(args.id)	

	try:
		if os.path.isfile(fileName):
			with open(fileName, "a") as f:
				command = args.command
				if args.command == "message":
					command = command + " " + args.fromName + " " + args.toName + " " + args.message
				if args.command == "reconnect" or args.command == "connect":
					command = command + " " + args.reg_ipv4 + " " + args.reg_port	
				command = command + "\n"	
				f.write(command)
		else:
			raise IOError		
	except IOError as e:
		print ('Target peer/node is not running')	

if __name__ == "__main__":
	main()