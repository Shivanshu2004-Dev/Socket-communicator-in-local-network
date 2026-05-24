# Multi-User Chat & File Transfer (TCP)

Simple Python-based multi-user chat server and client with basic file upload support.

Files
- `server.py` - TCP server that accepts chat connections (port 9009) and file uploads (port 9010).
- `client.py` - Interactive client for chatting and uploading files.

Features
- Broadcast chat messages to all connected users
- Private messages: `/pm <user> <message>`
- List users: `/list`
- Upload file to server: `/sendfile <path>` (server saves under `received_files/` and notifies users)

Run
1. Start server:

```bash
python3 server.py
```

2. Start client (either in same machine or remote, set `CHAT_HOST` env var to server host):

```bash
python3 client.py <username>
# or
CHAT_HOST=192.168.1.10 python3 client.py alice
```

Commands
- Type any line and press Enter to send a broadcast message.
- `/pm bob hello` - send private message to user `bob`.
- `/list` - request list of connected users.
- `/sendfile /path/to/file` - upload file to the server's file port.
- `/quit` - disconnect and exit client.

Download uploaded files
- The server starts a minimal HTTP server on port 8020 and serves files placed in `received_files/`.
- When a file is uploaded the server broadcasts a download URL, e.g.:
python3 client.py <username>
# or set server host:
CHAT_HOST=192.168.x.x python3 client.py alice- The server protects downloads with short-lived tokens. When a file is uploaded the server broadcasts a tokenized download URL, e.g.:
	`http://<server-host>:8020/download/<token>`

Token details
- Tokens are generated per-upload and valid for 1 hour by default.
- Anyone with a valid tokenized URL can download the file until it expires.

Example: download with curl

```bash
# copy the tokenized URL from chat server messages
curl -O "http://localhost:8020/download/XXXXXXXX_YYYY"
```

Security notes
- Tokens are unguessable but are not tied to a specific client IP or user. If you need stricter access control, I can:
	- bind tokens to uploader or requestor IP
	- make tokens one-time-use
	- add authentication + authorization checks before serving
	- enable HTTPS for encrypted downloads

Notes and limitations
- Authentication and encryption are not implemented. Use only on trusted networks.
- File transfers are saved to `received_files/` on server.
- This is a minimal educational example; adapt and harden before production use.
