from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium.webdriver.common.actions.pointer_input import PointerInput
from selenium.webdriver.common.actions.action_builder import ActionBuilder

from time import sleep

PERMISSION_PKG = "com.google.android.permissioncontroller"

GALLERY_ACTIVITY = "com.samsung.android.gallery.app.activity.external.GalleryExternalActivity"

def get_my_default_ui_automator2_options(device_udid):
    options = UiAutomator2Options()
    options.platform_name = "Android"
    options.udid = device_udid

    options.app_package = "com.sec.android.app.launcher"
    options.app_activity = "com.sec.android.app.launcher.activities.LauncherActivity"

    options.no_reset = True

    return options

class AndroidAutomator:
    def __init__(self, appium_server_url, options, logger = None):
        self.__driver = webdriver.Remote(appium_server_url, options=options)
        self.__logger = logger

    def __self.__log(self, msg):
        if self.__logger is None: return
        self.__logger.debug(f"[AndroidAutomator] {msg}")

    def set_credentials(self, pin: str):
        self.__pin = pin

    def __wait(self, duration = 10):
        return WebDriverWait(self.__driver, duration)
    
    def __wait_permission_dialog_appear(self, duration):
        self.__wait(duration).until(lambda d: d.current_package == PERMISSION_PKG)

    def __click_on_coordinate(self, x, y):
        finger = PointerInput("touch", "finger")
        click_actions = ActionBuilder(self.__driver, mouse=finger)
        click_actions.pointer_action.move_to_location(x, y)
        click_actions.pointer_action.pointer_down()
        click_actions.pointer_action.pause(0.1)  # Short pause to simulate tap
        click_actions.pointer_action.pointer_up()
        click_actions.perform()

    def __grant_permission(self):
        allow_btn = self.__wait().until(
            EC.presence_of_element_located((AppiumBy.XPATH, "(//android.widget.Button)[1]"))
        )
        allow_btn.click()

    def __open_qris(self):
        qris_iv = self.__wait(15).until(
            EC.presence_of_element_located((AppiumBy.ID, "com.bnc.finance:id/iv_qris"))
        )
        qris_iv.click()

        self.__wait_qris_scan_activity_opened()

        require_permission = False
        try:
            self.__wait_permission_dialog_appear(2)
            require_permission = True
        except:
            pass

        if require_permission:
            self.__grant_permission()
    
    def __print_current_activity(self):
        current_activity = self.__driver.current_activity
        self.__self.__log(f"Current Activity: {current_activity}")

    def __click_gallery(self):
        self.__click_on_coordinate(554, 1309)

    def __click_first_item_in_gallery(self):
        self.__click_on_coordinate(18, 570)

    def __click_pay_button(self):
        pay_btn = self.__wait().until(
            EC.presence_of_element_located((AppiumBy.ID, "com.bnc.finance:id/btn_confirm"))
        )
        pay_btn.click()

    def __fill_pin(self):
        pin_et = self.__wait().until(
            EC.presence_of_element_located((AppiumBy.XPATH, "//android.widget.EditText"))
        )
        pin_et.send_keys(self.__pin)

    def __click_confirm_button(self):
        confirm_btn = self.__wait().until(
            EC.presence_of_element_located((AppiumBy.ID, "com.bnc.finance:id/btn_confirm"))
        )
        confirm_btn.click()

    def __wait_qris_scan_activity_opened(self):
        self.__wait().until(
            lambda d: d.current_activity == "com.bnc.business.qrcode.activity.QrcodeScanActivity"
        )

    def __wait_gallery_opened(self):
        self.__wait().until(
            lambda d: d.current_activity == GALLERY_ACTIVITY
        )

    def __wait_pay_result_activity_opened(self):
        self.__wait().until(
            lambda d: d.current_activity == ".qrcode.activity.PayResultActivity"
        )

    def __wait_QRIS_pay_activity_opened(self):
        self.__wait().until(
            lambda d: d.current_activity == ".qrcode.activity.QrisPayActivity"
        )

    def __wait_main_activity(self, timeout = 60):
        self.__wait(timeout).until(
            lambda d: d.current_activity == "com.byb.main.MainActivity"
        )
   
    def __wait_verify_pin_dialog_appear(self):
        x_path = "//android.widget.TextView[@text='Verifikasi PIN']"
        self.__wait().until(
            EC.presence_of_element_located((AppiumBy.XPATH, x_path))
        )

    def pay_qris_transaction(self):
        # wait current activity is main activity
        self.__wait_main_activity()

        # wait stable
        sleep(1) 

        self.__log("[INFO] Opening QRIS scan activity..")
        self.__open_qris()
        self.__log("[INFO] Done.")

        sleep(1) # wait QRIS activity is stable
        
        self.__log("[INFO] Opening gallery..")
        self.__click_gallery()
        self.__wait_gallery_opened()
        self.__log("[INFO] Done.")
        
        self.__log("[INFO] Picking first item in gallery..")
        self.__click_first_item_in_gallery()
        self.__log("[INFO] Done.")

        sleep(1)
        
        self.__log("[INFO] Waiting QRIS pay activity..")
        self.__wait_QRIS_pay_activity_opened()
        self.__log("[INFO] Done.")

        self.__log("[INFO] Paying..")
        self.__click_pay_button()
        self.__log("[INFO] Waiting PIN dialog..")
        self.__wait_verify_pin_dialog_appear()
        self.__log("[INFO] Filling PIN..")
        self.__fill_pin()
        self.__log("[INFO] Waiting payment result..")
        self.__wait_pay_result_activity_opened()
        self.__log("[INFO] Done.")
        sleep(1)
        self.__click_confirm_button()


    def quit(self):
        self.__driver.quit()

if __name__ == "__main__":
    from dotenv import load_dotenv
    import os

    # Load the .env file
    load_dotenv()

    appium_server_url = os.getenv("APPIUM_SERVER_URL")
    device_udid = os.getenv("DEVICE_UDID")

    neo_pin = os.getenv("NEO_PIN")

    options = get_my_default_ui_automator2_options(device_udid) 
    automator = AndroidAutomator(appium_server_url, options)
    automator.set_credentials(neo_pin)

    # automator.print_current_activity()
    # sleep(3000)

    print("[INFO] Pay 5 QRIS transaction")

    for i in range(5):
        # start pay QRIS
        automator.pay_qris_transaction()

    print("Done!")

    automator.quit()
