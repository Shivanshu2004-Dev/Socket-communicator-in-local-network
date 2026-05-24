# Web UI Setup & Usage Guide

## Installation

### Prerequisites
- Python 3.7+
- pip (Python package manager)

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- Flask (web framework)
- Flask-CORS (enable cross-origin requests)
- Flask-SocketIO (real-time WebSocket communication)
- And related dependencies

## Running the Application

### Step 1: Start the Chat Server

In a terminal, run the original chat server:

```bash
python3 server.py
```

You should see:
```
Chat server listening on 0.0.0.0:9009
File server listening on 0.0.0.0:9010
HTTP file server will serve on port 8020
```

### Step 2: Start the Web Application

In another terminal, run the Flask web app:

```bash
python3 web_app.py
```

You should see:
```
 * Running on http://0.0.0.0:5000
```

### Step 3: Open in Browser

Navigate to: **http://localhost:5000**

## Features

### 👤 User Authentication
- Enter a unique username to join the chat
- See your online status in the sidebar
- View all connected users in real-time

### 💬 Real-time Chat
- Send public messages to all users
- Messages appear instantly with timestamps
- See when users join and leave
- Clean, modern message interface

### 📁 File Sharing
- **Upload Files**: Click "📎 Upload File" button
- **Share**: Files are automatically shared with all users
- **Download**: Click on any file in the "Shared Files" list to download
- **Security**: Download links expire after 1 hour
- **Support**: Any file type and size (up to 500MB)

### 👥 User Management
- See online users in the sidebar
- Real-time user status updates
- Automatic cleanup on disconnect

## UI Layout

### Left Sidebar
- **Header**: Shows your username and online status
- **Online Users**: List of all connected users (green dot = online)
- **Shared Files**: List of files shared by all users
- **Disconnect Button**: Leave the chat

### Main Chat Area
- **Messages**: View all chat messages with timestamps
- **Input Field**: Type your messages
- **Send Button**: Send your message
- **File Upload**: Share files with others

## Connection Settings

### Custom Server Host

If connecting to a remote server, set the environment variable before running web_app.py:

```bash
# Linux/Mac
export CHAT_HOST=192.168.x.x
python3 web_app.py

# Windows (PowerShell)
$env:CHAT_HOST='192.168.x.x'
python3 web_app.py

# Windows (CMD)
set CHAT_HOST=192.168.x.x
python3 web_app.py
```

## File Structure

```
FileTransferApp/
├── server.py              # Original chat/file server
├── client.py              # Original CLI client
├── web_app.py             # Flask web application
├── requirements.txt       # Python dependencies
├── templates/
│   └── index.html         # Web UI (HTML/CSS/JS)
├── upload_temp/           # Temporary upload storage
├── received_files/        # Server-side file storage
└── README.md              # Original documentation
```

## Security Notes

### For Development
- Currently handles file sharing via temporary storage
- Tokens expire after 1 hour
- No authentication encryption

### For Production Deployment
Deploy with gunicorn + nginx:

```bash
pip install gunicorn
gunicorn --worker-class eventlet -w 1 web_app:app
```

Then configure nginx as reverse proxy with HTTPS.

## Troubleshooting

### Can't connect to chat server
- Ensure `server.py` is running on port 9009
- Check firewall settings
- Verify `CHAT_HOST` environment variable is correct

### File uploads not working
- Check disk space in `upload_temp/` and `received_files/`
- Verify file size is under 500MB
- Check folder permissions

### WebSocket connection issues
- Ensure browser supports WebSockets
- Check if any proxy/firewall is blocking WebSocket connections
- Check browser console for errors (F12 -> Console tab)

### Users not appearing in list
- Refresh the page (but you'll disconnect)
- Ensure all users are connected to same server
- Check server logs for connection errors

## Tips & Best Practices

1. **Username**: Use alphanumeric characters (underscores OK)
2. **Files**: System shows file upload progress
3. **Messages**: Use Enter to send (Shift+Enter for new line)
4. **Mobile**: UI is responsive and works on tablets/phones

## API Endpoints (for advanced users)

### WebSocket Events
- `join_chat` - Connect user to chat
- `send_message` - Send public/private messages
- `get_users` - Request user list

### HTTP REST API
- `GET /` - Web UI
- `GET /api/health` - Health check
- `POST /api/upload` - Upload file
- `GET /api/download/<token>` - Download file
- `GET /api/files` - List all files

## Support

For issues or questions:
1. Check error messages in browser console (F12)
2. Check server terminal output
3. Review the troubleshooting section above
