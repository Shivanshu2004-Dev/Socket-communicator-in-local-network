"""Simple interactive chat client with file upload support."""

import socket
import threading
import struct
import os
import sys

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 9009
FILE_PORT = 9010
BUFFER_SIZE = 4096


def recv_loop(sock: socket.socket):
	buffer = b''
	try:
		while True:
			data = sock.recv(4096)
			if not data:
				print('\nDisconnected from server')
				os._exit(0)
			buffer += data
			while b'\n' in buffer:
				line, buffer = buffer.split(b'\n', 1)
				text = line.decode('utf-8', errors='ignore')
				if text.startswith('MSG '):
					print(text[4:])
				elif text.startswith('USERS '):
					print('[USERS] ' + text[6:])
				elif text.startswith('ERROR '):
					print('[ERROR] ' + text[6:])
				else:
					print(text)
	except Exception as e:
		print('Receive loop error:', e)
		os._exit(1)


def send_file(username: str, filepath: str, server_host: str, file_port: int):
	if not os.path.exists(filepath):
		print('File not found:', filepath)
		return
	filesize = os.path.getsize(filepath)
	filename = os.path.basename(filepath)

	try:
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.connect((server_host, file_port))

		name_b = username.encode('utf-8')
		fn_b = filename.encode('utf-8')
		hdr = struct.pack('!B', len(name_b)) + name_b
		hdr += struct.pack('!H', len(fn_b)) + fn_b
		hdr += struct.pack('!Q', filesize)
		s.sendall(hdr)

		with open(filepath, 'rb') as f:
			while True:
				chunk = f.read(BUFFER_SIZE)
				if not chunk:
					break
				s.sendall(chunk)

		print('File sent:', filename)
	except Exception as e:
		print('File send error:', e)
	finally:
		try:
			s.close()
		except Exception:
			pass


def interactive(username: str, server_host=SERVER_HOST, server_port=SERVER_PORT, file_port=FILE_PORT):
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.connect((server_host, server_port))
	sock.sendall(f'USER {username}\n'.encode('utf-8'))

	threading.Thread(target=recv_loop, args=(sock,), daemon=True).start()

	print('Commands:')
	print('/pm <user> <message>   - private message')
	print('/list                  - list users')
	print('/sendfile <path>       - upload file to server')
	print('/quit                  - exit')

	try:
		while True:
			line = input()
			if not line:
				continue
			if line.startswith('/pm '):
				try:
					_, target, msg = line.split(' ', 2)
				except ValueError:
					print('Usage: /pm <user> <message>')
					continue
				sock.sendall(f'PM {target} {msg}\n'.encode('utf-8'))
			elif line == '/list':
				sock.sendall(b'LIST\n')
			elif line.startswith('/sendfile '):
				_, path = line.split(' ', 1)
				send_file(username, path.strip(), server_host, file_port)
			elif line == '/quit':
				print('Exiting')
				sock.close()
				return
			else:
				sock.sendall(f'MSG {line}\n'.encode('utf-8'))
	except (KeyboardInterrupt, EOFError):
		sock.close()


if __name__ == '__main__':
	if len(sys.argv) >= 2:
		username = sys.argv[1]
	else:
		username = input('Choose a username: ').strip()
	host = os.environ.get('CHAT_HOST', SERVER_HOST)
	port = int(os.environ.get('CHAT_PORT', SERVER_PORT))
	fport = int(os.environ.get('CHAT_FILE_PORT', FILE_PORT))
	interactive(username, host, port, fport)

