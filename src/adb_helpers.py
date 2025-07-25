import subprocess

adb_path = "/Users/haus-dev/Library/Android/sdk/platform-tools/adb"

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