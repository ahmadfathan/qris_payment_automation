from browser.browser_automator import BrowserAutomator, get_my_default_chrome_options
from android.android_automator_v2 import AndroidAutomator, get_my_default_ui_automator2_options
from utils import get_user_ids, get_newest_file_by_name
from multiprocessing import Process, Event, set_start_method
from time import sleep
from adb_helpers import run_adb_command

from dotenv import load_dotenv
import os

# Load the .env file
load_dotenv()

base_url = os.getenv("WEB_BASE_URL")
username = os.getenv("WEB_CRED_USERNAME")
password = os.getenv("WEB_CRED_PASSWORD")

appium_server_url = os.getenv("APPIUM_SERVER_URL")
device_udid = os.getenv("DEVICE_UDID")

neo_pin = os.getenv("NEO_PIN")

set_start_method("fork")

def download_QRIS(browser_automator, continue_event, qris_downloaded_event):
    browser_automator.loop_downloads(continue_event, qris_downloaded_event)

def pay_QRIS_transaction(android_automator: AndroidAutomator, qris_downloaded_event, continue_event):
    while True:
        print("[SCAN QRIS] waiting QRIS downloaded..")
        qris_downloaded_event.wait()
        print("[SCAN QRIS] QRIS downloaded")
        
        # push the file to android device
        dest_folder = "/storage/emulated/0/Pictures"
        filename = get_newest_file_by_name("screenshots")

        adb_push_file_to_android(f"screenshots/{filename}", dest_folder)

        sleep(1)
        adb_trigger_scan_file(f"{dest_folder}/{filename}")
        
        sleep(0.5)

        # scan QRIS
        android_automator.pay_qris_transaction()

        # emit continue event
        continue_event.set()
        
        # clear events
        qris_downloaded_event.clear()

def adb_push_file_to_android(filename, dest):
    run_adb_command(f"push {filename} {dest}")

def adb_trigger_scan_file(path):
    run_adb_command(f"shell am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file://{path}")

def count_down(n):
    for i in range(n, 0, -1):
        print(f"\rStarting in {i} ", end='', flush=True)
        sleep(1)
    print()

if __name__ == "__main__":

    USER_IDS_PATH = "user_ids_5.txt"
    user_ids = get_user_ids(USER_IDS_PATH)

    continue_event = Event()
    qris_downloaded_event = Event()

    # setup browser automator
    print("[INFO] Setting up browser..")
    chrome_options = get_my_default_chrome_options()
    browser_automator = BrowserAutomator(base_url, chrome_options)
    browser_automator.set_credentials(username, password)
    browser_automator.setup()
    print("[INFO] Browser is ready.")

    # setup android automator
    print("[INFO] Setting up android..")
    ui_automator2_options = get_my_default_ui_automator2_options(device_udid) 
    android_automator = AndroidAutomator(appium_server_url, ui_automator2_options)
    android_automator.set_credentials(neo_pin)
    print("[INFO] Android is ready.")

    sleep(1)

    print("[INFO] Generating QRIS..")
    browser_automator.set_user_ids(user_ids)
    browser_automator.generate_QRIS()
    print("[INFO] Done.")

    p_download_QRIS = Process(target=download_QRIS, args=(browser_automator, continue_event, qris_downloaded_event,))
    p_scan_QRIS = Process(target=pay_QRIS_transaction, args=(android_automator, qris_downloaded_event, continue_event,))
    
    p_download_QRIS.start()
    p_scan_QRIS.start()

    count_down(3)

    continue_event.set()

    p_download_QRIS.join()
    p_scan_QRIS.terminate()
    
    # finished
    android_automator.quit()
    browser_automator.quit()
