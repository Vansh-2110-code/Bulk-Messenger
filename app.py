import sys
import os
import json
import threading
import time
from datetime import datetime
from functools import wraps
import pandas as pd
from flask import Flask, request, jsonify, render_template, send_from_directory, send_file, session, redirect, url_for
from werkzeug.utils import secure_filename


# --- COLUMN NORMALIZATION HELPER ---
# Maps any Excel column to a canonical Name / Phone / Email field.
_NAME_KEYWORDS   = ['name', 'company', 'organisation', 'organization', 'firm', 'client', 'customer', 'contact']
_PHONE_KEYWORDS  = ['phone', 'mobile', 'cell', 'tel', 'number', 'whatsapp', 'contact no', 'mob']
_EMAIL_KEYWORDS  = ['email', 'e-mail', 'mail', 'gmail', 'email id', 'mail id', 'emailid', 'mailid']

def _best_match(col_lower, keywords):
    """Return True if col_lower starts-with or contains any keyword."""
    for kw in keywords:
        if col_lower == kw or col_lower.startswith(kw) or kw in col_lower:
            return True
    return False

def normalize_contacts_df(df):
    """
    Given a DataFrame with arbitrary column names, produce a new DataFrame
    with exactly three columns: Name, Phone, Email.
    Columns are auto-detected by keyword matching; unrecognised columns are dropped.
    """
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    name_col  = None
    phone_col = None
    email_col = None

    for col in df.columns:
        cl = col.lower()
        if email_col is None and _best_match(cl, _EMAIL_KEYWORDS):
            email_col = col
        elif name_col is None and _best_match(cl, _NAME_KEYWORDS):
            name_col = col
        elif phone_col is None and _best_match(cl, _PHONE_KEYWORDS):
            phone_col = col

    # Build output with only the 3 standard columns
    result = pd.DataFrame()
    result['Name']  = df[name_col].fillna('')  if name_col  else ''
    result['Phone'] = df[phone_col].fillna('') if phone_col else ''
    result['Email'] = df[email_col].fillna('') if email_col else ''

    # Stringify everything so JSON serialisation is safe
    for col in result.columns:
        result[col] = result[col].astype(str).replace('nan', '').replace('None', '')

    return result

# Add current path to sys.path so we can import local modules
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

import bulk_messenger
import actions
from db import db_manager

# Create the flask app
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.environ.get('SECRET_KEY', 'bulk_messenger_secret_key_2026')
app.config['UPLOAD_FOLDER'] = os.getcwd()
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload

# Global State
state = {
    'current_user': None,
    'whatsapp_driver': None,
    'gmail_driver': None,
    'sending_thread': None,
    'is_sending': False,
    'cancel_flag': False,
    'logs': [],
    'login_status': {
        'whatsapp': 'idle',  # 'idle', 'waiting', 'confirmed'
        'gmail': 'idle'
    },
    'login_confirmed': {
        'whatsapp': False,
        'gmail': False
    },
    'progress': {
        'current': 0,
        'total': 0,
        'name': '',
        'email': '',
        'phone': '',
        'status': 'idle',  # 'idle', 'sending', 'completed', 'cancelled'
        'whatsapp_success': 0,
        'email_success': 0
    }
}

# Use RLock for application state so re-entrant calls never deadlock
lock = threading.RLock()
log_lock = threading.Lock()

# Custom stdout capture class
class StdoutRedirector:
    def __init__(self, original_stdout):
        self.original_stdout = original_stdout
        
    def write(self, message):
        self.original_stdout.write(message)
        if message.strip():
            timestamp = datetime.now().strftime("%H:%M:%S")
            # Thread-safe log append using separate lock to prevent state deadlocks
            with log_lock:
                state['logs'].append(f"[{timestamp}] {message.strip()}")
                # Keep logs bounded
                if len(state['logs']) > 1000:
                    state['logs'] = state['logs'][-1000:]
                    
    def flush(self):
        self.original_stdout.flush()

# Redirect stdout globally
sys.stdout = StdoutRedirector(sys.stdout)


def check_cancel():
    with lock:
        return state['cancel_flag']


def check_gmail_confirmed():
    with lock:
        return state['login_confirmed']['gmail']


