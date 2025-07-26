from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium.webdriver.common.actions.pointer_input import PointerInput
from selenium.webdriver.common.actions.action_builder import ActionBuilder

from time import sleep

GALLERY_APP_PKG = "com.sec.android.gallery3d"
PERMISSION_PKG = "com.google.android.permissioncontroller"

def get_my_default_ui_automator2_options(device_udid):
    options = UiAutomator2Options()
    options.platform_name = "Android"
    options.udid = device_udid

    options.app_package = "com.bnc.finance"
    options.app_activity = "com.bnc.finance/com.byb.main.MainActivity"

    return options

class AndroidAutomator:
    def __init__(self, appium_server_url, options):
        self.__driver = webdriver.Remote(appium_server_url, options=options)

    def set_credentials(self, phone: str, password: str, pin: str):
        self.__phone = phone
        self.__password = password
        self.__pin = pin

    def __wait(self, duration = 10):
        return WebDriverWait(self.__driver, duration)
    
    def __wait_permission_dialog_appear(self):
        self.__wait().until(lambda d: d.current_package == PERMISSION_PKG)

    def __wait_gallery_opened(self):
        self.__wait().until(lambda d: d.current_package == GALLERY_APP_PKG)

    def __wait_popup_dialog_appear(self):
        self.__wait().until(
            EC.presence_of_element_located((AppiumBy.ID, "com.bnc.finance:id/shadow"))
        )

    def __wait_security_verification_appear(self):
        x_path = "//android.widget.TextView[@text='Verifikasi Keamanan']"
        self.__wait().until(
            EC.presence_of_element_located((AppiumBy.XPATH, x_path))
        )

    def __wait_security_verification_done(self):
        x_path = "//android.widget.TextView[@text='Verifikasi Keamanan']"
        self.__wait(60).until_not(
            EC.presence_of_element_located((AppiumBy.XPATH, x_path))
        )

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

    def setup(self):
        # grant permissions
        need_permission = False
        try:
            self.__wait_permission_dialog_appear()
            need_permission = True
        except:
            # permission dialog does not appear
            pass

        if need_permission:
            self.__grant_permission()

        # close initial popup 
        close_iv = self.__wait().until(
            EC.presence_of_element_located((AppiumBy.ID, "com.bnc.finance:id/iv_close"))
        )
        close_iv.click()  
 
        self.__wait_popup_dialog_appear()
        ok_btn = self.__wait().until(
            EC.presence_of_element_located((AppiumBy.ID, "com.bnc.finance:id/btn"))
        )
        ok_btn.click()

    def login(self):
        # go to profile
        profile_menu_btn = self.__wait().until(
            EC.presence_of_element_located((AppiumBy.ID, "com.bnc.finance:id/radio_personal"))
        )
        profile_menu_btn.click()

        # login
        login_btn = self.__wait().until(
            EC.presence_of_element_located((AppiumBy.ID, "com.bnc.finance:id/btn_register_login"))
        )
        login_btn.click()

        phone_et = self.__wait().until(
            EC.presence_of_element_located((AppiumBy.ID, "com.bnc.finance:id/phone_edit"))
        )
        phone_et.send_keys(self.__phone)

        continue_btn = self.__driver.find_element(AppiumBy.ID, "com.bnc.finance:id/continue_btn")
        continue_btn.click()

        confirm_btn = self.__wait().until(
            EC.presence_of_element_located((AppiumBy.ID, "com.bnc.finance:id/btn_confirm"))
        )
        confirm_btn.click()

        need_verification = False
        try:
            self.__wait_security_verification_appear()
            need_verification = True
        except:
            # security verification does not apper, just go ahead
            pass
 
        if need_verification:
            print("Please solve security verification")
            self.__wait_security_verification_done()

        print("Security verification solved!")

        password_et = self.__wait().until(
            EC.presence_of_element_located((AppiumBy.XPATH, "(//android.widget.EditText)[1]"))
        )
        password_et.send_keys(self.__password)

        btn = self.__driver.find_element(AppiumBy.XPATH, "(//android.widget.Button)[1]")
        btn.click()


    def open_qris(self):
        qris_iv = self.__wait(15).until(
            EC.presence_of_element_located((AppiumBy.ID, "com.bnc.finance:id/iv_qris"))
        )
        qris_iv.click()

        require_permission = False
        try:
            self.__wait_permission_dialog_appear()
            require_permission = True
        except:
            pass

        if require_permission:
            self.__grant_permission()

    def scan_qris(self):
        # [554,1309][618,1373] // gallery iv bound
        self.__click_on_coordinate(554, 1309)

        need_permission = False
        try:
            self.__wait_permission_dialog_appear() 
            need_permission = True  
        except:
            pass

        if need_permission:
            self.__grant_permission()

        print("[INFO] waiting gallery opened..")
        self.__wait_gallery_opened()
        print("[INFO] gallery has opened")

        gallery_image_x_path = "(//android.widget.FrameLayout[@resource-id='com.sec.android.gallery3d:id/deco_view_layout'])[1]"
        gallery_image = self.__wait().until(
            EC.presence_of_element_located((AppiumBy.XPATH, gallery_image_x_path))
        )
        gallery_image.click()

        pay_btn = self.__wait().until(
            EC.presence_of_element_located((AppiumBy.ID, "com.bnc.finance:id/btn_confirm"))
        )
        pay_btn.click()

        pin_et = self.__wait().until(
            EC.presence_of_element_located((AppiumBy.XPATH, "//android.widget.EditText"))
        )
        pin_et.send_keys(self.__pin)
    
    def print_current_activity(self):
        current_activity = self.__driver.current_activity
        print("Current Activity:", current_activity)

    def quit(self):
        self.__driver.quit()

if __name__ == "__main__":
    from dotenv import load_dotenv
    import os

    # Load the .env file
    load_dotenv()

    appium_server_url = os.getenv("APPIUM_SERVER_URL")
    device_udid = os.getenv("DEVICE_UDID")

    neo_phone = os.getenv("NEO_PHONE")
    neo_password = os.getenv("NEO_PASSWORD")
    neo_pin = os.getenv("NEO_PIN")

    options = get_my_default_ui_automator2_options(device_udid) 
    automator = AndroidAutomator(appium_server_url, options)
    automator.set_credentials(neo_phone, neo_password, neo_pin)
    automator.setup()
    automator.login()
    automator.open_qris()
    for i in range(3):
        automator.scan_qris()
        sleep(3)

    automator.quit()
