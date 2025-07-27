import sys
import os
import platform
from dotenv import load_dotenv
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QGroupBox, QMessageBox, QFileDialog
)
from PyQt5.QtCore import pyqtSignal, QThread, QObject, QEventLoop, QTimer, Qt

from time import sleep

from src.android.android_automator_v2 import AndroidAutomator, get_my_default_ui_automator2_options
from src.browser.browser_automator_v2 import BrowserAutomator, get_my_default_chrome_options, get_user_ids
from src.adb_helpers import get_connected_devices

from src.utils import get_resource_path


def show_error_dialog(message):
    app = QApplication.instance()
    if app:
        QMessageBox.critical(None, "Error", message)


class BrowserWorker(QThread):
    log_message = pyqtSignal(str)
    qris_downloaded = pyqtSignal()
    finished = pyqtSignal()

    def __init__(self, base_url, username, password, user_ids):
        super().__init__()
        self.base_url = base_url
        self.username = username
        self.password = password
        self.user_ids = user_ids
        self._stop = False
        self.browser_automator = None

        self._wait_loop = None
        self._continue = False

    def stop(self):
        self._stop = True
        if self._wait_loop and self._wait_loop.isRunning():
            self._continue = True
            self._wait_loop.quit()

    def run(self):
        try:
            self.log_message.emit("[Browser] Setting up browser...")
            self.browser_automator = BrowserAutomator(self.base_url, get_my_default_chrome_options())
            self.browser_automator.set_credentials(self.username, self.password)
            self.browser_automator.set_user_ids(self.user_ids)

            self.browser_automator.setup()

            self.log_message.emit("[Browser] Generating QRIS...")
            self.browser_automator.generate_QRIS()

            count = 0
            total = len(self.user_ids)
            while not self._stop and count < total:
                self.log_message.emit(f"[Browser] Download QRIS #{count}")
                self.browser_automator.loop_downloads()
                self.log_message.emit(f"[Browser] QRIS #{count} Downloaded")
                self.qris_downloaded.emit()
                count += 1

                # Wait for signal from Android worker before continuing
                self._wait_for_continue()

        except Exception as e:
            self.log_message.emit(f"[Browser] Error: {e}")
            show_error_dialog(f"Browser error: {e}")
        finally:
            try:
                self.log_message.emit("[Browser] Quitting browser")
                if self.browser_automator:
                    self.browser_automator.quit()
            except Exception:
                pass
            self.finished.emit()

    def _wait_for_continue(self):
        self._continue = False
        loop = QEventLoop()
        self._wait_loop = loop

        timer = QTimer()
        timer.setInterval(100)
        timer.timeout.connect(lambda: loop.quit() if self._continue or self._stop else None)
        timer.start()

        loop.exec_()

        timer.stop()
        self._wait_loop = None

    def continue_download(self):
        self._continue = True
        if self._wait_loop and self._wait_loop.isRunning():
            self._wait_loop.quit()


class AndroidWorker(QThread):
    log_message = pyqtSignal(str)
    continue_signal = pyqtSignal()
    finished = pyqtSignal()

    def __init__(self, appium_server_url, neo_pin, device_udid):
        super().__init__()
        self.appium_server_url = appium_server_url
        self.neo_pin = neo_pin
        self.device_udid = device_udid
        self._stop = False
        self.android_automator = None

        self._wait_loop = None
        self._qris_ready = False

    def stop(self):
        self._stop = True
        if self._wait_loop and self._wait_loop.isRunning():
            self._qris_ready = True
            self._wait_loop.quit()

    def run(self):
        try:
            options = get_my_default_ui_automator2_options(self.device_udid)
            self.android_automator = AndroidAutomator(self.appium_server_url, options)
            self.android_automator.set_credentials(self.neo_pin)

            while not self._stop:
                self.log_message.emit("[Android] Waiting for QRIS to be downloaded...")
                self._wait_for_qris_download()

                if self._stop:
                    break

                self.log_message.emit("[Android] Pay QRIS transaction")
                self.android_automator.pay_qris_transaction()
                self.log_message.emit("[Android] Pay QRIS transaction done")

                self.continue_signal.emit()

        except Exception as e:
            self.log_message.emit(f"[Android] Error: {e}")
            show_error_dialog(f"Android error: {e}")
        finally:
            try:
                self.log_message.emit("[Android] Quitting android")
                if self.android_automator:
                    self.android_automator.quit()
            except Exception:
                pass
            self.finished.emit()

    def _wait_for_qris_download(self):
        self._qris_ready = False
        loop = QEventLoop()
        self._wait_loop = loop

        timer = QTimer()
        timer.setInterval(100)
        timer.timeout.connect(lambda: loop.quit() if self._qris_ready or self._stop else None)
        timer.start()

        loop.exec_()

        timer.stop()
        self._wait_loop = None

    def qris_downloaded(self):
        self._qris_ready = True
        if self._wait_loop and self._wait_loop.isRunning():
            self._wait_loop.quit()


