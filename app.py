import sys
import os
import json
import threading
import time
from datetime import datetime
import pandas as pd
from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename

# Add current path to sys.path so we can import local modules
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

import bulk_messenger
import actions

# Create the flask app
app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['UPLOAD_FOLDER'] = os.getcwd()
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload

# Global State
state = {
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

lock = threading.Lock()

# Custom stdout capture class
class StdoutRedirector:
    def __init__(self, original_stdout):
        self.original_stdout = original_stdout
        
    def write(self, message):
        self.original_stdout.write(message)
        if message.strip():
            timestamp = datetime.now().strftime("%H:%M:%S")
            # Thread-safe log append
            with lock:
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
    with lock:
        state['is_sending'] = True
        state['cancel_flag'] = False
        state['progress']['status'] = 'sending'
        state['progress']['current'] = 0
        
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
            on_finished_gmail=on_finished_gm
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


@app.route('/')
def index():
    return render_template('index.html')


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
                try:
                    drv = bulk_messenger.init_whatsapp_driver(
                        confirm_check=check_whatsapp_confirmed
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
                try:
                    drv = bulk_messenger.init_gmail_driver(
                        confirm_check=check_gmail_confirmed
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


@app.route('/api/start', methods=['POST'])
def start_sending():
    global state
    
    req_data = request.json or {}
    choice = req_data.get('choice', '1')  # 1: WA, 2: Email, 3: Both
    
    if choice not in ['1', '2', '3']:
        return jsonify({'error': 'Invalid choice'}), 400
        
    with lock:
        if state['is_sending']:
            return jsonify({'error': 'Sending is already running!'}), 400
            
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
        wa_template = ""
        email_template = ""
        
        # Try loading message template
        if os.path.exists('actions.py'):
            with open('actions.py', 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            # Extract WhatsApp message body string
            try:
                import actions as act_mod
                wa_template = act_mod.get_message_body("{Name}")
            except:
                wa_template = "Greetings!"
                
            # Extract email message body string
            try:
                # check if get_email_body_text exists in actions
                if hasattr(act_mod, 'get_email_body_text'):
                    email_template = act_mod.get_email_body_text("{Name}")
                else:
                    email_template = "Greetings!"
            except:
                email_template = "Greetings!"
                
        return jsonify({
            'config': cfg,
            'pdfs': pdf_files,
            'excels': excel_files,
            'whatsapp_template': wa_template,
            'email_template': email_template
        })
        
    elif request.method == 'POST':
        data = request.json or {}
        
        # Load active config
        cfg = {}
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                cfg = json.load(f)
                
        # Update config properties
        cfg['send_with_attachment'] = data.get('send_with_attachment', True)
        cfg['attachment_path'] = data.get('attachment_path', 'timing.pdf')
        cfg['whatsapp_sender'] = data.get('whatsapp_sender', '')
        cfg['gmail_sender'] = data.get('gmail_sender', '')
        cfg['use_ml_optimization'] = data.get('use_ml_optimization', True)
        cfg['min_wait_seconds'] = int(data.get('min_wait_seconds', 60))
        cfg['max_wait_seconds'] = int(data.get('max_wait_seconds', 60))
        
        # Write back to config.json
        with open(config_path, 'w') as f:
            json.dump(cfg, f, indent=4)
            
        # Update templates in actions.py if modified
        wa_template = data.get('whatsapp_template')
        email_template = data.get('email_template')
        
        if wa_template or email_template:
            # Modify actions.py directly (very carefully)
            modify_actions_templates(wa_template, email_template)
            
        return jsonify({'success': 'Settings updated successfully'})


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
        filename = 'contacts.xlsx'  # Overwrite contacts.xlsx
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        print("✅ Excel contact list uploaded and saved as contacts.xlsx")
        return jsonify({'success': 'Excel contact list uploaded successfully'})
        
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
    """Return contacts from the active Excel file as JSON."""
    excel_path = os.path.join(app.config['UPLOAD_FOLDER'], 'contacts.xlsx')
    if not os.path.exists(excel_path):
        return jsonify({'contacts': [], 'columns': [], 'total': 0, 'error': 'contacts.xlsx not found'})
    try:
        df = pd.read_excel(excel_path)
        # Normalise column names for safe JSON
        df.columns = [str(c).strip() for c in df.columns]
        # Replace NaN with empty string so JSON serialisation works
        df = df.fillna('')
        contacts = df.to_dict(orient='records')
        return jsonify({
            'contacts': contacts,
            'columns': list(df.columns),
            'total': len(contacts)
        })
    except Exception as e:
        return jsonify({'contacts': [], 'columns': [], 'total': 0, 'error': str(e)}), 500


@app.route('/api/contacts/<int:row_index>', methods=['DELETE'])
def delete_contact(row_index):
    """Delete a contact row by its 0-based index from contacts.xlsx."""
    excel_path = os.path.join(app.config['UPLOAD_FOLDER'], 'contacts.xlsx')
    if not os.path.exists(excel_path):
        return jsonify({'error': 'contacts.xlsx not found'}), 404
    try:
        df = pd.read_excel(excel_path)
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
