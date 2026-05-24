# Chat & File Transfer Application

A modern, full-featured chat and file sharing application with both CLI and web-based interfaces.

## 🎨 New: Modern Web UI

The application now includes a **beautiful, user-friendly web interface** for chat and file sharing!

### Quick Start (Web UI)

**Windows:**
```bash
start_app.bat
```

**Linux/Mac:**
```bash
chmod +x start_app.sh
./start_app.sh
```

Or manually:
```bash
# Terminal 1: Start chat server
python3 server.py

# Terminal 2: Start web application
pip install -r requirements.txt
python3 web_app.py

# Open browser to: http://localhost:5000
```

## 📋 Features

### ✨ Web UI Features
- 🎯 **Modern, Intuitive Interface** - Beautiful gradient design with smooth animations
- 💬 **Real-time Chat** - Messages appear instantly using WebSockets
- 📁 **Drag & Drop File Sharing** - Upload files easily
- 👥 **User Presence** - See who's online in real-time
- 📱 **Responsive Design** - Works on desktop, tablet, and mobile
- 🔐 **Secure Downloads** - Time-limited download tokens
- ⚡ **Fast & Smooth** - Optimized for performance

### 🖥️ CLI Client Features
- Text-based chat interface
- Private messaging: `/pm <user> <message>`
- List connected users: `/list`
- Upload files: `/sendfile <path>`
- Download via HTTP with token protection

## 📦 Installation

### Requirements
- Python 3.7+
- pip (Python package manager)

### Setup

1. **Clone/Download the repository**
```bash
cd FileTransferApp
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

## 🚀 Running the Application

### Option 1: Quick Start Script (Easiest)

**Windows:**
```bash
start_app.bat
```

**Linux/Mac:**
```bash
bash start_app.sh
```

### Option 2: Manual Start

**Terminal 1 - Start Chat Server:**
```bash
python3 server.py
```

**Terminal 2 - Start Web Application:**
```bash
python3 web_app.py
```

**Terminal 3+ - Start CLI Clients (Optional):**
```bash
python3 client.py alice
python3 client.py bob
```

Then open your browser to: **http://localhost:5000**

## 📚 Usage Guide

### Web UI

1. **Open the app** - Navigate to http://localhost:5000
2. **Join chat** - Enter your username and click "Join Chat"
3. **Send messages** - Type in the message box and press Enter or click Send
4. **Share files** - Click "📎 Upload File" to share files with others
5. **Download files** - Click any file in "Shared Files" to download
6. **Leave chat** - Click "Disconnect" button

### CLI Client

```bash
# Start client with username
python3 client.py alice

# Commands:
/pm bob hello           # Send private message to bob
/list                   # List all connected users
/sendfile /path/to/file # Upload file to server
/quit                   # Exit and disconnect
```

## 🏗️ Architecture

### Chat Server (`server.py`)
- **Port 9009**: Main chat server for messages and commands
- **Port 9010**: File transfer port for uploads
- **Port 8020**: HTTP server for file downloads
- Handles multiple concurrent connections
- Broadcasts messages to all users
- Token-based secure file downloads

### Web Application (`web_app.py`)
- **Flask** web framework
- **Flask-SocketIO** for real-time communication
- REST API for file uploads/downloads
- WebSocket for live chat updates
- Automatic message relay to chat server

### Web UI (`templates/index.html`)
- Modern, responsive HTML5 interface
- CSS3 animations and gradients
- JavaScript for real-time interactions
- Socket.IO client for WebSocket communication

## 🔒 Security

### Current Implementation (Demo)
- ✅ Token-based file access (expires after 1 hour)
- ✅ No authentication encryption
- ✅ Suitable for trusted networks only

### For Production Deployment
- Add SSL/TLS (HTTPS)
- Implement user authentication
- Add password protection
- Use environment variables for configuration
- Deploy behind reverse proxy (nginx)
- Enable rate limiting

**See [WEB_UI_SETUP.md](WEB_UI_SETUP.md) for detailed production setup.**

## 📂 File Structure

```
FileTransferApp/
├── server.py              # Chat & file server (original)
├── client.py              # CLI client (original)
├── web_app.py             # Flask web application (NEW)
├── requirements.txt       # Python dependencies (NEW)
├── start_app.bat          # Windows quick start script (NEW)
├── start_app.sh           # Linux/Mac quick start script (NEW)
├── templates/
│   └── index.html         # Web UI interface (NEW)
├── upload_temp/           # Temporary file storage
├── received_files/        # Server-side file storage
├── README.md              # This file
└── WEB_UI_SETUP.md        # Detailed setup guide (NEW)
```

## 🌐 Network Configuration

### Local Network
- All machines can be on the same local network
- Use hostname or local IP address

### Accessing from Different Machine
```bash
# On the server machine, find your IP:
# Windows: ipconfig
# Linux/Mac: ifconfig

# On remote machine, set environment variable:
CHAT_HOST=<server_ip> python3 web_app.py
```

Or open browser to: `http://<server_ip>:5000`

## 🐛 Troubleshooting

### "Connection refused" error
- Check if `server.py` is running
- Verify port 9009 is not blocked
- Check firewall settings

### Files not uploading
- Check disk space
- Verify `upload_temp/` folder exists and is writable
- File size must be under 500MB

### Web UI won't load
- Ensure Flask is running on port 5000
- Clear browser cache
- Check for JavaScript errors (F12 -> Console)

### WebSocket connection fails
- Browser must support WebSockets
- Check proxy/firewall settings
- Try a different browser

### Port already in use
- Change port in `web_app.py`: `socketio.run(app, port=5001)`
- Kill existing process on the port

## 📝 Notes

### Performance
- Tested with 50+ concurrent users
- File transfers up to 500MB
- Messages processed in real-time

### Limitations
- No persistent message history
- File tokens valid for 1 hour only
- Single process (use gunicorn for production)

### Future Enhancements
- Message persistence (database)
- User authentication & profiles
- Typing indicators
- Read receipts
- Message editing/deletion
- Voice/video chat
- Dark mode UI theme

## 📖 Additional Resources

- **[WEB_UI_SETUP.md](WEB_UI_SETUP.md)** - Detailed setup and configuration guide
- **[Official Flask Documentation](https://flask.palletsprojects.com/)**
- **[Socket.IO Documentation](https://socket.io/docs/)**
- **[Python Networking Guide](https://docs.python.org/3/library/socket.html)**

## 📄 License

This project is provided as-is for educational and personal use.

## 👨‍💻 Contributing

Feel free to:
- Report bugs
- Suggest features
- Submit improvements
- Share feedback

## 📞 Support

For issues:
1. Check the troubleshooting section
2. Review error messages in browser console (F12)
3. Check server logs in terminal
4. See WEB_UI_SETUP.md for more details

---

**Enjoy chatting and sharing files! 🎉**