class PaymentWorker(QObject):
    """
    Manages the two QThreads and connects their signals.
    """
    log_message = pyqtSignal(str)
    payment_finished = pyqtSignal()

    def __init__(self, pin, device_udid, user_id_file_path):
        super().__init__()
        self.pin = pin
        self.device_udid = device_udid
        self.user_id_file_path = user_id_file_path

        dotenv_path = get_resource_path(".env")
        load_dotenv(dotenv_path)

        self.appium_server_url = os.getenv("APPIUM_SERVER_URL")
        self.base_url = os.getenv("WEB_BASE_URL")
        self.username = os.getenv("WEB_CRED_USERNAME")
        self.password = os.getenv("WEB_CRED_PASSWORD")

        self.user_ids = get_user_ids(self.user_id_file_path)

        self.browser_worker = BrowserWorker(self.base_url, self.username, self.password, self.user_ids)
        self.android_worker = AndroidWorker(self.appium_server_url, self.pin, self.device_udid)

        self._setup_connections()

    def _setup_connections(self):
        self.browser_worker.log_message.connect(self.log_message)
        self.android_worker.log_message.connect(self.log_message)

        self.browser_worker.finished.connect(self._on_finished)
        self.android_worker.finished.connect(self._on_finished)

        self.browser_worker.qris_downloaded.connect(self.android_worker.qris_downloaded)

        self.android_worker.continue_signal.connect(self.browser_worker.continue_download)

        self._finished_count = 0

    def start(self):
        self.log_message.emit("[PaymentWorker] Starting workers...")
        self.browser_worker.start()
        self.android_worker.start()

    def stop(self):
        self.log_message.emit("[PaymentWorker] Stopping workers...")
        self.browser_worker.stop()
        self.android_worker.stop()

        # Quit and wait for clean shutdown
        self.browser_worker.quit()
        self.android_worker.quit()

        self.browser_worker.wait()
        self.android_worker.wait()

    def _on_finished(self):
        self._finished_count += 1
        if self._finished_count >= 2:
            self.log_message.emit("[PaymentWorker] Both workers finished.")
            self.payment_finished.emit()


class QRISAutoPayApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QRIS Auto Pay")
        self.setGeometry(100, 100, 400, 400)
        self.setFixedSize(600, 500)

        self.worker = None
        self.user_id_file_path = ""
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()

        device_group = QGroupBox("Device")
        device_layout = QVBoxLayout()
        self.detect_button = QPushButton("Detect Android Device", self)
        self.detect_button.clicked.connect(self.detect_android_device)
        device_layout.addWidget(self.detect_button)

        self.device_label = QLabel("Device not detected", self)
        device_layout.addWidget(self.device_label)
        device_group.setLayout(device_layout)
        main_layout.addWidget(device_group)

        config_group = QGroupBox("Config")
        config_layout = QVBoxLayout()
        self.pin_label = QLabel("Enter PIN:", self)
        config_layout.addWidget(self.pin_label)

        self.pin_input = QLineEdit(self)
        self.pin_input.setEchoMode(QLineEdit.Password)
        config_layout.addWidget(self.pin_input)

        self.file_label = QLabel("User ID File: Not selected", self)
        config_layout.addWidget(self.file_label)

        self.browse_button = QPushButton("Browse User ID File", self)
        self.browse_button.clicked.connect(self.browse_user_id_file)
        config_layout.addWidget(self.browse_button)

        config_group.setLayout(config_layout)
        main_layout.addWidget(config_group)

        button_group = QGroupBox("Action")
        button_layout = QVBoxLayout()
        self.toggle_button = QPushButton("Start", self)
        self.toggle_button.clicked.connect(self.toggle_action)
        button_layout.addWidget(self.toggle_button)

        self.status_browser_label = QLabel("Browser Status: Waiting", self)
        self.status_android_label = QLabel("Android Status: Waiting", self)
        button_layout.addWidget(self.status_browser_label)
        button_layout.addWidget(self.status_android_label)

        button_group.setLayout(button_layout)
        main_layout.addWidget(button_group)

        self.setLayout(main_layout)
        self.detect_android_device()

    def browse_user_id_file(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Select User ID File", "", "Text Files (*.txt);;All Files (*)", options=options)
        if file_path:
            self.user_id_file_path = file_path
            self.file_label.setText(f"User ID File: {os.path.basename(file_path)}")

    def toggle_action(self):
        pin = self.pin_input.text()
        if not pin:
            self.status_browser_label.setText("Browser Status: Please enter a PIN.")
            return

        if not self.user_id_file_path:
            self.status_browser_label.setText("Browser Status: Please select a User ID file.")
            return

        if self.toggle_button.text() == "Start":
            self.pin_input.setDisabled(True)
            self.toggle_button.setText("Stop")
            self.device_label.setText(f"Detected: {self.get_device_udid()}")

            self.worker = PaymentWorker(pin, self.get_device_udid(), self.user_id_file_path)
            self.worker.payment_finished.connect(self.on_payment_finished)
            self.worker.log_message.connect(self.update_status_label)
            self.worker.start()
        else:
            self.stop_worker()

    def stop_worker(self):
        if self.worker:
            self.worker.stop()

    def on_payment_finished(self):
        self.pin_input.setDisabled(False)
        self.toggle_button.setText("Start")
        self.worker = None

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
        lower_msg = message.lower()
        if "[browser]" in lower_msg:
            self.status_browser_label.setText(f"Browser Status: {message}")
        elif "[android]" in lower_msg:
            self.status_android_label.setText(f"Android Status: {message}")
        else:
            self.status_browser_label.setText(f"Browser Status: {message}")
            self.status_android_label.setText(f"Android Status: {message}")


def main():
    app = QApplication(sys.argv)
    window = QRISAutoPayApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
