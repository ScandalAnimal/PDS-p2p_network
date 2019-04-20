all:
	ln -s pds18-peer.py pds18-peer
	ln -s pds18-node.py pds18-node
	ln -s pds18-rpc.py pds18-rpc

clean:
	rm pds18-peer
	rm pds18-node
	rm pds18-rpc	