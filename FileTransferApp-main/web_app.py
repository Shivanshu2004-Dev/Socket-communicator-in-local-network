"""Modern web-based chat and file transfer application."""

import os
import socket
import threading
import struct
import secrets
import time
from flask import Flask, render_template, request, jsonify, send_file, session
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
from functools import wraps
from datetime import datetime, timedelta
import json

# Get the absolute path to the templates directory
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))

# Initialize Flask with explicit template folder
app = Flask(__name__, template_folder=template_dir)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['UPLOAD_FOLDER'] = 'upload_temp/'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('received_files/', exist_ok=True)

CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Chat server connection
CHAT_SERVER_HOST = os.environ.get('CHAT_HOST', '127.0.0.1')
CHAT_SERVER_PORT = 9009
FILE_SERVER_PORT = 9010
BUFFER_SIZE = 4096

# Active connections
connected_users = {}  # {username: {'socket': sock, 'sid': socketio_sid, 'connected_at': timestamp}}
chat_lock = threading.Lock()

# File tracking
file_tokens = {}  # {token: (filename, path, expiry)}
TOKEN_TTL = 3600  # 1 hour


def connect_to_chat_server(username):
    """Connect to the chat server with retry logic."""
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)  # 5 second timeout
            print(f'[DEBUG] Connection attempt {attempt + 1}/{max_retries} for {username}')
            sock.connect((CHAT_SERVER_HOST, CHAT_SERVER_PORT))
            print(f'[DEBUG] Connected to chat server {CHAT_SERVER_HOST}:{CHAT_SERVER_PORT}')
            sock.sendall(f'USER {username}\n'.encode('utf-8'))
            print(f'[DEBUG] Sent USER command for {username}')
            return sock
        except socket.timeout:
            print(f'[ERROR] Timeout on attempt {attempt + 1} for {username}')
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
        except Exception as e:
            print(f'[ERROR] Connection error on attempt {attempt + 1} for {username}: {e}')
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
    
    print(f'[ERROR] Failed to connect after {max_retries} attempts')
    return None


def receive_chat_messages(username, sock, socketio_sid):
    """Receive messages from chat server."""
    buffer = b''
    print(f'[DEBUG] Receive thread started for {username}')
    try:
        while True:
            try:
                data = sock.recv(4096)
            except socket.timeout:
                # Timeout is normal, continue
                continue
            except Exception as e:
                print(f'[ERROR] Socket error for {username}: {e}')
                break
                
            if not data:
                print(f'[ERROR] {username} disconnected from server (no data)')
                with chat_lock:
                    if username in connected_users:
                        del connected_users[username]
                with app.app_context():
                    socketio.emit('user_disconnected', {'username': username}, broadcast=True)
                    socketio.emit('connection_error', {'error': 'Lost connection to chat server', 'username': username}, room=socketio_sid)
                break
            
            buffer += data
            while b'\n' in buffer:
                line, buffer = buffer.split(b'\n', 1)
                text = line.decode('utf-8', errors='ignore').strip()
                
                if not text:
                    continue
                
                if text.startswith('CONNECTED '):
                    # Server confirmed connection
                    connected_user = text[10:]
                    print(f'[DEBUG] Server confirmed connection for {connected_user}')
                    with chat_lock:
                        if username in connected_users:
                            connected_users[username]['status'] = 'connected'
                    with app.app_context():
                        socketio.emit('connection_confirmed', {'username': connected_user}, room=socketio_sid)
                        socketio.emit('users_list', {'users': 'User joined'}, broadcast=True)
                        
                elif text.startswith('MSG '):
                    # Broadcast message from chat server to web users
                    msg_text = text[4:]
                    with app.app_context():
                        socketio.emit('chat_message', {
                            'message': msg_text,
                            'type': 'broadcast',
                            'username': username
                        }, broadcast=True)
                        
                elif text.startswith('USERS '):
                    users_list = text[6:]
                    with app.app_context():
                        socketio.emit('users_list', {'users': users_list}, room=socketio_sid)
                        # Also broadcast to all
                        socketio.emit('users_list', {'users': users_list}, broadcast=True)
                        
                elif text.startswith('ERROR '):
                    error_msg = text[6:]
                    print(f'[ERROR] Server error for {username}: {error_msg}')
                    with chat_lock:
                        if username in connected_users:
                            del connected_users[username]
                    with app.app_context():
                        socketio.emit('error_message', {'error': error_msg}, room=socketio_sid)
                        
    except Exception as e:
        print(f'[ERROR] Receive loop error for {username}: {e}')
        import traceback
        traceback.print_exc()
        with chat_lock:
            if username in connected_users:
                del connected_users[username]
        with app.app_context():
            socketio.emit('connection_error', {'error': f'Connection error: {str(e)}', 'username': username}, room=socketio_sid)
    finally:
        try:
            sock.close()
        except:
            pass
        with chat_lock:
            if username in connected_users:
                print(f'[DEBUG] Cleaning up {username} from connected_users')
                del connected_users[username]


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})


