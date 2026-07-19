import psycopg2
from psycopg2.extras import RealDictCursor
import os

# Get DATABASE_URL from environment or .env file
DATABASE_URL = "postgresql://dms_user:1234@localhost:5432/document_management"
print(f"DEBUG: DATABASE_URL = {DATABASE_URL}")

if not DATABASE_URL:
    print("DATABASE_URL not found. Please set it in .env file.")
    exit(1)

def get_table_schema(table_name):
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table_name}' ORDER BY ordinal_position;")
        schema = cursor.fetchall()
        cursor.close()
        return schema
    except psycopg2.Error as e:
        print(f"Error connecting to database or fetching schema for {table_name}: {e}")
        return None
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    tables_to_check = ["documents", "departments", "document_types", "users", "document_requests", "audit_logs"]

    for table_name in tables_to_check:
        print(f"\n--- Schema for {table_name} ---")
        schema = get_table_schema(table_name)
        if schema:
            for col in schema:
                print(f"- {col['column_name']} ({col['data_type']})")
        else:
            print(f"Could not retrieve schema for {table_name}.")