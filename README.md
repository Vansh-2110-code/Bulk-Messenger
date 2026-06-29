# Bulk Messaging System 

Production-ready Python script for sending bulk messages via WhatsApp and Gmail.

## Features

✅ **Three Operation Modes** - WhatsApp only, Email only, or Both with single sign-in  
✅ **Browser-Based Login** - No password configuration needed, login via Chrome browser  
✅ **WhatsApp Integration** - Automated messaging via WhatsApp Web (Selenium)  
✅ **Gmail Integration** - Automated emails via Gmail web interface with attachments  
✅ **Excel Data Import** - Read contacts from Excel file  
✅ **Error Handling** - Continues execution even if individual messages fail  
✅ **Personalized Messages** - Dynamic name replacement in templates  

## Prerequisites

1. **Python 3.8+** installed on your system
2. **Google Chrome** browser installed
3. **WhatsApp account** (for WhatsApp messaging)
4. **Gmail account** (for email messaging)

## Installation

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Create Sample Excel File

```bash
python create_sample_excel.py
```

This will create `contacts.xlsx` with sample data. Replace it with your actual contacts.

### Step 3: Optional - Add PDF Brochure

Place your brochure PDF in the same folder and name it `Lintcloud_Brochure.pdf` (or update `BROCHURE_PATH` in the script).

### Step 4: Update Mobile Number

Open `bulk_messenger.py` and update:

```python
YOUR_MOBILE_NUMBER = # Your mobile number
YOUR_GMAIL_ID = # Your Gmail ID
```

**That's it! No password configuration needed.**

## Excel File Format

Your `contacts.xlsx` file must have the following columns:

| Name        | Email              | Phone          |
|-------------|--------------------|----------------|
| John Doe    | john@example.com   | +919876543210  |
| Jane Smith  | jane@example.com   | +919876543211  |

**Note:** Phone numbers should include country code (e.g., +91 for India)

## Usage

### Run the Script

```bash
python bulk_messenger.py
```

### Select Operation

You'll see an interactive menu with three options:

```
📬 Select Messaging Service:

[1] WhatsApp Only (Single Sign-In)
[2] Email Only (Single Sign-In)
[3] Both WhatsApp + Email (Single Sign-In for Both)

[0] Exit
```

**Option Descriptions:**

- **[1] WhatsApp Only**: Send messages only via WhatsApp. You'll need to scan the QR code once. No email configuration required.
- **[2] Email Only**: Send emails only via Gmail SMTP. You'll need to configure Gmail credentials. No WhatsApp login required.
- **[3] Both Services**: Send both WhatsApp AND Email to each contact. Single sign-in for both services (scan QR for WhatsApp, Gmail credentials for Email).

### WhatsApp Login (Options 1 & 3)

When you select option [1] or [3]:
1. Chrome browser will open automatically
2. WhatsApp Web will load
3. **Scan the QR code** with your phone
4. Press **Enter** in the terminal after login
5. Script will start sending messages

### Email Login (Options 2 & 3)

**No configuration needed!** Email now uses browser-based login (just like WhatsApp).

When you select option [2] or [3]:
1. Chrome browser will open automatically with Gmail
2. **Login to your Gmail** account in the browser:
   - Enter your email address
   - Enter your regular password (no App Password needed!)
   - Complete 2FA if you have it enabled
3. Wait for Gmail inbox to load
4. Press **Enter** in the terminal to confirm
5. Script will start sending emails

### Optional: Add PDF Attachment

If you want to attach a brochure PDF to emails:
1. Place your PDF in the same folder as `bulk_messenger.py`
2. Name it `Lintcloud_Brochure.pdf` (or update `BROCHURE_PATH` in the script)

## Important Notes

### WhatsApp Usage

⚠️ **Anti-Ban Measures:**
- Script uses single-tab navigation (no new tabs)
- 5-second delay between messages (configurable)
- Do NOT send too many messages in short time
- Recommended: Max 50-100 messages per session

⚠️ **Phone Number Format:**
- Include country code: `+919876543210`
- Can include spaces/dashes: `+91 98765-43210`
- Script will auto-format for WhatsApp

### Gmail Usage

⚠️ **Browser-Based Login:**
- Login to Gmail directly in Chrome browser
- Use your regular Gmail password (no App Password needed)
- 2FA works normally if you have it enabled
- Session persists as long as browser stays open

⚠️ **Attachment:**
- Place `Lintcloud_Brochure.pdf` in the same folder
- Script will attach it automatically to each email
- If file not found, emails sent without attachment
- Update `BROCHURE_PATH` if file is elsewhere

⚠️ **Gmail Limitations:**
- Gmail has sending limits (~500 emails/day for regular accounts)
- Add delays between emails (script does this automatically)
- For large batches, split across multiple days

### Safety & Compliance

⚠️ **Legal & Ethical:**
- Only send messages to contacts who have consented
- Comply with GDPR, TCPA, and local regulations
- Respect opt-out requests immediately
- Don't spam - you may be banned

## Troubleshooting

### Chrome Driver Issues

**Error:** `chromedriver not found`

**Solution:** The script uses Selenium 4.x which auto-downloads ChromeDriver. Ensure Chrome browser is installed.

### WhatsApp Not Loading

**Error:** QR code doesn't appear

**Solution:**
1. Close all Chrome instances
2. Clear browser cache
3. Run script again
4. Ensure stable internet connection

### Gmail Login Issues

**Error:** Can't login or page doesn't load

**Solution:**
1. Check internet connection is stable
2. Make sure you're entering correct Gmail password
3. Complete 2FA steps if prompted
4. Wait for inbox to fully load before pressing Enter
5. Try incognito mode if having issues

### Excel File Not Found

**Error:** `Excel file 'contacts.xlsx' not found`

**Solution:**
1. Run `python create_sample_excel.py` first
2. Ensure Excel file is in same directory
3. Check `EXCEL_FILE` path in configuration

## Customization

### Message Template

Edit the `get_message_body()` function in `bulk_messenger.py` to customize your message:

```python
def get_message_body(name):
    return f"""Dear {name},

Your custom message here...

Thanks & regards,
Your Name
Contact Info"""
```

### Timing Configuration

Adjust wait times to avoid bans:

```python
WHATSAPP_WAIT_TIME = 5           # Seconds between WhatsApp messages
MESSAGE_SEND_BUTTON_WAIT = 10    # Timeout for send button
```

## Project Structure

```
bulk/
├── bulk_messenger.py           # Main script
├── create_sample_excel.py      # Helper to create sample Excel
├── contacts.xlsx               # Your contacts (create this)
├── Lintcloud_Brochure.pdf      # Your PDF attachment (add this)
├── requirements.txt            # Python dependencies
└── README.md                   # This file

---

**⚠️ DISCLAIMER:** Use this tool responsibly. The developers are not responsible for any misuse, spam, or violations of terms of service. Always obtain consent before sending bulk messages.
