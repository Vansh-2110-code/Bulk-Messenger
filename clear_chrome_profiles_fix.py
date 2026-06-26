"""
Chrome Profile Cleanup Script
This script will delete corrupted Chrome profiles that cause ERR_INVALID_ARGUMENT
"""
import os
import shutil
import time
import sys

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

def clear_chrome_profiles():
    print("=" * 60)
    print("Chrome Profile Cleanup Tool")
    print("=" * 60)
    
    # Get the chrome_profiles directory
    profiles_dir = os.path.join(os.getcwd(), "chrome_profiles")
    
    if not os.path.exists(profiles_dir):
        print("\n✅ No chrome_profiles folder found - nothing to clean!")
        print("   The script will create fresh profiles on next run.")
        return True
    
    print(f"\n📂 Found profiles directory: {profiles_dir}")
    
    # List what's inside
    try:
        contents = os.listdir(profiles_dir)
        if len(contents) == 0:
            print("   📭 Directory is empty - nothing to clean!")
            return True
        
        print(f"\n📋 Found {len(contents)} profile(s):")
        for item in contents:
            item_path = os.path.join(profiles_dir, item)
            if os.path.isdir(item_path):
                try:
                    size = sum(os.path.getsize(os.path.join(dirpath, filename))
                              for dirpath, dirnames, filenames in os.walk(item_path)
                              for filename in filenames)
                    size_mb = size / (1024 * 1024)
                    print(f"   📁 {item} ({size_mb:.1f} MB)")
                except:
                    print(f"   📁 {item}")
            else:
                print(f"   📄 {item}")
    except Exception as e:
        print(f"   ⚠️  Could not list contents: {e}")
    
    # Confirm deletion
    print("\n" + "=" * 60)
    print("⚠️  WARNING: This will DELETE all Chrome profiles!")
    print("   You will need to re-login to WhatsApp and Gmail.")
    print("=" * 60)
    
    response = input("\n🗑️  Do you want to delete these profiles? (yes/no): ").strip().lower()
    
    if response not in ['yes', 'y']:
        print("\n❌ Cleanup cancelled. No changes made.")
        return False
    
    # Delete the directory
    print("\n🗑️  Deleting chrome_profiles folder...")
    try:
        # Close any file handles
        time.sleep(1)
        
        # Try to remove the directory
        shutil.rmtree(profiles_dir, ignore_errors=True)
        
        # Verify deletion
        time.sleep(0.5)
        if not os.path.exists(profiles_dir):
            print("✅ Successfully deleted chrome_profiles!")
            print("\n📌 Next steps:")
            print("   1. Run your bulk_messenger.py script again")
            print("   2. Login to Gmail when prompted")
            print("   3. The ERR_INVALID_ARGUMENT error should be fixed!")
            return True
        else:
            print("⚠️  Folder still exists. Trying alternative method...")
            
            # Try renaming instead (Windows sometimes locks folders)
            backup_name = f"chrome_profiles_backup_{int(time.time())}"
            os.rename(profiles_dir, backup_name)
            print(f"✅ Renamed to: {backup_name}")
            print("   You can manually delete this folder later.")
            return True
            
    except Exception as e:
        print(f"❌ Error during deletion: {e}")
        print("\n💡 Manual fix:")
        print(f"   1. Close all Chrome windows")
        print(f"   2. Manually delete folder: {profiles_dir}")
        print(f"   3. Run the script again")
        return False

if __name__ == "__main__":
    try:
        success = clear_chrome_profiles()
        
        print("\n" + "=" * 60)
        if success:
            print("🎉 Cleanup complete!")
        else:
            print("⚠️  Cleanup incomplete - see instructions above")
        print("=" * 60)
        
        input("\nPress Enter to exit...")
        
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        input("\nPress Enter to exit...")
