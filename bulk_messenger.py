import actions
import importlib

import pandas as pd
import time
import os
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import urllib.parse
from datetime import datetime

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

try:
    from ml_optimizer import get_optimizer
    from email_analytics import get_analytics
    ML_ENABLED = True
    print("✅ ML Optimization enabled!")
except ImportError:
    ML_ENABLED = False
    print("⚠️  ML modules not found. Running in standard mode.")

EXCEL_FILE = "contacts.xlsx"
YOUR_MOBILE_NUMBER = "9993523379"
YOUR_GMAIL_ID = "[EMAIL_ADDRESS]"
def init_whatsapp_driver(cancel_check=None, confirm_check=None, on_waiting=None, on_finished=None):
    print("\n[WhatsApp] Initializing Chrome browser...")
    options = webdriver.ChromeOptions()
    
    user_data_dir = os.path.join(os.getcwd(), "chrome_profiles", "whatsapp")
    os.makedirs(user_data_dir, exist_ok=True)
    
    # --- FIX: Remove stale Chrome SingletonLock that blocks reuse ---
    singleton_lock = os.path.join(user_data_dir, "Default", "SingletonLock")
    if os.path.exists(singleton_lock):
        try:
            os.remove(singleton_lock)
            print("[WhatsApp] Removed stale Chrome profile lock.")
        except Exception as e:
            print(f"[WhatsApp] Warning: Could not remove profile lock: {e}")
            
    # Use proper path formatting to avoid ERR_INVALID_ARGUMENT
    user_data_dir = os.path.abspath(user_data_dir).replace("\\", "/")
    
    print(f"[WhatsApp] Using profile directory: {user_data_dir}")
    options.add_argument(f"--user-data-dir={user_data_dir}")
    
    # CRITICAL: Specify profile directory to ensure session persistence
    options.add_argument("--profile-directory=Default")
    
    # Anti-detection features
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Suppress console errors (like net error -2)
    options.add_argument("--log-level=3")
    
    # Stability arguments optimized for Windows session persistence
    options.add_argument("--start-maximized")
    options.add_argument("--disable-popup-blocking")
    options.page_load_strategy = 'eager'
    
    # IMPORTANT: Do NOT use --incognito or --disable-session-crashed-bubble
    # as they prevent session persistence
    
    # Add preferences to ensure session persistence
    prefs = {
        "profile.default_content_setting_values.notifications": 2,
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        # Enable cookies and local storage to save WhatsApp session
        "profile.default_content_settings.cookies": 1,
        "profile.cookie_controls_mode": 0,
        # Enable IndexedDB for WhatsApp Web session storage
        "profile.content_settings.exceptions.indexed_db": {
            "https://web.whatsapp.com,*": {
                "setting": 1
            }
        },
        # Ensure local storage is enabled
        "profile.content_settings.exceptions.local_storage": {
            "https://web.whatsapp.com,*": {
                "setting": 1
            }
        }
    }
    options.add_experimental_option("prefs", prefs)
    
    try:
        driver = webdriver.Chrome(options=options)
        # Bring Chrome window to the foreground on Windows
        try:
            driver.maximize_window()
        except:
            pass
        try:
            import ctypes
            hwnd = ctypes.windll.user32.FindWindowW(None, driver.title)
            if hwnd:
                ctypes.windll.user32.SetForegroundWindow(hwnd)
                ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        except:
            pass
    except Exception as e:
        print(f"❌ [WhatsApp] Failed to start Chrome: {str(e)}")
        print("   💡 Try clearing the chrome_profiles folder and run again.")
        print("   💡 Or delete: " + os.path.join(os.getcwd(), "chrome_profiles", "whatsapp"))
        raise
    
    print("[WhatsApp] Opening WhatsApp Web...")
    driver.get("https://web.whatsapp.com")
    
    if on_waiting:
        on_waiting()
    
    print("\n" + "=" * 60)
    print("   WHATSAPP LOGIN — MANUAL CONFIRMATION REQUIRED")
    print("=" * 60)
    print("\n📱 Steps to log in:")
    print("   1. Look at the Chrome window that just opened")
    print("   2. Scan the QR code with your WhatsApp mobile app")
    print("      (WhatsApp → Linked Devices → Link a Device)")
    print("   3. Wait for the WhatsApp inbox to fully load")
    print("   4. Come back here and click  ✅ Confirm WhatsApp Login")
    print("\n⏸️  Waiting for you to click the Confirm button on the dashboard...")
    
    logged_in = False
    start_wait = time.time()
    # Wait up to 5 minutes — user must click confirm button
    try:
        while time.time() - start_wait < 300:
            if cancel_check and cancel_check():
                print("🛑 WhatsApp login cancelled by user.")
                break
            if confirm_check and confirm_check():
                logged_in = True
                break
            time.sleep(1)
    finally:
        if on_finished:
            on_finished()
    
    if logged_in:
        print("✅ [WhatsApp] Login confirmed! Ready to send messages.\n")
    else:
        if not (cancel_check and cancel_check()):
            print("❌ [WhatsApp] Confirmation timeout (5 minutes exceeded).")
            raise Exception("WhatsApp login confirmation timeout.")
    
    return driver


