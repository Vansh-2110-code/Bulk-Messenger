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

import json

def get_valid_brochures():
    try:
        if os.path.exists('config.json'):
            with open('config.json', 'r') as f:
                cfg = json.load(f)
            if not cfg.get('send_with_attachment', True):
                return []
            path = cfg.get('attachment_path', '')
            if path:
                if os.path.exists(path):
                    return [os.path.abspath(path)]
                rel_path = os.path.join(os.getcwd(), os.path.basename(path))
                if os.path.exists(rel_path):
                    return [os.path.abspath(rel_path)]
    except Exception as e:
        print(f"   ⚠️  Error reading brochure config: {e}")
    
    for fallback in ["timing.pdf", "Lintcloud_Brochure.pdf"]:
        if os.path.exists(fallback):
            return [os.path.abspath(fallback)]
    return []

# Keep variable for compatibility
BROCHURE_PATHS = get_valid_brochures()

# CC Recipients - these emails will be CC'd on all outgoing emails
CC_RECIPIENTS = []

WHATSAPP_WAIT_TIME = 30
MESSAGE_SEND_BUTTON_WAIT = 10

def get_message_body(name):
    try:
        if os.path.exists('config.json'):
            with open('config.json', 'r') as f:
                cfg = json.load(f)
            custom_template = cfg.get('whatsapp_template', '')
            if custom_template:
                res = custom_template.replace('{Name}', name).replace('{name}', name)
                return clean_text_for_selenium(res)
    except Exception as e:
        print(f"Error loading custom WhatsApp template: {e}")

    return """Dear Participants,

Greetings from Joy University!

Thank you for registering for our symposium EVOLVAI 2K26. We are excited to have you join us for this innovative and engaging event. Your participation truly adds value to the experience, and we look forward to hosting you on campus.

To ensure a smooth journey, transportation has been arranged from the following locations:

🚌 Bus Details:

From Nagercoil:

- Boarding Point: In front of British Bakery,Vadassery 
- Boarding Time: 7:45 AM
- Bus Driver Contact Number: 9597446074

From Tirunelveli:

- Boarding Point: -
   1. Varnarpeti,infornt of Laxmi Gayatri Hotel
2.New bus Stand, In front of Unlimited Showroom 
- Boarding Time: 6:30 AM
- Bus Driver Contact Number: 9715111519

Kindly make sure to reach your respective boarding points on time to avoid any delays.

�📌 Please note:

- The detailed event schedule has been attached to this email for your reference.
- The bus driver contact numbers have also been included for your convenience.

We request you to go through the schedule carefully and plan your participation accordingly.

If you have any queries or need assistance, feel free to reach out to the event coordinators.

Looking forward to seeing you at EVOLVAI 2K26! 🚀

Student Coordinators
1.G.Shashindra Reddy- 7981880223
2.Hana - 7845190631
3.Shivam Pandey -9060155621

Warm regards,
Team EVOLVAI 2K26
Joy University"""


def is_browser_alive(driver):
    try:
        _ = driver.current_url
        return True
    except Exception as e:
        print(f"DEBUG: is_browser_alive exception: {e}")
        return False


def clean_text_for_selenium(text):
    return ''.join(char for char in text if ord(char) <= 0xFFFF)


def get_email_body_text(name):
    try:
        if os.path.exists('config.json'):
            with open('config.json', 'r') as f:
                cfg = json.load(f)
            custom_template = cfg.get('email_template', '')
            if custom_template:
                res = custom_template.replace('{Name}', name).replace('{name}', name)
                return clean_text_for_selenium(res)
    except Exception as e:
        print(f"Error loading custom Email template: {e}")

    message = """Dear Participants,

Greetings from Joy University!

Thank you for registering for our symposium EVOLVAI 2K26. We are excited to have you join us for this innovative and engaging event. Your participation truly adds value to the experience, and we look forward to hosting you on campus.

To ensure a smooth journey, transportation has been arranged from the following locations:

🚌 Bus Details:

From Nagercoil:

- Boarding Point: In front of British Bakery,Vadassery 
- Boarding Time: 7:45 AM
- Bus Driver Contact Number: 9597446074

From Tirunelveli:

- Boarding Point: -
   1. Varnarpeti,infornt of Laxmi Gayatri Hotel
2.New bus Stand, In front of Unlimited Showroom 
- Boarding Time: 6:30 AM
- Bus Driver Contact Number: 9715111519

Kindly make sure to reach your respective boarding points on time to avoid any delays.

📌 Please note:

- The detailed event schedule has been attached to this email for your reference.
- The bus driver contact numbers have also been included for your convenience.

We request you to go through the schedule carefully and plan your participation accordingly.

If you have any queries or need assistance, feel free to reach out to the event coordinators.

Looking forward to seeing you at EVOLVAI 2K26! 🚀

Student Coordinators
1.G.Shashindra Reddy- 7981880223
2.Hana - 7845190631
3.Shivam Pandey -9060155621

Warm regards,
Team EVOLVAI 2K26
Joy University"""
    
    return clean_text_for_selenium(message)


