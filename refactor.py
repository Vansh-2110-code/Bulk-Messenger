import os

with open('bulk_messenger.py', 'r', encoding='utf-8') as f:
    code = f.read()

imports = """import pandas as pd
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

"""

def extract_block(code_str, start_marker, end_marker):
    start_idx = code_str.find(start_marker)
    if start_idx == -1: 
        print(f"Failed to find {start_marker}")
        return "", code_str
    
    if end_marker:
        end_idx = code_str.find(end_marker, start_idx)
        if end_idx == -1: 
            print(f"Failed to find end {end_marker}")
            end_idx = len(code_str)
    else:
        end_idx = len(code_str)
        
    block = code_str[start_idx:end_idx]
    new_code = code_str[:start_idx] + code_str[end_idx:]
    return block, new_code

# Extract globals
globals_block, code = extract_block(code, "BROCHURE_PATHS = [", "def get_message_body(name):")

msg_body_block, code = extract_block(code, "def get_message_body(name):", "def is_browser_alive(driver):")

is_alive_block, code = extract_block(code, "def is_browser_alive(driver):", "def init_whatsapp_driver():")

send_wa_block, code = extract_block(code, "def send_whatsapp_message(driver, phone, name, ml_optimizer=None):", "def clean_text_for_selenium(text):")

clean_text_block, code = extract_block(code, "def clean_text_for_selenium(text):", "def get_email_body_text(name):")

email_body_block, code = extract_block(code, "def get_email_body_text(name):", "def init_gmail_driver():")

close_windows_block, code = extract_block(code, "def close_all_compose_windows(driver):", "def send_email_via_browser(driver, to_email, name, ml_optimizer=None, analytics=None):")

send_email_block, code = extract_block(code, "def send_email_via_browser(driver, to_email, name, ml_optimizer=None, analytics=None):", "def read_contacts():")

# Assemble actions.py
actions_code = imports + globals_block + msg_body_block + is_alive_block + clean_text_block + email_body_block + close_windows_block + send_wa_block + send_email_block

with open('actions.py', 'w', encoding='utf-8') as f:
    f.write(actions_code)

# Rewrite bulk_messenger.py
code = "import actions\nimport importlib\n" + code

# Now in bulk_messenger.py, replace calls with actions.calls
code = code.replace("BROCHURE_PATHS", "actions.BROCHURE_PATHS")
code = code.replace("CC_RECIPIENTS", "actions.CC_RECIPIENTS")
code = code.replace("WHATSAPP_WAIT_TIME", "actions.WHATSAPP_WAIT_TIME")
code = code.replace("is_browser_alive", "actions.is_browser_alive")
code = code.replace("send_whatsapp_message", "actions.send_whatsapp_message")
code = code.replace("send_email_via_browser", "actions.send_email_via_browser")

loop_target = "print(f\"\\n--- Contact {index + 1}/{total_contacts}: {display_name} ---\")"
reload_logic = f"""print(f"\\n--- Contact {{index + 1}}/{{total_contacts}}: {{display_name}} ---")
        
        # 🔥 HOT RELOAD 🔥
        try:
            importlib.reload(actions)
        except Exception as e:
            print(f"⚠️  Hot reload failed: {{e}}")"""

code = code.replace(loop_target, reload_logic)

with open('bulk_messenger.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Refactored bulk_messenger.py into actions.py successfully.")
