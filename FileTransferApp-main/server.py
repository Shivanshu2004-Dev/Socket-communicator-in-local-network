("""Multi-user chat & file transfer server.

Features:
- Accept multiple TCP clients
- Broadcast messages
- Private messages using /pm <user> <message>
- List users with /list
- Send files with /sendfile <filename> <size> followed by raw bytes on a separate connection

Protocol (simple text commands):
- On connect, client sends username line: USER <name>\n
- Normal messages are prefixed with MSG <text>\n
- Commands start with / (client-side) and are translated to server actions.

File transfer: client connects to file transfer port and sends metadata then raw bytes.
""")

import socket
import threading
import os
import struct
from typing import Dict, Tuple
import secrets
import time
import mimetypes

HOST = '0.0.0.0'
PORT = 9009
FILE_PORT = 9010
HTTP_PORT = 8020
BUFFER_SIZE = 4096


class ClientInfo:
	def __init__(self, name: str, conn: socket.socket, addr: Tuple[str, int]):
		self.name = name
		self.conn = conn
		self.addr = addr


class ChatServer:
	def __init__(self, host=HOST, port=PORT, file_port=FILE_PORT):
		self.host = host
		self.port = port
		self.file_port = file_port
		self.http_port = HTTP_PORT
		self.clients: Dict[str, ClientInfo] = {}
		self.lock = threading.Lock()
		self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.file_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		# token -> (path, expiry_timestamp)
		self.download_tokens: Dict[str, Tuple[str, float]] = {}
		self.token_ttl = 60 * 60  # seconds; tokens valid for 1 hour

	def start(self):
		self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.server_sock.bind((self.host, self.port))
		self.server_sock.listen(100)
		print(f"Chat server listening on {self.host}:{self.port}")

		self.file_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.file_sock.bind((self.host, self.file_port))
		self.file_sock.listen(20)
		print(f"File server listening on {self.host}:{self.file_port}")

		# Start HTTP server to serve received files
		threading.Thread(target=self._start_http_server, daemon=True).start()
		print(f"HTTP file server will serve on port {self.http_port}")

		threading.Thread(target=self._accept_file_connections, daemon=True).start()

		try:
			while True:
				conn, addr = self.server_sock.accept()
				threading.Thread(target=self._handle_client, args=(conn, addr), daemon=True).start()
		except KeyboardInterrupt:
			print('Shutting down server')
		finally:
			self.server_sock.close()
			self.file_sock.close()

	def _accept_file_connections(self):
		while True:
			conn, addr = self.file_sock.accept()
			threading.Thread(target=self._handle_file_transfer, args=(conn, addr), daemon=True).start()

	def _handle_file_transfer(self, conn: socket.socket, addr):
		# Expect metadata: <sender_name_len(1)> <name> <filename_len(2)> <filename> <filesize(8)> then raw bytes
		try:
			hdr = conn.recv(1)
			if not hdr:
				conn.close()
				return
			name_len = hdr[0]
			name = conn.recv(name_len).decode('utf-8')
			fn_len_b = conn.recv(2)
			fn_len = struct.unpack('!H', fn_len_b)[0]
			filename = conn.recv(fn_len).decode('utf-8')
			size_b = conn.recv(8)
			filesize = struct.unpack('!Q', size_b)[0]

			print(f"Receiving file '{filename}' ({filesize} bytes) from {name} @ {addr}")

			# Save to server files directory with unique user-prefixed filename
			os.makedirs('received_files', exist_ok=True)
			import time
			safe_name = f"{name}_{int(time.time())}_{filename}"
			out_path = os.path.join('received_files', safe_name)
			remaining = filesize
			with open(out_path, 'wb') as f:
				while remaining:
					chunk = conn.recv(min(BUFFER_SIZE, remaining))
					if not chunk:
						break
					f.write(chunk)
					remaining -= len(chunk)

			print(f"Saved file to {out_path}")

			# Notify all clients that a file was received and where to download (HTTP endpoint)
			# URL is constructed assuming server is reachable at self.host (may be 0.0.0.0 locally)
			url_host = 'localhost' if self.host in ('0.0.0.0', '') else self.host
			# generate token and store mapping with expiry
			token = secrets.token_urlsafe(16)
			expiry = time.time() + self.token_ttl
			with self.lock:
				self.download_tokens[token] = (out_path, expiry)

			download_url = f'http://{url_host}:{self.http_port}/download/{token}'
			msg = f"[FILE] {name} uploaded {filename} ({filesize} bytes). Download (tokenized): {download_url}"
			self._broadcast(msg)
		except Exception as e:
			print('File transfer error:', e)
		finally:
			conn.close()

	def _handle_client(self, conn: socket.socket, addr):
		with conn:
			try:
				# Expect first line: USER <name>\n
				data = conn.recv(1024)
				if not data:
					return
				line = data.decode('utf-8').strip()
				if not line.startswith('USER '):
					conn.sendall(b'ERROR Missing USER\n')
					return
				name = line[5:].strip()
				if not name:
					conn.sendall(b'ERROR Empty name\n')
					return

				with self.lock:
					if name in self.clients:
						conn.sendall(b'ERROR NameTaken\n')
						return
					self.clients[name] = ClientInfo(name, conn, addr)

				# Send confirmation to the client
				conn.sendall(f'CONNECTED {name}\n'.encode('utf-8'))
				
				welcome = f"[SYSTEM] {name} joined the chat"
				self._broadcast(welcome)

				# Now continuously read lines (simple protocol): MSG <text>\n or PM <target> <text>\n
				buffer = b''
				while True:
					chunk = conn.recv(1024)
					if not chunk:
						break
					buffer += chunk
					while b'\n' in buffer:
						line, buffer = buffer.split(b'\n', 1)
						text = line.decode('utf-8', errors='ignore')
						if text.startswith('MSG '):
							self._broadcast(f"{name}: {text[4:]}")
						elif text.startswith('PM '):
							try:
								_, target, pm = text.split(' ', 2)
							except ValueError:
								conn.sendall(b'ERROR PM format\n')
								continue
							self._private_message(name, target, pm)
						elif text == 'LIST':
							with self.lock:
								users = ','.join(self.clients.keys())
							conn.sendall(f'USERS {users}\n'.encode('utf-8'))
						else:
							# unknown
							conn.sendall(b'ERROR UnknownCommand\n')
			except ConnectionResetError:
				pass
			finally:
				# cleanup
				with self.lock:
					if name in self.clients:
						del self.clients[name]
				self._broadcast(f"[SYSTEM] {name} left the chat")

	def _broadcast(self, message: str):
		data = f'MSG {message}\n'.encode('utf-8')
		to_remove = []
		with self.lock:
			for uname, info in list(self.clients.items()):
				try:
					info.conn.sendall(data)
				except Exception:
					to_remove.append(uname)
			for r in to_remove:
				del self.clients[r]

	def _private_message(self, sender: str, target: str, message: str):
		with self.lock:
			info = self.clients.get(target)
			sender_info = self.clients.get(sender)
		if info:
			try:
				info.conn.sendall(f'MSG [PM from {sender}] {message}\n'.encode('utf-8'))
				if sender_info:
					sender_info.conn.sendall(f'MSG [PM to {target}] {message}\n'.encode('utf-8'))
			except Exception as e:
				print('PM send error', e)

	def _start_http_server(self):
		# Serve the received_files directory on HTTP_PORT
		try:
			import http.server
			import socketserver
			os.makedirs('received_files', exist_ok=True)

			server_self = self

			class TokenHandler(http.server.BaseHTTPRequestHandler):
				def do_GET(self):
					# expected path: /download/<token>
					parts = self.path.split('/')
					if len(parts) != 3 or parts[1] != 'download':
						self.send_response(404)
						self.end_headers()
						self.wfile.write(b'Not found')
						return
					token = parts[2]
					now = time.time()
					with server_self.lock:
						entry = server_self.download_tokens.get(token)
						if not entry:
							self.send_response(403)
							self.end_headers()
							self.wfile.write(b'Invalid or expired token')
							return
						path, expiry = entry
						if now > expiry:
							# expired
							del server_self.download_tokens[token]
							self.send_response(403)
							self.end_headers()
							self.wfile.write(b'Token expired')
							return
					# Serve file content with appropriate headers
					if not os.path.exists(path):
						self.send_response(404)
						self.end_headers()
						self.wfile.write(b'File not found')
						return
					ctype, _ = mimetypes.guess_type(path)
					if not ctype:
						ctype = 'application/octet-stream'
					try:
						fs = os.path.getsize(path)
						self.send_response(200)
						self.send_header('Content-Type', ctype)
						self.send_header('Content-Length', str(fs))
						# suggest download filename = basename without token prefix
						self.send_header('Content-Disposition', f'attachment; filename="{os.path.basename(path)}"')
						self.end_headers()
						with open(path, 'rb') as f:
							while True:
								chunk = f.read(BUFFER_SIZE)
								if not chunk:
									break
								self.wfile.write(chunk)
					except Exception as e:
						self.send_response(500)
						self.end_headers()
						self.wfile.write(b'Internal server error')

			# Use TCPServer; bind to host and configured http_port
			cwd = os.getcwd()
			os.chdir('received_files')
			try:
				with socketserver.TCPServer((self.host, self.http_port), TokenHandler) as httpd:
					print(f"HTTP server serving received_files at http://{self.host}:{self.http_port}/")
					httpd.serve_forever()
			finally:
				os.chdir(cwd)
		except Exception as e:
			print('HTTP server error:', e)


if __name__ == '__main__':
	server = ChatServer()
	server.start()