def close_all_compose_windows(driver):
    """Close all open compose windows to ensure clean state."""
    try:
        compose_windows = driver.find_elements(By.XPATH, "//div[@role='dialog']")
        visible_windows = [w for w in compose_windows if w.is_displayed()]
        
        if len(visible_windows) == 0:
            return 0
        
        print(f"   🧹 Found {len(visible_windows)} open compose window(s), closing...")
        
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.common.action_chains import ActionChains
        
        for window in visible_windows:
            try:
                # Try clicking the close button
                close_buttons = window.find_elements(By.XPATH, ".//img[@aria-label='Save & close'] | .//img[@aria-label='Discard']")
                if close_buttons:
                    for btn in close_buttons:
                        try:
                            if btn.is_displayed():
                                btn.click()
                                time.sleep(0.5)
                                break
                        except:
                            continue
                
                # If close button didn't work, use Escape key
                if window.is_displayed():
                    actions = ActionChains(driver)
                    actions.send_keys(Keys.ESCAPE)
                    actions.perform()
                    time.sleep(0.5)
            except:
                continue
        
        # Verify windows are closed
        time.sleep(0.5)
        compose_windows = driver.find_elements(By.XPATH, "//div[@role='dialog']")
        remaining = [w for w in compose_windows if w.is_displayed()]
        
        if len(remaining) > 0:
            # Force close with multiple Escape presses
            actions = ActionChains(driver)
            for _ in range(3):
                actions.send_keys(Keys.ESCAPE)
            actions.perform()
            time.sleep(0.5)
        
        return len(visible_windows)
    except Exception as e:
        print(f"   ⚠️  Error closing compose windows: {e}")
        return 0


def send_whatsapp_message(driver, phone, name, ml_optimizer=None):
    def a_sleep(secs):
        if ml_optimizer and hasattr(ml_optimizer, 'get_action_delay'):
            import time as _time
            _time.sleep(ml_optimizer.get_action_delay(secs))
        else:
            import time as _time
            _time.sleep(secs)

    try:
        message = get_message_body(name)
        
        phone_str = str(phone).strip()
        
        if '.' in phone_str:
            phone_str = phone_str.split('.')[0]
        
        import re
        digits_only = re.sub(r'\D', '', phone_str)
        
        if digits_only.startswith('91') and len(digits_only) > 10:
            formatted_phone = digits_only
        elif digits_only.startswith('0') and len(digits_only) == 11:
            formatted_phone = '91' + digits_only[1:]
        elif len(digits_only) == 10:
            formatted_phone = '91' + digits_only
        else:
            formatted_phone = digits_only
        
        url = f"https://web.whatsapp.com/send?phone={formatted_phone}&text={urllib.parse.quote(message, safe=':/')}"
        print(f"[WhatsApp] Opening chat with {name}")
        print(f"   📱 Phone: +{formatted_phone}")
        driver.get(url)
        
        a_sleep(5)
        
        send_button_selectors = [
            '//button[@aria-label="Send"]',
            '//span[@data-icon="send"]',
            '//button[contains(@aria-label, "Send")]',
            '//*[@data-icon="send"]/ancestor::button',
            '//span[@data-testid="send"]/ancestor::button'
        ]
        
        send_button = None
        for selector in send_button_selectors:
            try:
                elems = driver.find_elements(By.XPATH, selector)
                for btn in elems:
                    if btn.is_displayed() and btn.is_enabled():
                        send_button = btn
                        print(f"   ✅ Found send button")
                        break
            except:
                continue
            if send_button:
                break
        
        if not send_button:
            print(f"   💡 Trying keyboard shortcut Enter...")
            from selenium.webdriver.common.keys import Keys
            from selenium.webdriver.common.action_chains import ActionChains
            actions = ActionChains(driver)
            actions.send_keys(Keys.ENTER)
            actions.perform()
            a_sleep(2)
        else:
            a_sleep(1)
            send_button.click()
        
        print(f"✅ [WhatsApp] Text message sent to {name}")
        
        valid_brochures = get_valid_brochures()
        if valid_brochures:
            print("   📎 [WhatsApp] Automating file attachments...")
            for brochure_path in valid_brochures:
                try:
                    abs_path = os.path.abspath(brochure_path)
                    print(f"   📄 Attaching file: {os.path.basename(abs_path)}")
                    
                    attach_input = None
                    for selector in ["//input[@accept='*']", "//input[@type='file']"]:
                        try:
                            inputs = driver.find_elements(By.XPATH, selector)
                            for inp in inputs:
                                attach_input = inp
                                break
                            if attach_input:
                                break
                        except:
                            continue
                    
                    if not attach_input:
                        # Try clicking attach button to reveal file input
                        attach_btn_selectors = [
                            '//div[@aria-label="Attach"]',
                            '//span[@data-icon="plus"]',
                            '//span[@data-icon="attach-menu-plus"]',
                            '//div[@title="Attach"]',
                            '//button[@title="Attach"]'
                        ]
                        for btn_sel in attach_btn_selectors:
                            try:
                                btn = driver.find_element(By.XPATH, btn_sel)
                                if btn.is_displayed():
                                    btn.click()
                                    a_sleep(1)
                                    break
                            except:
                                continue
                        
                        # Look again for inputs
                        for selector in ["//input[@accept='*']", "//input[@type='file']"]:
                            try:
                                inputs = driver.find_elements(By.XPATH, selector)
                                for inp in inputs:
                                    attach_input = inp
                                    break
                                if attach_input:
                                    break
                            except:
                                continue
                    
                    if attach_input:
                        attach_input.send_keys(abs_path)
                        a_sleep(3) # Wait for preview screen
                        
                        preview_send_selectors = [
                            '//span[@data-icon="send"]',
                            '//div[@aria-label="Send"]',
                            '//span[@data-testid="send"]/ancestor::button',
                            '//button[@aria-label="Send"]'
                        ]
                        sent_attachment = False
                        for p_sel in preview_send_selectors:
                            try:
                                p_btns = driver.find_elements(By.XPATH, p_sel)
                                for btn in p_btns:
                                    if btn.is_displayed():
                                        btn.click()
                                        print("   ✅ [WhatsApp] Clicked preview send button")
                                        sent_attachment = True
                                        break
                            except:
                                continue
                            if sent_attachment:
                                break
                        
                        if not sent_attachment:
                            print("   💡 Try pressing Enter on preview screen...")
                            from selenium.webdriver.common.keys import Keys
                            from selenium.webdriver.common.action_chains import ActionChains
                            actions_chain = ActionChains(driver)
                            actions_chain.send_keys(Keys.ENTER)
                            actions_chain.perform()
                            a_sleep(2)
                            print("   ✅ [WhatsApp] Sent via Enter key fallback")
                        else:
                            a_sleep(2)
                    else:
                        print("   ⚠️  [WhatsApp] Could not find file input element. Trying manual fallback...")
                        for remaining in range(10, 0, -1):
                            print(f"      Manual attachment fallback: {remaining} seconds remaining...", end='\r')
                            a_sleep(1)
                except Exception as e:
                    print(f"   ⚠️  [WhatsApp] Failed to attach {os.path.basename(brochure_path)}: {str(e)}")
        
        # Delay before next contact removed as per request
        
        return True
        
    except TimeoutException:
        print(f"❌ [WhatsApp] Timeout: Could not send message to {name} ({phone})")
        print(f"   💡 Make sure the contact exists on WhatsApp")
        return False
    except Exception as e:
        print(f"❌ [WhatsApp] Error sending to {name} ({phone}): {str(e)}")
        return False