def check_whatsapp_confirmed():
    with lock:
        return state['login_confirmed']['whatsapp']


def update_progress(p_dict):
    with lock:
        state['progress'].update(p_dict)


def run_sender_thread(choice):
    global state
    
    use_whatsapp = choice in ['1', '3']
    use_email = choice in ['2', '3']
    
    # Check browser health outside the lock
    wa_drv = None
    gm_drv = None
    with lock:
        wa_drv = state['whatsapp_driver']
        gm_drv = state['gmail_driver']

    if use_whatsapp and wa_drv and not actions.is_browser_alive(wa_drv):
        wa_drv = None
        
    if use_email and gm_drv and not actions.is_browser_alive(gm_drv):
        gm_drv = None

    with lock:
        state['is_sending'] = True
        state['cancel_flag'] = False
        state['progress']['status'] = 'sending'
        state['progress']['current'] = 0
        state['whatsapp_driver'] = wa_drv
        state['gmail_driver'] = gm_drv
        
    print(f"🎬 Starting background sender process (Mode: {choice})...")
    
    # Define callbacks for driver initialization
    def on_waiting_wa():
        with lock:
            state['login_status']['whatsapp'] = 'waiting'
            state['login_confirmed']['whatsapp'] = False
            
    def on_finished_wa():
        with lock:
            state['login_status']['whatsapp'] = 'idle'
            state['login_confirmed']['whatsapp'] = False
            
    def on_waiting_gm():
        with lock:
            state['login_status']['gmail'] = 'waiting'
            state['login_confirmed']['gmail'] = False
            
    def on_finished_gm():
        with lock:
            state['login_status']['gmail'] = 'idle'
            state['login_confirmed']['gmail'] = False

    def check_wa_confirmed():
        with lock:
            return state['login_confirmed']['whatsapp']
            
    def check_gm_confirmed():
        with lock:
            return state['login_confirmed']['gmail']
            
    try:
        success, wa_drv, gm_drv = bulk_messenger.run_sending_process(
            choice=choice,
            whatsapp_driver=state['whatsapp_driver'],
            gmail_driver=state['gmail_driver'],
            progress_callback=update_progress,
            cancel_check=check_cancel,
            confirm_check_whatsapp=check_wa_confirmed,
            confirm_check_gmail=check_gm_confirmed,
            on_waiting_whatsapp=on_waiting_wa,
            on_finished_whatsapp=on_finished_wa,
            on_waiting_gmail=on_waiting_gm,
            on_finished_gmail=on_finished_gm,
            username=state.get('current_user')
        )
        
        with lock:
            state['whatsapp_driver'] = wa_drv
            state['gmail_driver'] = gm_drv
            if state['cancel_flag']:
                state['progress']['status'] = 'cancelled'
            else:
                state['progress']['status'] = 'completed'
                
    except Exception as e:
        print(f"❌ Error in sender thread: {str(e)}")
        with lock:
            state['progress']['status'] = 'error'
            
    finally:
        with lock:
            state['is_sending'] = False
            state['sending_thread'] = None


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
@login_required
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.json or {}
        username = data.get('username', '')
        password = data.get('password', '')
        success, authenticated_user = db_manager.authenticate_user(username, password)
        if success:
            session['username'] = authenticated_user
            return jsonify({'success': True, 'redirect': '/'})
        return jsonify({'success': False, 'message': 'Invalid username or password.'}), 401
    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        data = request.json or {}
        username = data.get('username', '')
        password = data.get('password', '')
        success, message = db_manager.create_user(username, password)
        if success:
            return jsonify({'success': True, 'message': message, 'redirect': '/login'})
        return jsonify({'success': False, 'message': message}), 400
    return render_template('signup.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/api/user_info', methods=['GET'])
def get_user_info():
    if 'username' in session:
        return jsonify({'logged_in': True, 'username': session['username']})
    return jsonify({'logged_in': False})


@app.route('/api/mail_history', methods=['GET'])
@login_required
def get_mail_history():
    username = session.get('username')
    emails = db_manager.get_user_sent_emails(username=username)
    return jsonify({'success': True, 'emails': emails})


