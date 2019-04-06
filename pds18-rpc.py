#!/usr/bin/python

from parsers import parseRpcArgs
# class Rpc:
	# def __init__(self, args):
	# def __str__(self):
		# return ("Id: " + str(self.id) + ", username: " + self.username + 
			# ", chatIp: " + self.chatIp + ", chatPort: " + str(self.chatPort) + 
			# ", regIp: " + self.regIp + ", regPort: " + str(self.regPort))	


def main():
	print ("RPC")

	args = parseRpcArgs()
	print (args)
	# peer = Peer(args)
	# print ("Peer:" + str(peer))

	# sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	# sock.bind((peer.chatIp, peer.chatPort))
	# server_address = (peer.regIp, peer.regPort)

	# signal.signal(signal.SIGINT, signalHandler)

	# rpcFileName = "peer" + str(peer.id)
	# f = open(rpcFileName, "w+")
	# rpcFilePath = os.path.abspath(rpcFileName)
	# f.close()

	# try:

	# 	helloMessage = encodeHELLOMessage(getRandomId(), peer.username, peer.chatIp, peer.chatPort)
	# 	print ("hello: " + helloMessage)
	# 	helloThread = threading.Thread(target=sendHello, args=(sock, server_address), kwargs={"message": helloMessage, "username": peer.username})
	# 	helloThread.start()

	# 	readRpcThread = threading.Thread(target=readRpc, kwargs={"file": rpcFileName})
	# 	readRpcThread.start()

	# 	# TODO add more functionality (recv?)
	# 	while True:
	# 		data, server = sock.recvfrom(4096)
	# 		print ("FINALLY")
	# 		time.sleep(0.5)


	# except ServiceException:
	# 	print ("ServiceException")
	# 	helloEvent.set()
	# 	helloThread.join()
	# 	readRpcEvent.set()
	# 	readRpcThread.join()

	# finally:
	# 	print ("closing socket")
	# 	os.remove(rpcFilePath)
	# 	sock.close()	

if __name__ == "__main__":
	main()