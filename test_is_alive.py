from bulk_messenger import init_gmail_driver, is_browser_alive
import traceback
import time

driver = init_gmail_driver()
time.sleep(2)
print("Testing alive...")
try:
    _ = driver.current_url
    print("Alive!")
except Exception as e:
    print("Exception!")
    traceback.print_exc()