def send_email_via_browser(driver, to_email, name, ml_optimizer=None, analytics=None):
    def a_sleep(secs):
        if ml_optimizer and hasattr(ml_optimizer, 'get_action_delay'):
            import time as _time
            _time.sleep(ml_optimizer.get_action_delay(secs))
        else:
            import time as _time
            _time.sleep(secs)

    start_time = time.time()
    
    try:
        if not is_browser_alive(driver):
            print(f"❌ [Email] Browser window was closed! Please keep the browser open.")
            print(f"   💡 Tip: Do not manually close the Chrome browser while the script is running.")
            return False
        
        print(f"[Email] Composing email to {name} ({to_email})...")
        
        # Clean up any lingering compose windows before starting
        closed_count = close_all_compose_windows(driver)
        if closed_count > 0:
            print(f"   ✅ Closed {closed_count} lingering compose window(s)")
        
        if ml_optimizer:
            engagement = ml_optimizer.get_engagement_prediction(to_email, name)
            print(f"   🎯 Engagement prediction: {engagement['probability']*100:.0f}% ({engagement['confidence']})")
        
        a_sleep(1)
        
        print("   📝 Step 1: Clicking Compose button...")
        try:
            compose_selectors = [
                "//div[contains(@class, 'T-I') and contains(@class, 'T-I-KE')]",
                "//div[@role='button' and contains(., 'Compose')]",
                "//div[contains(@aria-label, 'Compose')]"
            ]
            
            compose_clicked = False
            import time as _time
            end_time = _time.time() + 5
            while _time.time() < end_time and not compose_clicked:
                for selector in compose_selectors:
                    try:
                        elems = driver.find_elements(By.XPATH, selector)
                        for btn in elems:
                            if btn.is_displayed() and btn.is_enabled():
                                btn.click()
                                compose_clicked = True
                                print("   ✅ Compose button clicked!")
                                break
                    except:
                        continue
                    if compose_clicked:
                        break
                if not compose_clicked:
                    a_sleep(0.5)
            
            if not compose_clicked:
                print("   ⚠️  Trying keyboard shortcut...")
                from selenium.webdriver.common.keys import Keys
                from selenium.webdriver.common.action_chains import ActionChains
                actions = ActionChains(driver)
                actions.send_keys('c')
                actions.perform()
            
            a_sleep(3.5)
        except Exception as e:
            print(f"   ❌ Could not click Compose: {str(e)}")
            return False
        
        print("   📧 Step 2: Adding recipient...")
        try:
            a_sleep(1)
            
            to_selectors = [
                "//textarea[@name='to']",
                "//input[@name='to']",
                "//textarea[@aria-label='To']",
                "//input[@aria-label='To']",
                "//textarea[contains(@aria-label, 'Recipients')]",
                "//input[contains(@aria-label, 'Recipients')]",
                "//div[@aria-label='To']//textarea",
                "//div[@aria-label='To']//input",
                "//textarea[@role='combobox']",
                "//input[@role='combobox']",
                "//div[contains(@class, 'agP')]//textarea",
                "//div[contains(@class, 'wO')]//input"
            ]
            
            to_field = None
            selector_used = None
            
            import time as _time
            end_time = _time.time() + 5
            while _time.time() < end_time and not to_field:
                for selector in to_selectors:
                    try:
                        elems = driver.find_elements(By.XPATH, selector)
                        for elem in elems:
                            if elem.is_displayed() and elem.is_enabled():
                                to_field = elem
                                selector_used = selector
                                print(f"   ✅ Found To field using selector")
                                break
                    except:
                        continue
                    if to_field:
                        break
                if not to_field:
                    a_sleep(0.5)
            
            if to_field:
                try:
                    to_field.click()
                    a_sleep(0.5)
                    to_field.clear()
                    a_sleep(0.3)
                    to_field.send_keys(to_email)
                    print(f"   ✅ Recipient added: {to_email}")
                    a_sleep(0.8)
                except Exception as e:
                    print(f"   ⚠️  Error filling field: {e}")
                    print(f"   💡 Trying keyboard input method...")
                    
                    from selenium.webdriver.common.keys import Keys
                    from selenium.webdriver.common.action_chains import ActionChains
                    
                    actions = ActionChains(driver)
                    # Send email and then Tab to confirm/move to next field
                    actions.send_keys(to_email)
                    actions.send_keys(Keys.TAB)
                    actions.perform()
                    a_sleep(1.0)
                    print(f"   ✅ Recipient added via keyboard")
            else:
                print("   ❌ Could not find To field with any selector")
                print("   🔍 Debug: Checking compose window state...")
                
                try:
                    all_inputs = driver.find_elements(By.XPATH, "//div[@role='dialog']//input | //div[@role='dialog']//textarea")
                    print(f"   📋 Found {len(all_inputs)} input/textarea elements in compose window")
                    
                    if len(all_inputs) > 0:
                        to_field_found = False
                        
                        for elem in all_inputs:
                            try:
                                if not elem.is_displayed():
                                    continue
                                
                                aria_label = elem.get_attribute('aria-label') or ''
                                name = elem.get_attribute('name') or ''
                                placeholder = elem.get_attribute('placeholder') or ''
                                role = elem.get_attribute('role') or ''
                                
                                is_to_field = (
                                    'to' in name.lower() or
                                    'to' in aria_label.lower() or
                                    'recipient' in aria_label.lower() or
                                    'recipient' in placeholder.lower() or
                                    role == 'combobox'
                                )
                                
                                if is_to_field:
                                    print(f"   🎯 Identified To field: {aria_label or name or role}")
                                    elem.click()
                                    a_sleep(0.3)
                                    elem.clear()
                                    elem.send_keys(to_email)
                                    print(f"   ✅ Recipient added using smart selection")
                                    to_field_found = True
                                    break
                            except:
                                continue
                        
                        if not to_field_found:
                            print(f"   💡 Trying first visible combobox/textarea...")
                            for elem in all_inputs:
                                try:
                                    if elem.is_displayed():
                                        role = elem.get_attribute('role') or ''
                                        tag = elem.tag_name
                                        
                                        if role == 'combobox' or tag == 'textarea':
                                            elem.click()
                                            a_sleep(0.3)
                                            elem.send_keys(to_email)
                                            print(f"   ✅ Used {tag} with role={role}")
                                            to_field_found = True
                                            break
                                except:
                                    continue
                        
                        if not to_field_found:
                            for elem in all_inputs:
                                try:
                                    if elem.is_displayed():
                                        elem.click()
                                        a_sleep(0.3)
                                        elem.send_keys(to_email)
                                        print(f"   ✅ Used first available input field")
                                        to_field_found = True
                                        break
                                except:
                                    continue
                        
                        if not to_field_found:
                            print("   ❌ Could not use any input field")
                            return False
                    else:
                        print("   💡 Compose window might not be fully loaded")
                        print("   ⏳ Waiting 3 more seconds and retrying...")
                        a_sleep(3)
                        
                        try:
                            to_field = driver.find_element(By.XPATH, "//div[@role='dialog']//textarea[@role='combobox']")
                            to_field.click()
                            to_field.send_keys(to_email)
                            print(f"   ✅ Recipient added (retry successful)")
                        except:
                            try:
                                to_field = driver.find_element(By.XPATH, "//div[@role='dialog']//textarea")
                                to_field.click()
                                to_field.send_keys(to_email)
                                print(f"   ✅ Recipient added (retry successful)")
                            except:
                                print("   ❌ All attempts failed")
                                return False
                except Exception as debug_error:
                    print(f"   ❌ Debug failed: {debug_error}")
                    return False
        except Exception as e:
            print(f"   ❌ Error adding recipient: {str(e)}")
            return False
        
        # CRITICAL: Verify compose window is still open after adding recipient
        try:
            a_sleep(0.5)
            compose_windows = driver.find_elements(By.XPATH, "//div[@role='dialog']")
            if not any(w.is_displayed() for w in compose_windows):
                print("   ❌ CRITICAL: Compose window closed after adding recipient!")
                print("   💡 This usually means the email address triggered an error or autocomplete action")
                print("   🔄 Skipping this contact to prevent further errors...")
                return False
        except Exception as verify_error:
            print(f"   ⚠️  Could not verify compose window state: {verify_error}")
        
        # Add CC recipients if configured
        if CC_RECIPIENTS:
            print(f"   📧 Step 2b: Adding {len(CC_RECIPIENTS)} CC recipient(s)...")
            try:
                a_sleep(0.5)
                
                # First, need to expose the CC field by clicking "Cc" or "Recipients"
                cc_button_selectors = [
                    "//span[@role='link' and contains(text(), 'Cc')]",
                    "//span[contains(@class, 'aoD') and contains(., 'Cc')]",
                    "//*[contains(text(), 'Cc') and @role='link']",
                    "//div[@aria-label='Add Cc recipients']//span",
                    "//span[text()='Cc']"
                ]
                
                cc_button_clicked = False
                for selector in cc_button_selectors:
                    try:
                        cc_button = driver.find_element(By.XPATH, selector)
                        if cc_button.is_displayed():
                            cc_button.click()
                            a_sleep(0.5)
                            cc_button_clicked = True
                            print(f"   ✅ Opened CC field")
                            break
                    except:
                        continue
                
                if not cc_button_clicked:
                    print(f"   ⚠️  Could not find CC button, trying direct input...")
                
                # Now find and fill the CC field
                cc_selectors = [
                    "//textarea[@name='cc']",
                    "//input[@name='cc']",
                    "//textarea[@aria-label='Cc']",
                    "//input[@aria-label='Cc']",
                    "//div[@aria-label='Cc']//textarea",
                    "//div[@aria-label='Cc']//input"
                ]
                
                cc_field = None
                import time as _time
                end_time = _time.time() + 3
                while _time.time() < end_time and not cc_field:
                    for selector in cc_selectors:
                        try:
                            elems = driver.find_elements(By.XPATH, selector)
                            for elem in elems:
                                if elem.is_displayed() and elem.is_enabled():
                                    cc_field = elem
                                    print(f"   ✅ Found CC field")
                                    break
                        except:
                            continue
                        if cc_field:
                            break
                    if not cc_field:
                        a_sleep(0.5)
                
                if cc_field:
                    # Add all CC recipients to the field
                    cc_field.click()
                    a_sleep(0.3)
                    cc_field.clear()
                    
                    for i, cc_email in enumerate(CC_RECIPIENTS):
                        cc_field.send_keys(cc_email)
                        if i < len(CC_RECIPIENTS) - 1:
                            # Use comma or Tab to add multiple CC recipients
                            from selenium.webdriver.common.keys import Keys
                            cc_field.send_keys(Keys.ENTER)
                            a_sleep(0.2)
                    
                    print(f"   ✅ Added CC recipients: {', '.join(CC_RECIPIENTS)}")
                    a_sleep(0.5)
                else:
                    print(f"   ⚠️  Could not find CC field - emails will be sent without CC")
                    
            except Exception as e:
                print(f"   ⚠️  Error adding CC recipients: {str(e)}")
                print(f"   💡 Continuing without CC...")
        

        print("   📌 Step 3: Adding subject...")
        try:
            from selenium.webdriver.common.keys import Keys
            from selenium.webdriver.common.action_chains import ActionChains
            
            # IMPORTANT: Wait for Gmail's recipient dropdown to disappear
            # This prevents "element click intercepted" errors when clicking subject field
            print("   ⏳ Waiting for UI to settle...")
            a_sleep(2)  # Give Gmail time to close recipient dropdown
            
            # Also try to click away from the recipient field to ensure dropdown closes
            try:
                actions = ActionChains(driver)
                actions.send_keys(Keys.ESCAPE).perform()
                a_sleep(0.5)
            except:
                pass
            
            # First verify compose window is still open
            try:
                compose_windows = driver.find_elements(By.XPATH, "//div[@role='dialog']")
                if not any(w.is_displayed() for w in compose_windows):
                    print("   ❌ Compose window closed unexpectedly!")
                    return False
            except:
                print("   ❌ Cannot verify compose window state")
                return False
            
            subject_text = "EVOLVAI 2K26 – Event Details, Bus Boarding Points & Schedule"
            subject_entered = False
            
            # PRIMARY METHOD: Find and click the subject field directly (MOST RELIABLE)
            print("   💡 Searching for subject field...")
            
            # Expanded subject field selectors for better reliability
            subject_selectors = [
                "//input[@name='subjectbox']",
                "//input[@aria-label='Subject']",
                "//input[contains(@aria-label, 'Subject')]",
                "//input[@placeholder='Subject']",
                "//div[@role='dialog']//input[@type='text' and not(@name='to') and not(@name='cc') and not(@name='bcc')]",
                "//div[contains(@class, 'aoD')]//input",  # Gmail subject box class
                "//input[@class='aoT']",  # Another Gmail subject class
            ]
            
            subject_field = None
            for selector in subject_selectors:
                try:
                    fields = driver.find_elements(By.XPATH, selector)
                    for field in fields:
                        if field.is_displayed() and field.is_enabled():
                            # Verify it's not the TO or CC field
                            name_attr = field.get_attribute('name') or ''
                            aria_label = field.get_attribute('aria-label') or ''
                            role_attr = field.get_attribute('role') or ''
                            
                            # Skip comboboxes (those are recipient fields)
                            if role_attr == 'combobox':
                                continue
                            
                            # Skip TO, CC, BCC fields
                            if any(x in name_attr.lower() for x in ['to', 'cc', 'bcc']):
                                continue
                            if any(x in aria_label.lower() for x in ['to', 'cc', 'bcc', 'recipient']):
                                continue
                            
                            # This looks like the subject field!
                            subject_field = field
                            print(f"   ✅ Found subject field (selector: {selector[:40]}...)")
                            break
                    if subject_field:
                        break
                except:
                    continue
            
            # Smart detection fallback
            if not subject_field:
                print(f"   🔍 Using smart detection...")
                try:
                    # Get all input fields in the compose dialog
                    all_inputs = driver.find_elements(By.XPATH, "//div[@role='dialog']//input[@type='text']")
                    
                    for inp in all_inputs:
                        if inp.is_displayed() and inp.is_enabled():
                            name = inp.get_attribute('name') or ''
                            aria_label = inp.get_attribute('aria-label') or ''
                            role = inp.get_attribute('role') or ''
                            value = inp.get_attribute('value') or ''
                            
                            # Skip comboboxes
                            if role == 'combobox':
                                continue
                            
                            # Skip TO, CC, BCC fields
                            if any(x in name.lower() for x in ['to', 'cc', 'bcc']):
                                continue
                            if any(x in aria_label.lower() for x in ['to', 'cc', 'bcc', 'recipient']):
                                continue
                            
                            # Skip if it already has content (likely recipient field with email)
                            if '@' in value:
                                continue
                            
                            # This is likely the subject field
                            subject_field = inp
                            print(f"   ✅ Found subject field using smart detection")
                            break
                except Exception as smart_err:
                    print(f"   ⚠️  Smart detection failed: {smart_err}")
            
            # Try to enter subject in the found field
            if subject_field:
                try:
                    # Scroll field into view
                    driver.execute_script("arguments[0].scrollIntoView(true);", subject_field)
                    a_sleep(0.3)
                    
                    # Click the field
                    subject_field.click()
                    a_sleep(0.3)
                    
                    # Clear any existing content
                    subject_field.clear()
                    a_sleep(0.2)
                    
                    # Enter the subject
                    subject_field.send_keys(subject_text)
                    a_sleep(0.5)
                    
                    # VERIFY the subject was entered
                    entered_value = subject_field.get_attribute('value') or ''
                    if subject_text in entered_value or len(entered_value) > 10:
                        print(f"   ✅ Subject entered successfully: {subject_text[:50]}...")
                        print(f"   ✅ Verified in field: {entered_value[:50]}...")
                        subject_entered = True
                    else:
                        print(f"   ⚠️  Subject may not have been entered correctly")
                        print(f"   📝 Field value: '{entered_value}'")
                        
                except Exception as field_error:
                    print(f"   ⚠️  Error entering subject directly: {field_error}")
            
            # FALLBACK: Try keyboard navigation if direct entry failed
            if not subject_entered:
                print(f"   💡 Trying keyboard navigation method...")
                try:
                    actions = ActionChains(driver)
                    
                    # Click somewhere in compose to ensure focus
                    compose_dialog = driver.find_element(By.XPATH, "//div[@role='dialog']")
                    actions.move_to_element(compose_dialog).click().perform()
                    a_sleep(0.3)
                    
                    # Tab twice (past TO field to subject)
                    actions.send_keys(Keys.TAB).send_keys(Keys.TAB).perform()
                    a_sleep(0.4)
                    
                    # Type the subject
                    actions.send_keys(subject_text).perform()
                    a_sleep(0.3)
                    
                    print(f"   ✅ Subject entered via keyboard navigation")
                    subject_entered = True
                    
                except Exception as kb_error:
                    print(f"   ⚠️  Keyboard navigation failed: {kb_error}")
            
            # Final check - if still not entered, this is critical
            if not subject_entered:
                print(f"   ❌ CRITICAL: Could not enter subject with any method!")
                print(f"   ⚠️  Email will likely fail to send!")
                # Don't return False here - let it try to send and show proper error
                
        except Exception as e:
            print(f"   ⚠️  Subject step error: {str(e)}")
        
        print("   ✍️  Step 4: Writing message...")
        try:
            a_sleep(0.5)
            
            # Verify compose window is still open before proceeding
            try:
                compose_windows = driver.find_elements(By.XPATH, "//div[@role='dialog']")
                if not any(w.is_displayed() for w in compose_windows):
                    print("   ❌ Compose window closed before writing message!")
                    return False
            except:
                print("   ❌ Cannot access compose window")
                return False
            
            body_selectors = [
                "//div[@role='textbox' and @aria-label='Message Body']",
                "//div[@aria-label='Message Body']",
                "//div[@contenteditable='true' and @role='textbox']",
                "//div[@contenteditable='true'][@aria-label='Message Body']",
                "//div[@role='dialog']//div[@contenteditable='true']"
            ]
            
            body_field = None
            import time as _time
            end_time = _time.time() + 5
            while _time.time() < end_time and not body_field:
                for selector in body_selectors:
                    try:
                        elems = driver.find_elements(By.XPATH, selector)
                        for elem in elems:
                            if elem.is_displayed() and elem.is_enabled():
                                body_field = elem
                                break
                    except:
                        continue
                    if body_field:
                        break
                if not body_field:
                    a_sleep(0.5)
            
            # If still not found, try a more aggressive search
            if not body_field:
                print("   🔍 Body field not found with standard selectors, searching all editable divs...")
                try:
                    all_editable = driver.find_elements(By.XPATH, "//div[@contenteditable='true']")
                    for elem in all_editable:
                        if elem.is_displayed() and elem.is_enabled():
                            # Try to identify message body by checking if it's not subject or recipient
                            aria_label = elem.get_attribute('aria-label') or ''
                            if 'body' in aria_label.lower() or 'message' in aria_label.lower() or aria_label == '':
                                body_field = elem
                                print(f"   ✅ Found body field using fallback method")
                                break
                except:
                    pass
            
            if body_field:
                body_field.click()
                a_sleep(0.3)
                message = get_email_body_text(name)
                body_field.send_keys(message)
                print("   ✅ Message written!")
                a_sleep(0.5)
            else:
                print("   ❌ Could not find message body field with any selector")
                print("   💡 Trying last resort method...")
                
                # Last resort: try clicking and using keyboard navigation within the dialog
                try:
                    # Verify dialog still exists
                    compose_dialog = driver.find_element(By.XPATH, "//div[@role='dialog']")
                    
                    # Click somewhere safe in the dialog to ensure focus
                    from selenium.webdriver.common.action_chains import ActionChains
                    from selenium.webdriver.common.keys import Keys
                    
                    actions = ActionChains(driver)
                    
                    # Try clicking in the compose area
                    actions.move_to_element(compose_dialog).click().perform()
                    a_sleep(0.5)
                    
                    # Send Tab keys to navigate to body (from subject or recipient field)
                    actions.send_keys(Keys.TAB).send_keys(Keys.TAB).send_keys(Keys.TAB).perform()
                    a_sleep(0.3)
                    
                    message = get_email_body_text(name)
                    actions.send_keys(message).perform()
                    print("   ✅ Message written using keyboard navigation!")
                    a_sleep(0.5)
                except Exception as fallback_err:
                    print(f"   ❌ All methods failed: {fallback_err}")
                    print(f"   ⚠️  Cannot write message - email will not be sent")
                    return False
        except Exception as e:
            print(f"   ❌ Error writing message: {str(e)}")
            return False
        
        valid_brochures = get_valid_brochures()
        if valid_brochures:
            print("   📎 Step 5: Checking file attachments...")
            for brochure_path in valid_brochures:
                try:
                    # Check file size (Gmail limit is 25MB)
                    file_size_mb = os.path.getsize(brochure_path) / (1024 * 1024)
                    
                    if file_size_mb > 25:
                        print(f"   ⚠️  File too large ({file_size_mb:.1f} MB) - Gmail limit is 25MB")
                        print(f"   💡 Skipping attachment {os.path.basename(brochure_path)} to prevent send failure")
                    else:
                        print(f"   📄 File size: {file_size_mb:.2f} MB (within Gmail limit)")
                        attach_inputs = driver.find_elements(By.XPATH, "//input[@type='file']")
                        if attach_inputs:
                            attach_inputs[0].send_keys(os.path.abspath(brochure_path))
                            print(f"   ✅ Attached: {os.path.basename(brochure_path)}")
                            a_sleep(3)  # Give Gmail time to upload
                        else:
                            print(f"   ⚠️  Could not find file input field")
                except Exception as e:
                    print(f"   ⚠️  Could not attach file {os.path.basename(brochure_path)}: {str(e)}")
                    print(f"   💡 Continuing without attachment...")
        
        print("   🚀 Step 6: Sending email...")
        try:
            a_sleep(1)
            
            send_selectors = [
                "//div[@role='button' and @aria-label='Send ⌘Enter']",
                "//div[@role='button' and contains(@aria-label, 'Send')]",
                "//div[contains(@class, 'T-I') and contains(@class, 'J-J5-Ji')]",
                "//div[@role='button' and contains(., 'Send')]",
                "//*[@aria-label='Send ⌘Enter']",
                "//button[contains(text(), 'Send')]",
                "//*[contains(@data-tooltip, 'Send')]"
            ]
            
            send_clicked = False
            for selector in send_selectors:
                try:
                    send_buttons = driver.find_elements(By.XPATH, selector)
                    for send_button in send_buttons:
                        try:
                            if send_button.is_displayed() and send_button.is_enabled():
                                driver.execute_script("arguments[0].scrollIntoView(true);", send_button)
                                a_sleep(0.3)
                                
                                send_button.click()
                                print(f"   ✅ Clicked Send button!")
                                send_clicked = True
                                a_sleep(2)
                                break
                        except:
                            continue
                    if send_clicked:
                        break
                except Exception as e:
                    continue
            
            if not send_clicked:
                print(f"   💡 Send button not found, trying keyboard shortcut Ctrl+Enter...")
                from selenium.webdriver.common.keys import Keys
                from selenium.webdriver.common.action_chains import ActionChains
                
                actions = ActionChains(driver)
                actions.key_down(Keys.CONTROL).send_keys(Keys.RETURN).key_up(Keys.CONTROL)
                actions.perform()
                a_sleep(2)
                send_clicked = True
                print(f"   ✅ Sent using keyboard shortcut")
            
            print(f"   ⏳ Verifying email was sent...")
            a_sleep(2)
            
            email_sent = False
            error_message = None
            
            try:
                # First check for success confirmation
                confirmation_selectors = [
                    "//*[contains(text(), 'Message sent')]",
                    "//*[contains(text(), 'sent')]",
                    "//span[contains(text(), 'Message sent')]",
                    "//div[@role='alert']",
                    "//*[@aria-label='Message sent']"
                ]
                
                for conf_sel in confirmation_selectors:
                    try:
                        confirmations = driver.find_elements(By.XPATH, conf_sel)
                        if confirmations and any(c.is_displayed() for c in confirmations):
                            print(f"   ✅ Gmail confirmed: Message sent!")
                            email_sent = True
                            break
                    except:
                        continue
                
                if not email_sent:
                    compose_dialogs = driver.find_elements(By.XPATH, "//div[@role='dialog']")
                    visible_dialogs = [d for d in compose_dialogs if d.is_displayed()]
                    
                    if len(visible_dialogs) == 0:
                        print(f"   ✅ Compose window closed - email sent!")
                        email_sent = True
                    else:
                        print(f"   ⚠️  Compose window still open - checking for errors...")
                        
                        # Enhanced error detection - check for specific Gmail error messages
                        gmail_error_patterns = [
                            "Subject is required",
                            "subject",  # Sometimes it just highlights the field
                            "error",
                            "Error",
                            "failed",
                            "Failed",
                            "too large",
                            "size limit",
                            "couldn't send",
                            "not sent",
                            "invalid"
                        ]
                        
                        # Check for error messages in the compose window
                        for pattern in gmail_error_patterns:
                            try:
                                error_elems = visible_dialogs[0].find_elements(By.XPATH, f".//*[contains(text(), '{pattern}')]")
                                if error_elems:
                                    for elem in error_elems:
                                        if elem.is_displayed():
                                            error_text = elem.text.strip()
                                            if error_text:
                                                error_message = error_text
                                                print(f"   ❌ Gmail error detected: {error_text[:100]}")
                                                break
                                if error_message:
                                    break
                            except:
                                continue
                        
                        # Check for disabled send button (indicates validation error)
                        if not error_message:
                            try:
                                send_buttons = visible_dialogs[0].find_elements(By.XPATH, ".//div[@role='button' and contains(@aria-label, 'Send')]")
                                for btn in send_buttons:
                                    if btn.is_displayed():
                                        is_disabled = btn.get_attribute('aria-disabled') == 'true'
                                        if is_disabled:
                                            error_message = "Send button is disabled (validation error)"
                                            print(f"   ❌ {error_message}")
                                            break
                            except:
                                pass
                        
                        if not error_message:
                            # Generic error - something prevented sending
                            error_message = "Compose window did not close after send attempt"
                            print(f"   ❌ {error_message}")
                
            except Exception as verify_error:
                print(f"   ⚠️  Verification error: {verify_error}")
                # Don't assume sent if verification failed
            
            if not email_sent:
                print(f"   ❌ Email was NOT sent!")
                if error_message:
                    print(f"   📝 Reason: {error_message}")
                
                # RECOVERY: Close the failed compose window
                print(f"   🔧 Attempting to close failed compose window...")
                try:
                    from selenium.webdriver.common.keys import Keys
                    from selenium.webdriver.common.action_chains import ActionChains
                    
                    actions = ActionChains(driver)
                    # Press Escape multiple times to ensure window closes
                    for _ in range(3):
                        actions.send_keys(Keys.ESCAPE)
                    actions.perform()
                    a_sleep(1)
                    
                    # Verify closure
                    remaining_dialogs = driver.find_elements(By.XPATH, "//div[@role='dialog']")
                    visible_remaining = [d for d in remaining_dialogs if d.is_displayed()]
                    
                    if len(visible_remaining) == 0:
                        print(f"   ✅ Failed compose window closed successfully")
                    else:
                        print(f"   ⚠️  {len(visible_remaining)} dialog(s) still open - may need manual intervention")
                except Exception as close_error:
                    print(f"   ⚠️  Could not close window: {close_error}")
                
                return False
                
        except Exception as e:
            print(f"   ❌ Error sending email: {str(e)}")
            return False
        
        time_taken = time.time() - start_time
        print(f"✅ [Email] Message sent to {name}! (took {time_taken:.1f}s)")
        
        if analytics and ml_optimizer:
            analytics.record_send({
                'name': name,
                'email': to_email,
                'success': True,
                'time_taken': time_taken,
                'wait_time': 0,
                'priority_score': getattr(ml_optimizer.contact_prioritizer.score_contact(to_email, name), '__float__', lambda: 0)(),
                'engagement_prediction': ml_optimizer.get_engagement_prediction(to_email, name)['probability']
            })
        
        a_sleep(1)
        
        return True
        
    except Exception as e:
        time_taken = time.time() - start_time
        print(f"❌ [Email] Error sending to {name} ({to_email}): {str(e)}")
        
        if analytics:
            analytics.record_send({
                'name': name,
                'email': to_email,
                'success': False,
                'time_taken': time_taken,
                'error': str(e)
            })
        
        return False


