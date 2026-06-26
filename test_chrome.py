import os
import sys
from selenium import webdriver

def test_chrome():
    options = webdriver.ChromeOptions()
    user_data_dir = os.path.join(os.getcwd(), "test_profile")
    os.makedirs(user_data_dir, exist_ok=True)
    user_data_dir = os.path.abspath(user_data_dir).replace("\\", "/")
    options.add_argument(f"--user-data-dir={user_data_dir}")
    
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option('useAutomationExtension', False)
    
    options.add_argument("--log-level=3")
    options.add_argument("--silent")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-popup-blocking")
    options.page_load_strategy = 'eager'
    
    try:
        driver = webdriver.Chrome(options=options)
        print("Driver started")
        driver.get("https://mail.google.com")
        print("URL loaded:", driver.current_url)
        driver.quit()
        print("SUCCESS")
    except Exception as e:
        print("FAILED:", str(e))

if __name__ == "__main__":
    test_chrome()