@app.route('/api/history/export', methods=['GET'])
@login_required
def export_history():
    """Export sent emails history as an Excel file."""
    username = session.get('username')
    emails = db_manager.get_user_sent_emails(username=username, limit=5000)
    
    if not emails:
        return jsonify({'error': 'No sent email records to export'}), 400
        
    try:
        import io
        df = pd.DataFrame(emails)
        
        column_mapping = {
            'username': 'Username',
            'sender_email': 'Sender Email',
            'recipient_name': 'Recipient Name',
            'recipient_email': 'Recipient Email',
            'subject': 'Subject',
            'status': 'Status',
            'error_message': 'Error Message',
            'timestamp': 'Timestamp'
        }
        df = df.rename(columns=column_mapping)
        
        cols_order = ['Timestamp', 'Username', 'Sender Email', 'Recipient Name', 'Recipient Email', 'Subject', 'Status', 'Error Message']
        existing_cols = [c for c in cols_order if c in df.columns]
        df = df[existing_cols]
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Sent Emails History')
        output.seek(0)
        
        filename = f"sent_emails_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        return jsonify({'error': f"Failed to generate Excel file: {str(e)}"}), 500


@app.route('/api/status', methods=['GET'])
def get_status():
    # Check if browsers are still alive
    wa_alive = False
    gm_alive = False
    with lock:
        if state['whatsapp_driver']:
            try:
                wa_alive = actions.is_browser_alive(state['whatsapp_driver'])
            except:
                pass
        if state['gmail_driver']:
            try:
                gm_alive = actions.is_browser_alive(state['gmail_driver'])
            except:
                pass
                
    return jsonify({
        'is_sending': state['is_sending'],
        'whatsapp_browser_active': wa_alive,
        'gmail_browser_active': gm_alive,
        'progress': state['progress'],
        'login_status': state['login_status']
    })


@app.route('/api/logs', methods=['GET'])
def get_logs():
    with lock:
        return jsonify({
            'logs': state['logs']
        })