@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')
    emit('connect_response', {'data': 'Connected to server'})


@socketio.on('disconnect')
def handle_disconnect():
    print(f'Client disconnected: {request.sid}')
    # Find and disconnect user
    disconnected_user = None
    with chat_lock:
        for username, info in list(connected_users.items()):
            if info['sid'] == request.sid:
                try:
                    info['socket'].close()
                except:
                    pass
                del connected_users[username]
                disconnected_user = username
                break
    
    if disconnected_user:
        # Broadcast updated user list
        broadcast_user_list()


def broadcast_user_list():
    """Broadcast current user list to all clients."""
    with chat_lock:
        # Get all connected users (status doesn't matter)
        users = [u for u in connected_users.keys()]
    
    users_str = ', '.join(users) if users else 'No users'
    
    try:
        socketio.emit('users_list', {'users': users_str}, broadcast=True)
        print(f'[DEBUG] Broadcast user list: {users_str}')
    except Exception as e:
        print(f'[ERROR] Failed to broadcast user list: {e}')


@socketio.on('join_chat')
def handle_join_chat(data):
    """User joins the chat."""
    username = data.get('username', '').strip()
    
    if not username:
        emit('error_message', {'error': 'Username cannot be empty'})
        return
    
    with chat_lock:
        if username in connected_users:
            emit('error_message', {'error': 'Username already taken'})
            return
    
    # Connect to chat server
    chat_sock = connect_to_chat_server(username)
    if not chat_sock:
        emit('error_message', {'error': 'Failed to connect to chat server. Check if server is running on port 9009'})
        return
    
    # Mark as pending initially
    with chat_lock:
        connected_users[username] = {
            'socket': chat_sock,
            'sid': request.sid,
            'connected_at': datetime.now(),
            'status': 'connecting'
        }
    
    # Notify client immediately that they're joining
    emit('join_response', {'username': username, 'status': 'joined'})
    
    # Broadcast updated user list
    broadcast_user_list()
    
    # Start receiving messages in background
    threading.Thread(
        target=receive_chat_messages,
        args=(username, chat_sock, request.sid),
        daemon=True
    ).start()
    
    # Timeout - mark as connected after 3 seconds if no error
    def mark_connected_timeout():
        time.sleep(3)
        with chat_lock:
            if username in connected_users:
                if connected_users[username]['status'] == 'connecting':
                    connected_users[username]['status'] = 'connected'
                    print(f'[DEBUG] Marked {username} as connected (timeout fallback)')
                    with app.app_context():
                        socketio.emit('connection_confirmed', {'username': username}, room=request.sid)
    
    threading.Thread(target=mark_connected_timeout, daemon=True).start()


@socketio.on('send_message')
def handle_send_message(data):
    """Send a chat message."""
    username = data.get('username')
    message = data.get('message', '').strip()
    msg_type = data.get('type', 'broadcast')  # broadcast or private
    target_user = data.get('target_user', '')
    
    if not message:
        return
    
    with chat_lock:
        if username not in connected_users:
            emit('error_message', {'error': 'Not connected to chat'})
            return
        
        chat_sock = connected_users[username]['socket']
    
    try:
        if msg_type == 'private' and target_user:
            cmd = f'PM {target_user} {message}\n'
        else:
            cmd = message + '\n'
        
        chat_sock.sendall(cmd.encode('utf-8'))
        print(f'[DEBUG] Message sent from {username}: {message[:50]}...')
        
        # Show message immediately in web UI
        with app.app_context():
            socketio.emit('chat_message', {
                'message': message,
                'type': 'own',
                'username': username,
                'timestamp': datetime.now().isoformat()
            }, broadcast=True)
    except Exception as e:
        print(f'[ERROR] Failed to send message from {username}: {e}')
        emit('error_message', {'error': f'Failed to send message: {e}'})


