import sys
import os
from dotenv import load_dotenv
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QGroupBox
)
from PyQt5.QtCore import pyqtSignal, QThread

# Import your automator from your project
from src.android.android_automator_v2 import AndroidAutomator, get_my_default_ui_automator2_options
from src.browser.browser_automator_v2 import BrowserAutomator, get_my_default_chrome_options, get_user_ids

from multiprocessing import Process, Event, set_start_method

from time import sleep
from src.adb_helpers import run_adb_command, get_connected_devices

set_start_method("fork")

def adb_push_file_to_android(filename, dest):
    run_adb_command(f"push {filename} {dest}")

def adb_trigger_scan_file(path):
    run_adb_command(f"shell am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file://{path}")

def download_QRIS(browser_automator, continue_event, qris_downloaded_event):
    browser_automator.loop_downloads(continue_event, qris_downloaded_event)

def scan_QRIS(android_automator, qris_downloaded_event, continue_event):
    while True:
        print("[SCAN QRIS] waiting QRIS downloaded..")
        qris_downloaded_event.wait()
        print("[SCAN QRIS] QRIS downloaded")
        
        # push the file to android device
        # dest_folder = "/storage/emulated/0/Pictures"
        # filename = get_newest_file_by_name("screenshots")

        # adb_push_file_to_android(f"screenshots/{filename}", dest_folder)

        # sleep(1)
        # adb_trigger_scan_file(f"{dest_folder}/{filename}")
        
        # sleep(0.5)

        # scan QRIS
        android_automator.pay_qris_transaction()

        print("Done!")

        # emit continue event
        continue_event.set()
        
        # clear events
        qris_downloaded_event.clear()

class PaymentWorker(QThread):
    payment_finished = pyqtSignal()

    def __init__(self, pin):
        super().__init__()
        self.pin = pin

    def run(self):
        print(f"Payment process started with PIN: {self.pin}")
        load_dotenv()

        appium_server_url = os.getenv("APPIUM_SERVER_URL")
        device_udid = os.getenv("DEVICE_UDID")
        neo_pin = os.getenv("NEO_PIN")

        base_url = os.getenv("WEB_BASE_URL")
        username = os.getenv("WEB_CRED_USERNAME")
        password = os.getenv("WEB_CRED_PASSWORD")

        USER_IDS_PATH = "user_ids_5.txt"
        user_ids = get_user_ids(USER_IDS_PATH)

        continue_event = Event()
        qris_downloaded_event = Event()

        browser_automator = BrowserAutomator(base_url, get_my_default_chrome_options())
        browser_automator.set_credentials(username, password)
        browser_automator.set_user_ids(user_ids)

        print("[BROWSER][INFO] Setting up..")
        browser_automator.setup()
        print("[BROWSER][INFO] Done.")

        print("[INFO] Generating QRIS..")
        browser_automator.generate_QRIS()
        print("[INFO] Done.")

        options = get_my_default_ui_automator2_options(device_udid)
        android_automator = AndroidAutomator(appium_server_url, options)
        android_automator.set_credentials(neo_pin)

        p_download_QRIS = Process(target=download_QRIS, args=(browser_automator, continue_event, qris_downloaded_event,))
        p_scan_QRIS = Process(target=scan_QRIS, args=(android_automator, qris_downloaded_event, continue_event,))
        
        p_download_QRIS.start()
        p_scan_QRIS.start()

        sleep(3)

        continue_event.set()

        p_download_QRIS.join()
        p_scan_QRIS.terminate()

        browser_automator.quit()
        android_automator.quit()

        # Emit signal after finishing
        self.payment_finished.emit()


class QRISAutoPayApp(QWidget):
    def __init__(self):
        super().__init__()

        # Set up the window
        self.setWindowTitle("QRIS Auto Pay")
        self.setGeometry(100, 100, 400, 350)
        self.setFixedSize(400, 350)

        self.worker = None  # Placeholder for the background worker

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()

        # 1. Device group
        device_group = QGroupBox("Device")
        device_layout = QVBoxLayout()
        self.detect_button = QPushButton("Detect Android Device", self)
        self.detect_button.clicked.connect(self.detect_android_device)
        device_layout.addWidget(self.detect_button)

        self.device_label = QLabel("Device not detected", self)
        device_layout.addWidget(self.device_label)

        device_group.setLayout(device_layout)
        main_layout.addWidget(device_group)

        # 2. Config group
        config_group = QGroupBox("Config")
        config_layout = QVBoxLayout()
        self.pin_label = QLabel("Enter PIN:", self)
        config_layout.addWidget(self.pin_label)

        self.pin_input = QLineEdit(self)
        self.pin_input.setEchoMode(QLineEdit.Password)
        config_layout.addWidget(self.pin_input)

        config_group.setLayout(config_layout)
        main_layout.addWidget(config_group)

        # 3. Action group
        button_group = QGroupBox("Action")
        button_layout = QVBoxLayout()
        self.toggle_button = QPushButton("Start", self)
        self.toggle_button.clicked.connect(self.toggle_action)
        button_layout.addWidget(self.toggle_button)

        self.status_label = QLabel("Status: Waiting for action", self)
        button_layout.addWidget(self.status_label)

        button_group.setLayout(button_layout)
        main_layout.addWidget(button_group)

        self.setLayout(main_layout)

        # Detect device on startup
        self.detect_android_device()

    def toggle_action(self):
        pin = self.pin_input.text()
        if not pin:
            self.status_label.setText("Status: Please enter a PIN.")
            return

        if self.toggle_button.text() == "Start":
            self.pin_input.setDisabled(True)
            self.toggle_button.setText("Stop")
            self.device_label.setText(f"Detected: {self.get_device_udid()}")
            self.status_label.setText(f"Status: Process started with PIN: {pin}")

            # Start payment in a new thread
            self.worker = PaymentWorker(pin)
            self.worker.payment_finished.connect(self.stop_payment_process)
            self.worker.start()
        else:
            self.stop_payment_process()

    def stop_payment_process(self):
        """Stop the payment process and reset UI state."""
        self.pin_input.setDisabled(False)
        self.toggle_button.setText("Start")
        self.status_label.setText("Status: Process stopped.")

    def detect_android_device(self):
        """Simulate device detection."""
        device_udid = self.get_device_udid()
        if device_udid:
            self.device_label.setText(f"Detected: {device_udid}")
            self.toggle_button.setEnabled(True)
        else:
            self.device_label.setText("Device not detected")
            self.toggle_button.setEnabled(False)

    def get_device_udid(self):
        devices = get_connected_devices()
        if len(devices) == 0:
            return ""
        
        return devices[0]

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QRISAutoPayApp()
    window.show()
    sys.exit(app.exec_())