@app.route('/api/login/<service>', methods=['POST'])
def launch_login(service):
    global state
    
    if service not in ['whatsapp', 'gmail']:
        return jsonify({'error': 'Invalid service'}), 400
        
    with lock:
        if state['is_sending']:
            return jsonify({'error': 'Cannot configure browser while sending task is active'}), 400
            
    try:
        if service == 'whatsapp':
            print("🚀 Launching WhatsApp login browser session...")
            def open_wa():
                with lock:
                    state['login_status']['whatsapp'] = 'waiting'
                    state['login_confirmed']['whatsapp'] = False
                def set_wa_drv(d):
                    with lock:
                        state['whatsapp_driver'] = d
                try:
                    drv = bulk_messenger.init_whatsapp_driver(
                        confirm_check=check_whatsapp_confirmed,
                        on_driver_created=set_wa_drv
                    )
                    with lock:
                        state['whatsapp_driver'] = drv
                except Exception as ex:
                    print(f"❌ Failed to init WhatsApp driver: {ex}")
                finally:
                    with lock:
                        state['login_status']['whatsapp'] = 'idle'
                        state['login_confirmed']['whatsapp'] = False
            threading.Thread(target=open_wa, daemon=True).start()
            
        elif service == 'gmail':
            print("🚀 Launching Gmail login browser session...")
            def open_gm():
                with lock:
                    state['login_status']['gmail'] = 'waiting'
                    state['login_confirmed']['gmail'] = False
                def set_gm_drv(d):
                    with lock:
                        state['gmail_driver'] = d
                try:
                    drv = bulk_messenger.init_gmail_driver(
                        confirm_check=check_gmail_confirmed,
                        on_driver_created=set_gm_drv
                    )
                    with lock:
                        state['gmail_driver'] = drv
                except Exception as ex:
                    print(f"❌ Failed to init Gmail driver: {ex}")
                finally:
                    with lock:
                        state['login_status']['gmail'] = 'idle'
                        state['login_confirmed']['gmail'] = False
            threading.Thread(target=open_gm, daemon=True).start()
            
        return jsonify({'success': f'Launching {service} driver'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/confirm-login/<service>', methods=['POST'])
def confirm_login(service):
    """Manually signal that login in the Chrome window is complete."""
    if service not in ['whatsapp', 'gmail']:
        return jsonify({'error': 'Invalid service'}), 400
    with lock:
        if state['login_status'][service] != 'waiting':
            return jsonify({'error': f'{service} login is not currently in progress'}), 400
        state['login_confirmed'][service] = True
        state['login_status'][service] = 'confirmed'
    print(f"✅ [{service.title()}] Login manually confirmed by user.")
    return jsonify({'success': f'{service} login confirmed'})


@app.route('/api/screenshot/<service>', methods=['GET'])
def get_screenshot(service):
    if service not in ['whatsapp', 'gmail']:
        return jsonify({'error': 'Invalid service'}), 400
    try:
        driver = None
        with lock:
            if service == 'whatsapp':
                driver = state['whatsapp_driver']
            elif service == 'gmail':
                driver = state['gmail_driver']
        
        if driver and actions.is_browser_alive(driver):
            screenshot_bin = driver.get_screenshot_as_png()
            import io
            return send_file(io.BytesIO(screenshot_bin), mimetype='image/png')
        else:
            return jsonify({'error': 'Driver not active'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/click/<service>', methods=['POST'])
def click_coordinates(service):
    if service not in ['whatsapp', 'gmail']:
        return jsonify({'error': 'Invalid service'}), 400
    try:
        data = request.json
        x = int(data.get('x', 0))
        y = int(data.get('y', 0))
        img_width = int(data.get('width', 1))
        img_height = int(data.get('height', 1))
        
        driver = None
        with lock:
            if service == 'whatsapp':
                driver = state['whatsapp_driver']
            elif service == 'gmail':
                driver = state['gmail_driver']
                
        if driver and actions.is_browser_alive(driver):
            # Scale coordinates
            window_size = driver.get_window_size()
            win_width = window_size['width']
            win_height = window_size['height']
            
            scaled_x = int((x / img_width) * win_width)
            scaled_y = int((y / img_height) * win_height)
            
            # Click via JS
            click_js = """
            var el = document.elementFromPoint(arguments[0], arguments[1]);
            if (el) {
                el.click();
                if (el.focus) { el.focus(); }
                return true;
            }
            return false;
            """
            success = driver.execute_script(click_js, scaled_x, scaled_y)
            return jsonify({'success': success, 'x': scaled_x, 'y': scaled_y})
        return jsonify({'error': 'Driver not active'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/send-keys/<service>', methods=['POST'])
def send_keys(service):
    if service not in ['whatsapp', 'gmail']:
        return jsonify({'error': 'Invalid service'}), 400
    try:
        data = request.json
        text = data.get('text', '')
        special_key = data.get('key', '')
        
        driver = None
        with lock:
            if service == 'whatsapp':
                driver = state['whatsapp_driver']
            elif service == 'gmail':
                driver = state['gmail_driver']
                
        if driver and actions.is_browser_alive(driver):
            active_element = driver.switch_to.active_element
            if special_key:
                from selenium.webdriver.common.keys import Keys
                if special_key == 'Enter':
                    active_element.send_keys(Keys.ENTER)
                elif special_key == 'Tab':
                    active_element.send_keys(Keys.TAB)
                elif special_key == 'Backspace':
                    active_element.send_keys(Keys.BACKSPACE)
                elif special_key == 'Escape':
                    active_element.send_keys(Keys.ESCAPE)
            else:
                active_element.send_keys(text)
            return jsonify({'success': True})
        return jsonify({'error': 'Driver not active'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/navigate/<service>', methods=['POST'])
def navigate_to_url(service):
    if service not in ['whatsapp', 'gmail']:
        return jsonify({'error': 'Invalid service'}), 400
    try:
        data = request.json
        url = data.get('url', '')
        if not url:
            return jsonify({'error': 'URL is required'}), 400
            
        driver = None
        with lock:
            if service == 'whatsapp':
                driver = state['whatsapp_driver']
            elif service == 'gmail':
                driver = state['gmail_driver']
                
        if driver and actions.is_browser_alive(driver):
            driver.get(url)
            return jsonify({'success': True})
        return jsonify({'error': 'Driver not active'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/start', methods=['POST'])
@login_required
def start_sending():
    global state
    
    req_data = request.json or {}
    choice = req_data.get('choice', '1')  # 1: WA, 2: Email, 3: Both
    
    if choice not in ['1', '2', '3']:
        return jsonify({'error': 'Invalid choice'}), 400
        
    with lock:
        if state['is_sending']:
            return jsonify({'error': 'Sending is already running!'}), 400
            
        state['current_user'] = session.get('username')
        state['cancel_flag'] = False
        state['sending_thread'] = threading.Thread(target=run_sender_thread, args=(choice,))
        state['sending_thread'].start()
        
    return jsonify({'success': 'Sending thread started'})


@app.route('/api/stop', methods=['POST'])
def stop_sending():
    global state
    
    with lock:
        if not state['is_sending']:
            return jsonify({'error': 'No sending process active'}), 400
        state['cancel_flag'] = True
        
    print("🛑 Stop request received. Aborting sending loop...")
    return jsonify({'success': 'Aborting sent command'})


@app.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    config_path = 'config.json'
    
    if request.method == 'GET':
        cfg = {}
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                cfg = json.load(f)
                
        # Read available files
        pdf_files = [f for f in os.listdir('.') if f.endswith('.pdf')]
        excel_files = [f for f in os.listdir('.') if f.endswith('.xlsx') or f.endswith('.xls')]
        
        # Read message templates
        wa_template = cfg.get('whatsapp_template', '')
        if not wa_template and os.path.exists('actions.py'):
            try:
                import actions as act_mod
                wa_template = act_mod.get_message_body("{Name}")
            except:
                wa_template = "Greetings!"
                
        email_template = cfg.get('email_template', '')
        if not email_template and os.path.exists('actions.py'):
            try:
                import actions as act_mod
                if hasattr(act_mod, 'get_email_body_text'):
                    email_template = act_mod.get_email_body_text("{Name}")
                else:
                    email_template = "Greetings!"
            except:
                email_template = "Greetings!"
                
        email_subject = cfg.get('email_subject', '')
        if not email_subject and os.path.exists('actions.py'):
            try:
                import actions as act_mod
                if hasattr(act_mod, 'get_email_subject'):
                    email_subject = act_mod.get_email_subject("{Name}")
            except:
                email_subject = ""
                
        email_cc = cfg.get('email_cc', '')
                
        return jsonify({
            'config': cfg,
            'pdfs': pdf_files,
            'excels': excel_files,
            'whatsapp_template': wa_template,
            'email_template': email_template,
            'email_subject': email_subject,
            'email_cc': email_cc
        })
        
    elif request.method == 'POST':
        data = request.json or {}
        
        # Load active config
        cfg = {}
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                cfg = json.load(f)
                
        # Update config properties dynamically
        if 'send_with_attachment' in data:
            cfg['send_with_attachment'] = data['send_with_attachment']
        if 'attachment_path' in data:
            cfg['attachment_path'] = data['attachment_path']
        if 'whatsapp_sender' in data:
            cfg['whatsapp_sender'] = data['whatsapp_sender']
        if 'gmail_sender' in data:
            cfg['gmail_sender'] = data['gmail_sender']
        if 'gmail_app_password' in data:
            cfg['gmail_app_password'] = data['gmail_app_password']
        if 'use_ml_optimization' in data:
            cfg['use_ml_optimization'] = data['use_ml_optimization']
        if 'min_wait_seconds' in data:
            cfg['min_wait_seconds'] = int(data['min_wait_seconds'])
        if 'max_wait_seconds' in data:
            cfg['max_wait_seconds'] = int(data['max_wait_seconds'])
        if 'whatsapp_template' in data:
            cfg['whatsapp_template'] = data['whatsapp_template']
        if 'email_template' in data:
            cfg['email_template'] = data['email_template']
        if 'email_subject' in data:
            cfg['email_subject'] = data['email_subject']
        if 'email_cc' in data:
            cfg['email_cc'] = data['email_cc']
            
        # Write back to config.json
        with open(config_path, 'w') as f:
            json.dump(cfg, f, indent=4)
            
        return jsonify({'success': 'Settings updated successfully'})


@app.route('/api/verify-email', methods=['POST'])
def verify_email_connection():
    try:
        data = request.json or {}
        sender_email = data.get('gmail_sender', '')
        app_password = data.get('gmail_app_password', '')
        
        # Fallback to config.json if not provided
        if not sender_email or not app_password:
            config_path = 'config.json'
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    cfg = json.load(f)
                sender_email = sender_email or cfg.get('gmail_sender', '')
                app_password = app_password or cfg.get('gmail_app_password', '')
                
        if not sender_email or not app_password:
            return jsonify({'error': 'Gmail ID or App Password is not provided'}), 400
            
        import smtplib
        clean_password = app_password.replace(" ", "")
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=15)
        try:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(sender_email, clean_password)
        finally:
            try:
                server.quit()
            except Exception:
                try:
                    server.close()
                except Exception:
                    pass
        
        return jsonify({'success': 'Email connection verified successfully!'})
    except Exception as e:
        return jsonify({'error': f'Verification failed: {str(e)}'}), 500


@app.route('/api/verify-recipient-emails', methods=['POST'])
def verify_recipient_emails():
    excel_path = os.path.join(app.config['UPLOAD_FOLDER'], 'contacts.xlsx')
    if not os.path.exists(excel_path):
        return jsonify({'error': 'No contacts Excel list uploaded yet'}), 400
        
    try:
        df = pd.read_excel(excel_path)
        df.columns = [str(c).strip() for c in df.columns]
        
        email_col = None
        for col in df.columns:
            if col.lower() == 'email':
                email_col = col
                break
                
        if not email_col:
            return jsonify({'error': "Contacts list does not contain an 'Email' column"}), 400
            
        import verify_emails
        results = []
        for index, row in df.iterrows():
            email_val = str(row[email_col]).strip() if not pd.isna(row[email_col]) else ''
            name_val = str(row.get('Name', row.get('name', f'Row {index + 1}'))).strip()
            
            if not email_val:
                results.append({
                    'index': index,
                    'name': name_val,
                    'email': '',
                    'valid': False,
                    'reason': 'Email is empty'
                })
            else:
                res = verify_emails.verify_single_email(email_val)
                results.append({
                    'index': index,
                    'name': name_val,
                    'email': email_val,
                    'valid': res['valid'],
                    'reason': res['reason']
                })
                
        return jsonify({'success': True, 'results': results})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def modify_actions_templates(wa_template, email_template):
    if not os.path.exists('actions.py'):
        return
        
    with open('actions.py', 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
        
    # We will look for def get_message_body(name): and def get_email_body_text(name):
    # and rewrite them dynamically
    code = "".join(lines)
    
    # Simple search & replace or rewrite. Since templates can contain multi-line text, 
    # we can construct functions dynamically:
    # A cleaner approach is to have actions.py read message bodies from config.json!
    # Wait! If we edit actions.py to read greetings from config.json, we solve this permanently 
    # and cleanly without fragile string-replacements!
    # Let's verify how actions.py currently defines get_message_body and get_email_body_text.
    pass


@app.route('/api/upload/contacts', methods=['POST'])
def upload_contacts():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    if file and (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
        try:
            # Read raw Excel into DataFrame
            df_raw = pd.read_excel(file)
            # Normalize to Name / Phone / Email only
            df_norm = normalize_contacts_df(df_raw)
            # Save as canonical contacts.xlsx
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], 'contacts.xlsx')
            df_norm.to_excel(save_path, index=False)
            print(f"✅ Excel uploaded and normalized → {len(df_norm)} rows | columns: Name, Phone, Email")
            return jsonify({'success': 'Excel contact list uploaded and normalized successfully', 'rows': len(df_norm)})
        except Exception as e:
            print(f"❌ Error processing uploaded Excel: {e}")
            return jsonify({'error': f'Failed to process Excel file: {str(e)}'}), 500

    return jsonify({'error': 'Invalid file format. Only Excel files (.xlsx) allowed.'}), 400


@app.route('/api/upload/attachment', methods=['POST'])
def upload_attachment():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400
        
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Save path in config.json
        config_path = 'config.json'
        cfg = {}
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                cfg = json.load(f)
                
        cfg['attachment_path'] = filename
        cfg['send_with_attachment'] = True
        
        with open(config_path, 'w') as f:
            json.dump(cfg, f, indent=4)
            
        print(f"✅ Attachment file uploaded and set in config: {filename}")
        return jsonify({'success': f'File {filename} uploaded successfully'})
        
    return jsonify({'error': 'Upload failed'}), 400


@app.route('/api/contacts', methods=['GET'])
def get_contacts():
    """Return contacts from the active Excel file as JSON (always Name / Phone / Email)."""
    excel_path = os.path.join(app.config['UPLOAD_FOLDER'], 'contacts.xlsx')
    if not os.path.exists(excel_path):
        return jsonify({'contacts': [], 'columns': [], 'total': 0, 'error': 'contacts.xlsx not found'})
    try:
        df = pd.read_excel(excel_path)
        # Normalize to the 3 standard columns so the UI always shows Name / Phone / Email
        df = normalize_contacts_df(df)
        contacts = df.to_dict(orient='records')
        return jsonify({
            'contacts': contacts,
            'columns': list(df.columns),   # Always ['Name', 'Phone', 'Email']
            'total': len(contacts)
        })
    except Exception as e:
        return jsonify({'contacts': [], 'columns': [], 'total': 0, 'error': str(e)}), 500


@app.route('/api/contacts', methods=['POST'])
def add_contact():
    """Add a new contact to contacts.xlsx (always uses Name / Phone / Email columns)."""
    excel_path = os.path.join(app.config['UPLOAD_FOLDER'], 'contacts.xlsx')
    data = request.json or {}
    try:
        if os.path.exists(excel_path):
            df = pd.read_excel(excel_path)
            df = normalize_contacts_df(df)
        else:
            df = pd.DataFrame(columns=['Name', 'Phone', 'Email'])

        # Accept incoming keys case-insensitively mapped to standard column names
        new_row = {
            'Name':  data.get('Name',  data.get('name',  '')),
            'Phone': data.get('Phone', data.get('phone', '')),
            'Email': data.get('Email', data.get('email', '')),
        }

        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_excel(excel_path, index=False)
        print(f"✅ Added contact: {new_row.get('Name', 'Unknown')} to contacts.xlsx")
        return jsonify({'success': True, 'total': len(df)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/contacts/<int:row_index>', methods=['PUT'])
def update_contact(row_index):
    """Update an existing contact row by its 0-based index in contacts.xlsx."""
    excel_path = os.path.join(app.config['UPLOAD_FOLDER'], 'contacts.xlsx')
    if not os.path.exists(excel_path):
        return jsonify({'error': 'contacts.xlsx not found'}), 404
    data = request.json or {}
    try:
        df = pd.read_excel(excel_path)
        df = normalize_contacts_df(df)
        if row_index < 0 or row_index >= len(df):
            return jsonify({'error': 'Row index out of range'}), 400

        for col in ['Name', 'Phone', 'Email']:
            if col in data:
                df.at[row_index, col] = data[col]
            elif col.lower() in data:
                df.at[row_index, col] = data[col.lower()]

        df.to_excel(excel_path, index=False)
        print(f"✅ Updated contact at row {row_index} in contacts.xlsx")
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/contacts/export', methods=['GET'])
def export_contacts():
    """Export and download contacts.xlsx file."""
    excel_path = os.path.join(app.config['UPLOAD_FOLDER'], 'contacts.xlsx')
    if not os.path.exists(excel_path):
        return jsonify({'error': 'contacts.xlsx not found'}), 404
    return send_file(excel_path, as_attachment=True, download_name='contacts_exported.xlsx')


@app.route('/api/contacts/<int:row_index>', methods=['DELETE'])
def delete_contact(row_index):
    """Delete a contact row by its 0-based index from contacts.xlsx."""
    excel_path = os.path.join(app.config['UPLOAD_FOLDER'], 'contacts.xlsx')
    if not os.path.exists(excel_path):
        return jsonify({'error': 'contacts.xlsx not found'}), 404
    try:
        df = pd.read_excel(excel_path)
        df = normalize_contacts_df(df)
        if row_index < 0 or row_index >= len(df):
            return jsonify({'error': 'Row index out of range'}), 400
        df = df.drop(index=row_index).reset_index(drop=True)
        df.to_excel(excel_path, index=False)
        print(f"✅ Deleted contact at row {row_index} from contacts.xlsx")
        return jsonify({'success': True, 'remaining': len(df)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Disable reload to prevent double startup and driver issues
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
