import subprocess
from .utils import get_resource_path
import platform

if platform.system() == "Windows": 
    adb_path = get_resource_path("adb\\windows\\adb.exe")
else:
    adb_path = get_resource_path("adb/macos/adb")

def get_connected_devices():
    try:
        result = subprocess.run(
            [adb_path, "devices"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode != 0:
            print("ADB Error:\n", result.stderr)
            return []

        lines = result.stdout.strip().splitlines()
        # Skip the first line: "List of devices attached"
        device_lines = lines[1:]
        devices = []

        for line in device_lines:
            parts = line.strip().split()
            if len(parts) == 2 and parts[1] == "device":
                devices.append(parts[0])

        return devices

    except FileNotFoundError:
        print("ADB not found. Make sure it's installed and in your PATH.")
        return []
    
def run_adb_command(command):
    try:
        result = subprocess.run(
            [adb_path] + command.split(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode == 0:
            print("Output:\n", result.stdout)
        else:
            print("Error:\n", result.stderr)
    except FileNotFoundError:
        print("ADB not found. Make sure it's installed and in your PATH.")