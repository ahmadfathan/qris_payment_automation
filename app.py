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

        options = get_my_default_ui_automator2_options(device_udid)
        automator = AndroidAutomator(appium_server_url, options)
        automator.set_credentials(neo_pin)

        print("[INFO] Pay 5 QRIS transaction")
        for i in range(5):
            automator.pay_qris_transaction()

        print("Done!")
        automator.quit()

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
        """Simulate getting the UDID of the Android device."""
        return "1234567890abcdef"  # Simulated. Replace with actual detection if needed.


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QRISAutoPayApp()
    window.show()
    sys.exit(app.exec_())
