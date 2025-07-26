import sys
import os
from dotenv import load_dotenv
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QGroupBox
)
from PyQt5.QtCore import pyqtSignal, QThread

from src.android.android_automator_v2 import AndroidAutomator, get_my_default_ui_automator2_options
from src.browser.browser_automator_v2 import BrowserAutomator, get_my_default_chrome_options, get_user_ids

from multiprocessing import Process, Event, set_start_method
from time import sleep
from src.adb_helpers import run_adb_command, get_connected_devices
import platform

if platform.system() == "Windows": 
    set_start_method("spawn")
else:
    set_start_method("fork")

def adb_push_file_to_android(filename, dest):
    run_adb_command(f"push {filename} {dest}")

def adb_trigger_scan_file(path):
    run_adb_command(f"shell am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file://{path}")

def download_QRIS(browser_automator, continue_event, qris_downloaded_event):
    browser_automator.loop_downloads(continue_event, qris_downloaded_event)

def scan_QRIS(android_automator, qris_downloaded_event, continue_event):
    while True:
        qris_downloaded_event.wait()
        android_automator.pay_qris_transaction()
        continue_event.set()
        qris_downloaded_event.clear()

# Worker thread class
class PaymentWorker(QThread):
    payment_finished = pyqtSignal()
    log_message = pyqtSignal(str)  # NEW: Signal to send status updates

    def __init__(self, pin, device_udid):
        super().__init__()
        self.pin = pin
        self.device_udid = device_udid

    def run(self):
        self.log_message.emit("Loading configuration...")
        load_dotenv()

        appium_server_url = os.getenv("APPIUM_SERVER_URL")
        neo_pin = os.getenv("NEO_PIN")

        base_url = os.getenv("WEB_BASE_URL")
        username = os.getenv("WEB_CRED_USERNAME")
        password = os.getenv("WEB_CRED_PASSWORD")

        user_ids = get_user_ids("user_ids_5.txt")

        continue_event = Event()
        qris_downloaded_event = Event()

        browser_automator = BrowserAutomator(base_url, get_my_default_chrome_options())
        browser_automator.set_credentials(username, password)
        browser_automator.set_user_ids(user_ids)

        self.log_message.emit("Setting up browser...")
        browser_automator.setup()

        self.log_message.emit("Generating QRIS...")
        browser_automator.generate_QRIS()
        self.log_message.emit("QRIS generated successfully.")

        options = get_my_default_ui_automator2_options(self.device_udid)
        android_automator = AndroidAutomator(appium_server_url, options)
        android_automator.set_credentials(neo_pin)

        self.log_message.emit("Launching QRIS processes...")

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

        self.log_message.emit("Payment automation complete.")
        self.payment_finished.emit()

# Main app class
class QRISAutoPayApp(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("QRIS Auto Pay")
        self.setGeometry(100, 100, 400, 350)
        self.setFixedSize(400, 350)

        self.worker = None
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()

        # Device group
        device_group = QGroupBox("Device")
        device_layout = QVBoxLayout()
        self.detect_button = QPushButton("Detect Android Device", self)
        self.detect_button.clicked.connect(self.detect_android_device)
        device_layout.addWidget(self.detect_button)

        self.device_label = QLabel("Device not detected", self)
        device_layout.addWidget(self.device_label)
        device_group.setLayout(device_layout)
        main_layout.addWidget(device_group)

        # Config group
        config_group = QGroupBox("Config")
        config_layout = QVBoxLayout()
        self.pin_label = QLabel("Enter PIN:", self)
        config_layout.addWidget(self.pin_label)

        self.pin_input = QLineEdit(self)
        self.pin_input.setEchoMode(QLineEdit.Password)
        config_layout.addWidget(self.pin_input)
        config_group.setLayout(config_layout)
        main_layout.addWidget(config_group)

        # Action group
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

            self.worker = PaymentWorker(pin, self.get_device_udid())
            self.worker.payment_finished.connect(self.stop_payment_process)
            self.worker.log_message.connect(self.update_status_label)
            self.worker.start()
        else:
            self.stop_payment_process()

    def stop_payment_process(self):
        self.pin_input.setDisabled(False)
        self.toggle_button.setText("Start")
        self.status_label.setText("Status: Process stopped.")

    def detect_android_device(self):
        device_udid = self.get_device_udid()
        if device_udid:
            self.device_label.setText(f"Detected: {device_udid}")
            self.toggle_button.setEnabled(True)
        else:
            self.device_label.setText("Device not detected")
            self.toggle_button.setEnabled(False)

    def get_device_udid(self):
        devices = get_connected_devices()
        return devices[0] if devices else ""

    def update_status_label(self, message):
        self.status_label.setText(f"Status: {message}")

# Run the app
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QRISAutoPayApp()
    window.show()
    sys.exit(app.exec_())
