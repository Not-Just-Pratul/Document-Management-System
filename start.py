#!/usr/bin/env python3
"""
Startup script for Multi-Plant Document Management System with PostgreSQL
"""

import os
import sys
import subprocess
from dotenv import load_dotenv

def check_postgres_path():
    """Check if PostgreSQL is available at the specified path"""
    postgres_path = r"C:\Progra~1\PostgreSQL\18\bin\psql.exe"
    
    if os.path.exists(postgres_path):
        print(f"OK PostgreSQL found at: {postgres_path}")
        return True
    else:
        print(f"X PostgreSQL not found at: {postgres_path}")
        print("Please ensure PostgreSQL 18 is installed at C:\\Program Files\\PostgreSQL\\18\\")
        return False

def check_dependencies():
    """Check if required Python packages are installed"""
    try:
        import psycopg2
        import dotenv
        print("OK Required dependencies found")
        return True
    except ImportError as e:
        print(f"X Missing dependency: {e}")
        print("Installing dependencies...")
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'psycopg2-binary', 'python-dotenv'], check=True)
            print("OK Dependencies installed successfully")
            return True
        except subprocess.CalledProcessError:
            print("X Failed to install dependencies")
            return False

def check_env_file():
    """Check if .env file exists"""
    if os.path.exists('.env'):
        print("OK .env file found")
        return True
    else:
        print("X .env file not found")
        print("Please run: python setup_postgresql.py")
        return False

def main():
    """Main startup process"""
    print("=" * 60)
    print("Multi-Plant Document Management System")
    print("PostgreSQL Startup Check")
    print("=" * 60)
    
    # Check PostgreSQL
    if not check_postgres_path():
        return False
    
    # Check dependencies
    if not check_dependencies():
        return False
    
    # Check .env file
    if not check_env_file():
        return False
    
    print("\n" + "=" * 60)
    print("OK All checks passed!")
    print("Starting application...")
    print("=" * 60)
    
    # Import and run the application
    try:
        from app import app
        import models
        
        # Initialize database and data
        if models.initialize_database():
            print("OK Database initialized successfully")
        else:
            print("X Failed to initialize database")
            return False
        
        # Create upload directories
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        print("\n" + "=" * 60)
        print("Multi-Plant Document Management System")
        print("PostgreSQL Version - Ready!")
        print("=" * 60)
        print("Default admin account:")
        print("- Admin: admin / admin123")
        print("\nAccess the application at: http://localhost:5000")
        print("=" * 60)
        
        # Run the application
        app.run(debug=app.debug, host='localhost', port=5000)
        
    except Exception as e:
        import traceback
        print(f"X Failed to start application: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            print("\nStartup failed. Please check the errors above.")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nApplication stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)
