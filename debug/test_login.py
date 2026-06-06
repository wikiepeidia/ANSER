#!/usr/bin/env python3
"""Test password verification with the fixed schema."""
import sys
sys.path.insert(0, '.')
from core.config import Config
from core.auth import AuthManager
from core.db.connection import Database

# Initialize database
db = Database()
auth = AuthManager(db)

# Test with a known account
test_email = "admin@admin.com"

# Try common passwords
test_passwords = ["admin", "password", "123456", "test123", "admin123"]

print(f"\n🔐 Testing login for: {test_email}\n")

for test_pwd in test_passwords:
    result = auth.verify_user(test_email, test_pwd)
    status = "✅ SUCCESS" if result else "❌ FAILED"
    print(f"  Password: {test_pwd:15} → {status}")
    if result:
        print(f"    User ID: {result['id']}, Role: {result['role']}")

print("\n💡 If all fail, the password stored in DB may not match any common test passwords.")
print("   You may need to:")
print("   1. Check what the actual password is")
print("   2. Reset the user password")
print("   3. Register a new test user with a known password")
