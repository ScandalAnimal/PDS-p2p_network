#!/usr/bin/python

import argparse

def parsePeerArgs():
	parser = argparse.ArgumentParser()
	parser.add_argument('--id', type=int, required=True, help='Unique peer identificator', metavar='id')
	parser.add_argument('--username', type=str, required=True, help='Peer username', metavar='username')
	parser.add_argument('--chat-ipv4', type=str, required=True, help='Address where peer is listening', metavar='chat-ipv4')
	parser.add_argument('--chat-port', type=int, required=True, help='Port where peer is listening', metavar='chat-port')
	parser.add_argument('--reg-ipv4', type=str, required=True, help='Address of reg node', metavar='reg-ipv4')
	parser.add_argument('--reg-port', type=int, required=True, help='Port of reg node', metavar='reg-port')
	return parser.parse_args()

def parseNodeArgs():
	parser = argparse.ArgumentParser()
	parser.add_argument('--id', type=int, required=True, help='Unique node identificator', metavar='id')
	parser.add_argument('--reg-ipv4', type=str, required=True, help='Address of reg node', metavar='reg-ipv4')
	parser.add_argument('--reg-port', type=int, required=True, help='Port of reg node', metavar='reg-port')
	return parser.parse_args()

