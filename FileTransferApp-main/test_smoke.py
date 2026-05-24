"""Smoke test: start server and simulate two clients and a file upload."""
import threading
import time
import socket
import os
import tempfile

from server import ChatServer

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 9009
FILE_PORT = 9010


def start_server():
    srv = ChatServer(host=SERVER_HOST, port=SERVER_PORT, file_port=FILE_PORT)
    threading.Thread(target=srv.start, daemon=True).start()
    return srv


def client_send_and_receive(name, send_msgs=None, do_list=False):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((SERVER_HOST, SERVER_PORT))
    s.sendall(f'USER {name}\n'.encode('utf-8'))
    time.sleep(0.1)
    if send_msgs:
        for m in send_msgs:
            s.sendall(f'MSG {m}\n'.encode('utf-8'))
            time.sleep(0.1)
    if do_list:
        s.sendall(b'LIST\n')
        data = s.recv(1024)
        print(name, 'LIST ->', data.decode('utf-8').strip())
    s.close()


def upload_file(username, content=b'hello world'):
    # create temp file
    fd, path = tempfile.mkstemp()
    os.write(fd, content)
    os.close(fd)

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((SERVER_HOST, FILE_PORT))
    name_b = username.encode('utf-8')
    fn_b = os.path.basename(path).encode('utf-8')
    hdr = bytes([len(name_b)]) + name_b
    hdr += len(fn_b).to_bytes(2, 'big') + fn_b
    hdr += len(content).to_bytes(8, 'big')
    s.sendall(hdr)
    with open(path, 'rb') as f:
        s.sendall(f.read())
    s.close()
    os.remove(path)


if __name__ == '__main__':
    start_server()
    time.sleep(0.2)
    t1 = threading.Thread(target=client_send_and_receive, args=('Alice', ['Hello everyone'], False))
    t2 = threading.Thread(target=client_send_and_receive, args=('Bob', ['Hi Alice'], True))
    t1.start(); t2.start()
    t1.join(); t2.join()
    upload_file('Alice', b'testfilecontent')
    print('Smoke test completed - check received_files directory for uploaded file')