@socketio.on('get_users')
def handle_get_users(data):
    """Get list of connected users."""
    username = data.get('username')
    
    with chat_lock:
        if username not in connected_users:
            # Just broadcast current list
            users = list(connected_users.keys())
            users_str = ', '.join(users) if users else 'No users'
            emit('users_list', {'users': users_str})
            return
        
        chat_sock = connected_users[username]['socket']
    
    try:
        # Send LIST command to get updated user list from server
        chat_sock.sendall(b'LIST\n')
    except Exception as e:
        print(f'[ERROR] Failed to send LIST command for {username}: {e}')
        # Still emit current local list as fallback
        with chat_lock:
            users = list(connected_users.keys())
            users_str = ', '.join(users) if users else 'No users'
            emit('users_list', {'users': users_str})


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle file upload."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    username = request.form.get('username', 'anonymous')
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        # Save file to temp location
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        
        # Generate download token
        token = secrets.token_urlsafe(32)
        file_tokens[token] = {
            'filename': file.filename,
            'path': filepath,
            'uploader': username,
            'expiry': datetime.now() + timedelta(seconds=TOKEN_TTL),
            'uploaded_at': datetime.now().isoformat()
        }
        
        download_url = f'/api/download/{token}'
        
        # Notify all users about the new file (if they're connected to chat)
        notification = f'[FILE SHARED] {username} shared: {file.filename} - Download: {download_url}'
        for uname, info in connected_users.items():
            try:
                info['socket'].sendall(f'{notification}\n'.encode('utf-8'))
            except:
                pass
        
        return jsonify({
            'success': True,
            'filename': file.filename,
            'token': token,
            'download_url': download_url,
            'uploader': username,
            'uploaded_at': datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/download/<token>', methods=['GET'])
def download_file(token):
    """Download a file using token."""
    if token not in file_tokens:
        return jsonify({'error': 'Invalid or expired token'}), 404
    
    file_info = file_tokens[token]
    
    # Check expiry
    if datetime.now() > file_info['expiry']:
        del file_tokens[token]
        return jsonify({'error': 'Token expired'}), 401
    
    filepath = file_info['path']
    filename = file_info['filename']
    
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    
    try:
        return send_file(filepath, as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/files', methods=['GET'])
def get_files_list():
    """Get list of available files."""
    try:
        files = []
        for token, info in list(file_tokens.items()):
            if datetime.now() > info['expiry']:
                del file_tokens[token]
                continue
            
            files.append({
                'token': token,
                'filename': info['filename'],
                'uploader': info['uploader'],
                'uploaded_at': info['uploaded_at'],
                'expires_at': info['expiry'].isoformat(),
                'download_url': f'/api/download/{token}'
            })
        
        return jsonify({'files': files}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500




def health_check_background():
    """Periodically check user connection health and broadcast updates."""
    print('[DEBUG] Starting health check background thread')
    while True:
        try:
            time.sleep(5)  # Check every 5 seconds
            
            # Broadcast current user list
            broadcast_user_list()
            
            # Check for dead connections
            with chat_lock:
                dead_users = []
                for username, info in list(connected_users.items()):
                    try:
                        sock = info['socket']
                        # Try to peek data without removing it
                        sock.setblocking(False)
                        try:
                            sock.recv(0)  # Non-blocking peek
                        except:
                            pass
                        sock.setblocking(True)
                    except:
                        dead_users.append(username)
                
                # Remove dead connections
                for username in dead_users:
                    print(f'[DEBUG] Removing dead connection for {username}')
                    if username in connected_users:
                        del connected_users[username]
            
        except Exception as e:
            print(f'[ERROR] Health check error: {e}')


# Start background health check thread
health_thread = threading.Thread(target=health_check_background, daemon=True)
health_thread.start()


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
