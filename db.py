import os
import json
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# Try importing pymongo
try:
    import pymongo
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False

class DatabaseManager:
    def __init__(self):
        self.mongo_client = None
        self.mongo_db = None
        self.use_mongo = False
        self.sqlite_path = os.path.join(os.path.dirname(__file__), 'messenger.db')
        self._init_db()

    def _get_mongo_uri(self):
        mongo_uri = os.environ.get('MONGO_URI', '')
        if not mongo_uri:
            config_path = os.path.join(os.path.dirname(__file__), 'config.json')
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        mongo_uri = config.get('mongo_uri', '').strip()
                except Exception as e:
                    print(f"[DB] Error loading config.json: {e}")
        return mongo_uri

    def _init_db(self):
        mongo_uri = self._get_mongo_uri()
        if PYMONGO_AVAILABLE and mongo_uri:
            try:
                print(f"[DB] Attempting MongoDB connection...")
                self.mongo_client = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
                # Test connection
                self.mongo_client.admin.command('ping')
                self.mongo_db = self.mongo_client['bulk_messenger']
                self.use_mongo = True
                print("[DB] Connected successfully to MongoDB!")
                self.create_user("demo", "demo123")
                return
            except Exception as e:
                print(f"[DB] MongoDB connection failed ({e}). Falling back to SQLite.")
                self.use_mongo = False

        # Fallback SQLite Initialization
        print(f"[DB] Initializing SQLite database at {self.sqlite_path}")
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sent_emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                sender_email TEXT,
                recipient_name TEXT,
                recipient_email TEXT NOT NULL,
                subject TEXT,
                status TEXT NOT NULL,
                error_message TEXT,
                timestamp TEXT NOT NULL
            )
        ''')
        conn.commit()
        conn.close()

        # Seed default demo account
        self.create_user("demo", "demo123")

    def create_user(self, username, password):
        username = username.strip().lower()
        if not username or not password:
            return False, "Username and password are required."
        
        pwd_hash = generate_password_hash(password)
        created_at = datetime.now().isoformat()

        if self.use_mongo:
            try:
                users = self.mongo_db['users']
                if users.find_one({'username': username}):
                    return False, "Username already exists."
                users.insert_one({
                    'username': username,
                    'password_hash': pwd_hash,
                    'created_at': created_at
                })
                return True, "User registered successfully."
            except Exception as e:
                return False, f"Database error: {str(e)}"
        else:
            try:
                conn = sqlite3.connect(self.sqlite_path)
                cursor = conn.cursor()
                cursor.execute('INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)',
                               (username, pwd_hash, created_at))
                conn.commit()
                conn.close()
                return True, "User registered successfully."
            except sqlite3.IntegrityError:
                return False, "Username already exists."
            except Exception as e:
                return False, f"Database error: {str(e)}"

    def authenticate_user(self, username, password):
        username = username.strip().lower()
        if not username or not password:
            return False, None

        if self.use_mongo:
            try:
                users = self.mongo_db['users']
                user = users.find_one({'username': username})
                if user and check_password_hash(user['password_hash'], password):
                    return True, user['username']
            except Exception as e:
                print(f"[DB] Auth error: {e}")
        else:
            try:
                conn = sqlite3.connect(self.sqlite_path)
                cursor = conn.cursor()
                cursor.execute('SELECT username, password_hash FROM users WHERE username = ?', (username,))
                row = cursor.fetchone()
                conn.close()
                if row and check_password_hash(row[1], password):
                    return True, row[0]
            except Exception as e:
                print(f"[DB] Auth error: {e}")
        return False, None

    def record_sent_email(self, username, sender_email, recipient_name, recipient_email, subject, status, error_message=''):
        timestamp = datetime.now().isoformat()
        if self.use_mongo:
            try:
                records = self.mongo_db['sent_emails']
                records.insert_one({
                    'username': username,
                    'sender_email': sender_email,
                    'recipient_name': recipient_name,
                    'recipient_email': recipient_email,
                    'subject': subject,
                    'status': status,
                    'error_message': error_message,
                    'timestamp': timestamp
                })
            except Exception as e:
                print(f"[DB] Error logging sent email to Mongo: {e}")
        else:
            try:
                conn = sqlite3.connect(self.sqlite_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO sent_emails (username, sender_email, recipient_name, recipient_email, subject, status, error_message, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (username, sender_email, recipient_name, recipient_email, subject, status, error_message, timestamp))
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"[DB] Error logging sent email to SQLite: {e}")

    def get_user_sent_emails(self, username=None, limit=100):
        records = []
        if self.use_mongo:
            try:
                query = {'username': {'$regex': f'^{username}$', '$options': 'i'}} if username else {}
                cursor = self.mongo_db['sent_emails'].find(query, {'_id': 0}).sort('timestamp', -1).limit(limit)
                records = list(cursor)
            except Exception as e:
                print(f"[DB] Error querying Mongo: {e}")
        else:
            try:
                conn = sqlite3.connect(self.sqlite_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                if username:
                    cursor.execute('SELECT username, sender_email, recipient_name, recipient_email, subject, status, error_message, timestamp FROM sent_emails WHERE LOWER(username) = LOWER(?) ORDER BY timestamp DESC LIMIT ?', (username, limit))
                else:
                    cursor.execute('SELECT username, sender_email, recipient_name, recipient_email, subject, status, error_message, timestamp FROM sent_emails ORDER BY timestamp DESC LIMIT ?', (limit,))
                rows = cursor.fetchall()
                conn.close()
                for row in rows:
                    records.append(dict(row))
            except Exception as e:
                print(f"[DB] Error querying SQLite: {e}")
        return records

# Singleton instance
db_manager = DatabaseManager()
