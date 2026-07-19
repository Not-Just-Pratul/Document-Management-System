#!/usr/bin/env python3
"""
Cross-platform PostgreSQL database setup helper.
"""
import os
import sys
import re
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://dms_user:1234@localhost:5432/document_management")

def parse_db_url(url):
    m = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', url)
    if not m:
        raise ValueError(f"Invalid DATABASE_URL format: {url}")
    return m.group(1), m.group(2), m.group(3), int(m.group(4)), m.group(5)

def get_conn(dbname="postgres"):
    user, password, host, port, _ = parse_db_url(DATABASE_URL)
    return psycopg2.connect(
        host=host, port=port, dbname=dbname, user=user, password=password,
        cursor_factory=RealDictCursor
    )

def db_exists():
    _, _, _, _, dbname = parse_db_url(DATABASE_URL)
    conn = get_conn("postgres")
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
    exists = cur.fetchone() is not None
    cur.close()
    conn.close()
    return exists

def user_exists():
    user, _, _, _, _ = parse_db_url(DATABASE_URL)
    conn = get_conn("postgres")
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (user,))
    exists = cur.fetchone() is not None
    cur.close()
    conn.close()
    return exists

def create_db():
    _, _, _, _, dbname = parse_db_url(DATABASE_URL)
    conn = get_conn("postgres")
    conn.autocommit = True
    cur = conn.cursor()
    try:
        cur.execute(f'CREATE DATABASE "{dbname}"')
        print(f"OK: Database '{dbname}' created")
    except psycopg2.errors.DuplicateDatabase:
        print(f"INFO: Database '{dbname}' already exists")
    except Exception as e:
        print(f"ERROR: Failed to create database: {e}")
    finally:
        cur.close()
        conn.close()

def create_user():
    user, password, _, _, _ = parse_db_url(DATABASE_URL)
    conn = get_conn("postgres")
    conn.autocommit = True
    cur = conn.cursor()
    try:
        cur.execute(f"CREATE USER \"{user}\" WITH PASSWORD '{password}'")
        print(f"OK: User '{user}' created")
    except psycopg2.errors.DuplicateObject:
        print(f"INFO: User '{user}' already exists, updating password...")
        cur.execute(f"ALTER USER \"{user}\" WITH PASSWORD '{password}'")
        print(f"OK: User '{user}' password updated")
    except Exception as e:
        print(f"ERROR: Failed to create user: {e}")
    finally:
        cur.close()
        conn.close()

def grant_privileges():
    user, _, _, _, dbname = parse_db_url(DATABASE_URL)
    conn = get_conn("postgres")
    conn.autocommit = True
    cur = conn.cursor()
    try:
        cur.execute(f'GRANT ALL PRIVILEGES ON DATABASE "{dbname}" TO "{user}"')
        print(f"OK: Granted privileges on database '{dbname}' to '{user}'")
    except Exception as e:
        print(f"ERROR: Failed to grant database privileges: {e}")

    # Connect to the target DB to grant schema privileges
    try:
        conn2 = get_conn(dbname)
        conn2.autocommit = True
        cur2 = conn2.cursor()
        cur2.execute(f'GRANT ALL ON SCHEMA public TO "{user}"')
        cur2.execute(f'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "{user}"')
        cur2.execute(f'GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "{user}"')
        print(f"OK: Granted schema privileges in '{dbname}' to '{user}'")
        cur2.close()
        conn2.close()
    except Exception as e:
        print(f"ERROR: Failed to grant schema privileges: {e}")
    finally:
        cur.close()
        conn.close()

def main():
    print("=" * 60)
    print("Setting up PostgreSQL database (cross-platform)...")
    print("=" * 60)

    try:
        _, _, host, port, dbname = parse_db_url(DATABASE_URL)
        print(f"\nDatabase configuration:")
        print(f"  Host: {host}:{port}")
        print(f"  Database: {dbname}")
    except Exception as e:
        print(f"ERROR: Failed to parse DATABASE_URL: {e}")
        return 1

    if not db_exists():
        create_db()
    else:
        print(f"INFO: Database '{dbname}' already exists")

    if not user_exists():
        create_user()
    else:
        print(f"INFO: User already exists")

    grant_privileges()

    print("\n" + "=" * 60)
    print("Database setup complete!")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(main())
