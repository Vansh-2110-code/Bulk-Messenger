import re

with open('bulk_messenger.py', 'r', encoding='utf-8') as f:
    code = f.read()

# I want to inject the a_sleep function at the beginning of send_email_via_browser
def_email = "def send_email_via_browser(driver, to_email, name, ml_optimizer=None, analytics=None):"
email_start = code.find(def_email)
if email_start != -1:
    email_end = code.find("def read_contacts():", email_start)
    if email_end == -1:
        email_end = len(code)
    
    email_block = code[email_start:email_end]
    
    # inject the sub-function
    injection = """def send_email_via_browser(driver, to_email, name, ml_optimizer=None, analytics=None):
    def a_sleep(secs):
        if ml_optimizer and hasattr(ml_optimizer, 'get_action_delay'):
            import time as _time
            _time.sleep(ml_optimizer.get_action_delay(secs))
        else:
            import time as _time
            _time.sleep(secs)
"""
    email_block = email_block.replace(def_email, injection)
    # Be careful not to replace `time.sleep` inside the injected `a_sleep` function!
    # The injection already uses `_time.sleep`, so `time.sleep` can be safely replaced everywhere else.
    email_block = email_block.replace("time.sleep(", "a_sleep(")
    
    # put back in code
    code = code[:email_start] + email_block + code[email_end:]

# Now do the same for send_whatsapp_message
def_wa = "def send_whatsapp_message(driver, phone, name, ml_optimizer=None):"
wa_start = code.find(def_wa)
if wa_start != -1:
    wa_end = code.find("def clean_text_for_selenium(", wa_start)
    if wa_end == -1:
        wa_end = len(code)
    
    wa_block = code[wa_start:wa_end]
    
    injection_wa = """def send_whatsapp_message(driver, phone, name, ml_optimizer=None):
    def a_sleep(secs):
        if ml_optimizer and hasattr(ml_optimizer, 'get_action_delay'):
            import time as _time
            _time.sleep(ml_optimizer.get_action_delay(secs))
        else:
            import time as _time
            _time.sleep(secs)
"""
    wa_block = wa_block.replace(def_wa, injection_wa)
    wa_block = wa_block.replace("time.sleep(", "a_sleep(")
    
    code = code[:wa_start] + wa_block + code[wa_end:]

with open('bulk_messenger.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Successfully replaced time.sleep with a_sleep in send functions.")
