#!/usr/bin/env python3
"""
Import Mini App translations from CSV to database via API
"""
import csv
import requests
import sys
from pathlib import Path

# API Configuration
API_BASE = "https://api-production-57e8.up.railway.app"
ADMIN_USERNAME = "markshark"
ADMIN_PASSWORD = "markshark"

def get_auth_token():
    """Get JWT token for admin access"""
    response = requests.post(
        f"{API_BASE}/api/v1/admin/auth/login",
        json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
    )
    response.raise_for_status()
    return response.json()["access_token"]

def import_translation(token, key, lang, text):
    """Import single translation via API"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.put(
        f"{API_BASE}/api/v1/admin/translations/{key}/{lang}",
        params={"text": text},
        headers=headers
    )
    return response.status_code == 200

def main():
    csv_path = Path(__file__).parent / "mini_app_ui_translations.csv"
    
    if not csv_path.exists():
        print(f"❌ CSV file not found: {csv_path}")
        sys.exit(1)
    
    print("🔐 Getting auth token...")
    try:
        token = get_auth_token()
        print("✅ Authenticated")
    except Exception as e:
        print(f"❌ Auth failed: {e}")
        sys.exit(1)
    
    print(f"📥 Importing translations from {csv_path}")
    
    imported = 0
    failed = 0
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            lang = row['language'].strip()
            key = row['message_key'].strip()
            text = row['text'].strip()
            
            try:
                if import_translation(token, key, lang, text):
                    imported += 1
                    if imported % 10 == 0:
                        print(f"  ✓ Imported {imported} translations...")
                else:
                    failed += 1
                    print(f"  ✗ Failed: {key}/{lang}")
            except Exception as e:
                failed += 1
                print(f"  ✗ Error {key}/{lang}: {e}")
    
    print(f"\n✅ Done! Imported {imported} translations, {failed} failed")

if __name__ == "__main__":
    main()
