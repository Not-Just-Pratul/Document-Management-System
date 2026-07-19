#!/usr/bin/env python3
"""
Generate password hash for admin user setup.
Run this script and copy the output hash into Neon SQL Editor.
"""

from werkzeug.security import generate_password_hash

def main():
    print("=" * 60)
    print("Admin Password Hash Generator")
    print("=" * 60)
    
    password = input("Enter admin password (default: admin@808): ").strip()
    if not password:
        password = "admin@808"
    
    print("\nGenerating hash...")
    hash_value = generate_password_hash(password, method='pbkdf2:sha256')
    
    print("\n" + "=" * 60)
    print("Password Hash Generated!")
    print("=" * 60)
    print(f"\nPassword: {password}")
    print(f"Hash: {hash_value}")
    print("\n" + "=" * 60)
    print("SQL to run in Neon SQL Editor:")
    print("=" * 60)
    
    sql = f"""INSERT INTO users (username, password_hash, email, role, is_default_admin, is_active)
VALUES (
  'admin',
  '{hash_value}',
  'admin@example.com',
  'admin',
  TRUE,
  TRUE
) ON CONFLICT (username) DO NOTHING;"""
    
    print(sql)
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