def init_gmail_driver(cancel_check=None, confirm_check=None, on_waiting=None, on_finished=None):
    print("\n[Email] Initializing Gmail browser...")
    options = webdriver.ChromeOptions()
    
    user_data_dir = os.path.join(os.getcwd(), "chrome_profiles", "gmail")
    os.makedirs(user_data_dir, exist_ok=True)
    
    # --- FIX 1: Remove stale Chrome SingletonLock that blocks reuse ---
    singleton_lock = os.path.join(user_data_dir, "Default", "SingletonLock")
    if os.path.exists(singleton_lock):
        try:
            os.remove(singleton_lock)
            print("[Email] Removed stale Chrome profile lock.")
        except Exception as e:
            print(f"[Email] Warning: Could not remove profile lock: {e}")
    
    # Use proper path formatting to avoid ERR_INVALID_ARGUMENT on Windows
    user_data_dir = os.path.abspath(user_data_dir).replace("\\", "/")
    options.add_argument(f"--user-data-dir={user_data_dir}")
    
    # CRITICAL: Specify profile directory to ensure session persistence
    options.add_argument("--profile-directory=Default")
    
    # Anti-detection features
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Suppress console errors
    options.add_argument("--log-level=3")
    
    # Stability arguments for Windows
    options.add_argument("--start-maximized")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # --- FIX 2: Set page load strategy correctly via capability ---
    options.set_capability("pageLoadStrategy", "eager")
    
    # Preferences
    prefs = {
        "profile.default_content_setting_values.notifications": 2,
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False
    }
    options.add_experimental_option("prefs", prefs)
    
    try:
        driver = webdriver.Chrome(options=options)
        # Bring Chrome window to the foreground on Windows
        try:
            driver.maximize_window()
        except:
            pass
        try:
            import ctypes
            hwnd = ctypes.windll.user32.FindWindowW(None, driver.title)
            if hwnd:
                ctypes.windll.user32.SetForegroundWindow(hwnd)
                ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        except:
            pass
    except Exception as e:
        print(f"❌ [Email] Failed to start Chrome: {str(e)}")
        print("   💡 Try clearing the chrome_profiles/gmail folder and run again.")
        print("   💡 Or delete: " + os.path.join(os.getcwd(), "chrome_profiles", "gmail"))
        raise
    
    print("[Email] Navigating to Gmail...")
    try:
        driver.get("https://mail.google.com")
        time.sleep(1)
    except Exception as e:
        print(f"[Email] Warning during navigation: {e}")
        
    if on_waiting:
        on_waiting()
    
    print("\n" + "=" * 60)
    print("   GMAIL LOGIN — MANUAL CONFIRMATION REQUIRED")
    print("=" * 60)
    print("\n📧 Steps to log in:")
    print("   1. Look at the Chrome window that just opened")
    print("   2. Enter your Gmail address and click Next")
    print("   3. Enter your password and click Next")
    print("   4. Complete any 2FA verification if prompted")
    print("   5. Wait until you can see your Gmail inbox")
    print("   6. Come back here and click  ✅ Confirm Gmail Login")
    print("\n⏸️  Waiting for you to click the Confirm button on the dashboard...")
    
    logged_in = False
    start_wait = time.time()
    # Wait up to 5 minutes — user must click confirm button
    try:
        while time.time() - start_wait < 300:
            if cancel_check and cancel_check():
                print("🛑 Gmail login cancelled by user.")
                break
            if confirm_check and confirm_check():
                logged_in = True
                break
            time.sleep(1)
    finally:
        if on_finished:
            on_finished()
    
    if logged_in:
        print("✅ [Email] Login confirmed! Navigating to Gmail inbox...\n")
        # Navigate to inbox after manual confirmation
        try:
            driver.get("https://mail.google.com/mail/u/0/#inbox")
            time.sleep(3)
        except:
            pass
    else:
        if not (cancel_check and cancel_check()):
            print("❌ [Email] Confirmation timeout (5 minutes exceeded).")
            raise Exception("Gmail login confirmation timeout.")
    
    return driver



