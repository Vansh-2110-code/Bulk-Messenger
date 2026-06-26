"""
Clear Chrome Profiles Script
This script clears the Chrome profile cache which can sometimes become corrupted.
"""

import shutil
import os

def clear_profiles():
    """Clear Chrome profile directories"""
    chrome_profiles_dir = os.path.join(os.getcwd(), "chrome_profiles")
    
    if os.path.exists(chrome_profiles_dir):
        print(f"[*] Clearing Chrome profiles directory...")
        try:
            shutil.rmtree(chrome_profiles_dir)
            print(f"[OK] Chrome profiles cleared successfully!")
            print(f"[NOTE] You will need to log in again when you run the script.")
        except Exception as e:
            print(f"[ERROR] Error clearing profiles: {str(e)}")
            print(f"[TIP] Try manually deleting the 'chrome_profiles' folder.")
    else:
        print(f"[INFO] No chrome_profiles directory found. Nothing to clear.")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("   CHROME PROFILES CLEANER")
    print("="*60)
    print("\nThis will clear saved Chrome login sessions.")
    print("You will need to log in again to WhatsApp and Gmail.\n")
    
    response = input("Do you want to continue? (yes/no): ").strip().lower()
    
    if response in ['yes', 'y']:
        clear_profiles()
    else:
        print("[CANCEL] Operation cancelled.")
    
    print("\n" + "="*60)
