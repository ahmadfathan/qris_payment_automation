from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium.webdriver.chrome.options import Options

from time import sleep
from datetime import datetime

from multiprocessing import Event

def get_user_ids(filename):
    ids = []
    with open(filename, "r") as f:
        lines = f.readlines()
        for line in lines:
            ids.append(line.strip())
    return ids

def get_my_default_chrome_options():
    # Create a dictionary for Chrome preferences
    chrome_prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "profile.password_manager_leak_detection": False  # Disables "change password" prompts
    }

    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_experimental_option("prefs", chrome_prefs)

    # chrome_options.add_argument("--headless")  # Runs Chrome in headless mode
    # chrome_options.add_argument("--no-sandbox")
    # chrome_options.add_argument("--disable-dev-shm-usage")

    return chrome_options

class BrowserAutomator:
    def __init__(self, base_url: str, chrome_options: Options, logger = None):
        self.__base_url = base_url

        # Optional: Set the path to your ChromeDriver if it's not in your PATH
        # self.__service = Service('/path/to/chromedriver')

        self.__driver = webdriver.Chrome(options=chrome_options)
        self.__driver.set_window_size(1280, 1000)

        self.__logger = logger

    def __log(self, msg):
        if self.__logger is None: return
        self.__logger.debug(f"[BrowserAutomator] {msg}")

    def __wait(self, timeout = 15):
        return WebDriverWait(self.__driver, timeout)

    def set_credentials(self, username: str, password: str):
        self.__username = username
        self.__password = password

    def setup(self):
        # Open a URL
        self.__driver.get(self.__base_url)
        self.__login(self.__username, self.__password)

    def __login(self, username, password):
        username_field = self.__wait().until(
            EC.presence_of_element_located((By.XPATH, "/html/body/div/form/div[1]/input"))
        )
        password_field = self.__driver.find_element(By.XPATH, "/html/body/div/form/div[2]/input")
        login_button = self.__driver.find_element(By.XPATH, "/html/body/div/form/button")

        username_field.send_keys(username)
        password_field.send_keys(password)
        login_button.click()

    def set_user_ids(self, user_ids: list):
        self.__user_ids = user_ids

    def __js_click_element(self, element):
        self.__driver.execute_script("arguments[0].click();", element)

    def generate_QRIS(self):
        self.__log("[INFO] Navigating to topup page..")

        topup_nav_x_path = "//*[@id='navbarNav']/ul/li[4]/a"
        topup_nav = self.__wait().until(
            EC.presence_of_element_located((By.XPATH, topup_nav_x_path))
        )
        #topup_nav.click()
        self.__js_click_element(topup_nav)
 
        self.__wait_page_loaded()

        self.__log("[INFO] Done.")

        serialized_user_ids = "\n".join( self.__user_ids)

        x_path = "//*[@id='user_ids']"
        user_ids_field = self.__wait().until(
            EC.presence_of_element_located((By.XPATH, x_path))
        )

        user_ids_field.send_keys(serialized_user_ids)

        x_path = "/html/body/div/form/div[2]/input"
        submit_button = self.__wait().until(
            EC.presence_of_element_located((By.XPATH, x_path))
        )

        submit_button.click()
        #self.__js_click_element(submit_button)

        # x_path = "/html/body/div/form/div[2]/input"
        # submit_button = self.__driver.find_element(By.XPATH, x_path)
        # submit_button.click()

    def __generate_filename(self, user_id):
        # Get current date
        current_datetime = datetime.now()

        # Format to YYYYMMDD
        formatted_datetime = current_datetime.strftime("%Y%m%d%H%M%S")

        return f"screenshots/QPA_{formatted_datetime}_{user_id}.png" 

    def __wait_page_loaded(self):
        self.__wait().until(
            lambda d: d.execute_script('return document.readyState') == 'complete'
        )

    def __download_QRIS(self, filename):
        original_window = self.__driver.current_window_handle

        self.__log("[INFO] Getting payment URL..")
        try:
            qr_link = self.__wait().until(
                EC.presence_of_element_located((By.XPATH, "//*[@id='iframeContainer']/a"))
            )
            payment_url = qr_link.get_attribute("href")
        except:
            try:
                iframe = self.__wait().until(
                    EC.presence_of_element_located((By.XPATH, "//*[@id='iframeContainer']/iframe"))
                )
                payment_url = iframe.get_attribute("src")
            except:
                return False

        self.__log(f"[INFO] URL: {payment_url}")
        self.__log("[INFO] Done.")

        self.__driver.execute_script(f"window.open('{payment_url}', '_blank');")
        
        sleep(1)  # Wait for tab to open

        # Switch to the new tab (usually index 1)
        self.__driver.switch_to.window(self.__driver.window_handles[1])

        self.__wait_page_loaded()

        sleep(2)         

        # Take a screenshot of the new tab
        self.__driver.save_screenshot(filename)
        self.__driver.close()

        self.__driver.switch_to.window(original_window)

        return True

    def __next_QRIS(self):
        next_button = self.__driver.find_element(By.XPATH, "//*[@id='paginationControls']/button[2]")
        self.__js_click_element(next_button)
        #next_button.click()

    def loop_downloads(self, continue_event = None, qris_downloaded_event = None):
        self.__log("[DOWNLOAD QRIS] Loop downloads started.")
        count = 0
        retry_count = 0
        while True:
            if continue_event is not None: 
                self.__log("[DOWNLOAD QRIS] waiting for continue signal..")
                continue_event.wait()
                self.__log("[DOWNLOAD QRIS] got the signal, continuing..")
                # unset it
                continue_event.clear()

            if count > 0:
                self.__next_QRIS()

            filename = self.__generate_filename(self.__user_ids[count])

            success = self.__download_QRIS(filename)

            if success:
                retry_count = 0
                count = count + 1
                
                if qris_downloaded_event is not None: 
                    qris_downloaded_event.set()
            else:
                if retry_count < 3:
                    self.__driver.refresh()
                else:
                    count = count + 1

            if count >= len(self.__user_ids):
                break

    def quit(self):
        self.__driver.quit()

if __name__ == "__main__":
    from dotenv import load_dotenv
    import os

    # Load the .env file
    load_dotenv()

    base_url = os.getenv("WEB_BASE_URL")
    username = os.getenv("WEB_CRED_USERNAME")
    password = os.getenv("WEB_CRED_PASSWORD")

    automator = BrowserAutomator(base_url, get_my_default_chrome_options())
    automator.set_credentials(username, password)

    print("[INFO] Setting up..")
    automator.setup()
    print("[INFO] Done.")

    user_ids = get_user_ids("user_ids_5.txt")
    automator.set_user_ids(user_ids)

    print("[INFO] Generating QRIS..")
    automator.generate_QRIS()
    print("[INFO] Done.")

    automator.loop_downloads()

    automator.quit()