def read_contacts():
    try:
        df = pd.read_excel(EXCEL_FILE)
        print(f"\n✅ Loaded {len(df)} contacts from {EXCEL_FILE}")
        return df
    except FileNotFoundError:
        print(f"\n❌ Error: Excel file '{EXCEL_FILE}' not found!")
        return None
    except Exception as e:
        print(f"\n❌ Error reading Excel file: {str(e)}")
        return None


def display_menu():
    print("\n" + "="*60)
    print("   BULK MESSAGING SYSTEM | Lintcloud Technologies")
    print("="*60)
    print("\n📬 Select Messaging Service:")
    print("\n[1] WhatsApp Only (Single Sign-In)")
    print("[2] Email Only (Single Sign-In)")
    print("[3] Both WhatsApp + Email (Single Sign-In for Both)")
    print("\n[0] Exit")
    print("-"*60)
    
    choice = input("\nEnter your choice (0-3): ").strip()
    return choice


def run_sending_process(choice, whatsapp_driver, gmail_driver, progress_callback=None, cancel_check=None,
                        confirm_check_whatsapp=None, confirm_check_gmail=None,
                        on_waiting_whatsapp=None, on_finished_whatsapp=None,
                        on_waiting_gmail=None, on_finished_gmail=None):
    global ML_ENABLED
    
    contacts_df = read_contacts()
    if contacts_df is None or len(contacts_df) == 0:
        print("❌ No contacts to send to.")
        return False, whatsapp_driver, gmail_driver
    
    ml_optimizer = None
    analytics = None
    if ML_ENABLED:
        try:
            ml_optimizer = get_optimizer('config.json')
            analytics = get_analytics()
            contacts_df = ml_optimizer.optimize_contact_list(contacts_df)
        except Exception as e:
            print(f"⚠️  ML initialization failed: {e}")
            ml_optimizer = None
            analytics = None
            
    use_whatsapp = choice in ['1', '3']
    use_email = choice in ['2', '3']
    
    if use_whatsapp:
        if whatsapp_driver is None or not actions.is_browser_alive(whatsapp_driver):
            whatsapp_driver = init_whatsapp_driver(
                cancel_check=cancel_check,
                confirm_check=confirm_check_whatsapp,
                on_waiting=on_waiting_whatsapp,
                on_finished=on_finished_whatsapp
            )
        else:
            print("✅ [WhatsApp] Reusing existing Chrome session.")
            
    if use_email:
        if gmail_driver is None or not actions.is_browser_alive(gmail_driver):
            gmail_driver = init_gmail_driver(
                cancel_check=cancel_check,
                confirm_check=confirm_check_gmail,
                on_waiting=on_waiting_gmail,
                on_finished=on_finished_gmail
            )
        else:
            print("✅ [Email] Reusing existing Chrome session.")
            try:
                if "mail.google.com/mail" not in gmail_driver.current_url:
                    gmail_driver.get("https://mail.google.com/mail/u/0/#inbox")
                    time.sleep(2)
            except:
                pass
                
    whatsapp_success = 0
    email_success = 0
    total_contacts = len(contacts_df)
    
    # --- FIX: Initialize loop variables so the final progress_callback
    #     never raises UnboundLocalError if the loop exits before iteration 0 ---
    display_name = ''
    email = ''
    phone = ''
    index = 0
    
    print("\n============================================================\n   STARTING BULK MESSAGING\n============================================================\n")
    
    for index, row in contacts_df.iterrows():
        if cancel_check and cancel_check():
            print("\n🛑 Sending process cancelled by user.")
            break
            
        name = row['Name']
        if pd.isna(name) or not name or str(name).strip() == '':
            name = "Unknown Contact"
            display_name = "[No Name in Excel]"
        else:
            name = str(name).strip()
            display_name = name
            
        phone = row.get('Phone', '')
        phone = '' if pd.isna(phone) else str(phone).strip()
        
        email = row.get('Email', '')
        email = '' if pd.isna(email) else str(email).strip()
        
        # Call status callback
        if progress_callback:
            progress_callback({
                'current': index + 1,
                'total': total_contacts,
                'name': display_name,
                'email': email,
                'phone': phone,
                'status': 'sending',
                'whatsapp_success': whatsapp_success,
                'email_success': email_success
            })
            
        print(f"\n--- Contact {index + 1}/{total_contacts}: {display_name} ---")
        
        # Hot reload actions
        try:
            importlib.reload(actions)
        except Exception as e:
            print(f"⚠️  Hot reload failed: {e}")
            
        if use_whatsapp:
            if not phone:
                print("⚠️  [WhatsApp] No phone number found, skipping...")
            else:
                if actions.send_whatsapp_message(whatsapp_driver, str(phone), name, ml_optimizer):
                    whatsapp_success += 1
                    
        if use_email:
            if not actions.is_browser_alive(gmail_driver):
                print("❌ [Email] Browser window was closed! Stopping email operations.")
                use_email = False
                continue
                
            if not email:
                print("⚠️  [Email] No email address found, skipping...")
            else:
                send_start = time.time()
                if actions.send_email_via_browser(gmail_driver, email, name, ml_optimizer, analytics):
                    email_success += 1
                    send_duration = time.time() - send_start
                    if ml_optimizer:
                        ml_optimizer.record_send_attempt(True, send_duration)
                    if analytics and email_success % 5 == 0:
                        analytics.print_dashboard()
                else:
                    if ml_optimizer:
                        ml_optimizer.record_send_attempt(False)
                        
    print("\n============================================================\n   MESSAGING COMPLETED\n============================================================\n")
    if use_whatsapp:
        print(f"✅ WhatsApp: {whatsapp_success}/{total_contacts} messages sent successfully")
    if use_email:
        print(f"✅ Email: {email_success}/{total_contacts} messages sent successfully")
        
    if ml_optimizer and email_success > 0:
        ml_optimizer.print_performance_summary()
    if analytics:
        analytics.print_dashboard()
        analytics.generate_report()
        print("\n📊 Detailed performance report saved to 'performance_report.txt'")
        
    if progress_callback:
        cancelled = cancel_check and cancel_check()
        progress_callback({
            'current': total_contacts if not cancelled else index,
            'total': total_contacts,
            'name': display_name or '-',
            'email': email or '-',
            'phone': phone or '-',
            'status': 'cancelled' if cancelled else 'completed',
            'whatsapp_success': whatsapp_success,
            'email_success': email_success
        })
        
    return True, whatsapp_driver, gmail_driver


def main():
    whatsapp_driver = None
    gmail_driver = None
    try:
        while True:
            choice = display_menu()
            if choice == '0':
                print("\n👋 Exiting program. Goodbye!")
                break
            if choice not in ['1', '2', '3']:
                print("\n❌ Invalid choice! Please try again.")
                continue
            
            success, whatsapp_driver, gmail_driver = run_sending_process(
                choice, whatsapp_driver, gmail_driver
            )
    finally:
        # Clean up browser instances upon exit
        if whatsapp_driver:
            print("\n🧹 Closing WhatsApp browser session...")
            try:
                whatsapp_driver.quit()
            except:
                pass
        if gmail_driver:
            print("🧹 Closing Gmail browser session...")
            try:
                gmail_driver.quit()
            except:
                pass


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Program interrupted by user. Exiting...")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
