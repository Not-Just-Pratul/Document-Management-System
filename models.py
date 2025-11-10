import psycopg2
import secrets
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash

from config import DATABASE_URL

def get_db_connection():
    """Get PostgreSQL database connection"""
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    except psycopg2.Error as e:
        print(f"Database connection error: {e}")
        return None

def recreate_tables():
    """Drops all existing tables from the PostgreSQL database."""
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to database for table recreation.")
        return False
    
    cursor = conn.cursor()
    try:
        cursor.execute('''
            DROP TABLE IF EXISTS admin_notifications CASCADE;
            DROP TABLE IF EXISTS document_requests CASCADE;
            DROP TABLE IF EXISTS audit_logs CASCADE;
            DROP TABLE IF EXISTS download_logs CASCADE;
            DROP TABLE IF EXISTS document_departments CASCADE;
            DROP TABLE IF EXISTS document_plants CASCADE;
            DROP TABLE IF EXISTS documents CASCADE;
            DROP TABLE IF EXISTS document_types CASCADE;
            DROP TABLE IF EXISTS user_departments CASCADE;
            DROP TABLE IF EXISTS user_plants CASCADE;
            DROP TABLE IF EXISTS users CASCADE;
            DROP TABLE IF EXISTS departments CASCADE;
            DROP TABLE IF EXISTS plants CASCADE;
        ''')
        conn.commit()
        print("DEBUG: Dropped all tables.")
        return True
    except psycopg2.Error as e:
        print(f"Database table recreation error: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

def init_db(force_recreate=False):
    """Initialize PostgreSQL database"""
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to database")
        return False
    
    cursor = conn.cursor()
    
    try:
        if force_recreate:
            if not recreate_tables():
                return False
        

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS plants (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL
            );

            CREATE TABLE IF NOT EXISTS departments (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL
            );

            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(80) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                email VARCHAR(120) UNIQUE,
                role VARCHAR(20) NOT NULL DEFAULT 'user',
                is_active BOOLEAN DEFAULT TRUE,
                last_login TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS user_plants (
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                plant_id INTEGER REFERENCES plants(id) ON DELETE CASCADE,
                PRIMARY KEY (user_id, plant_id)
            );

            CREATE TABLE IF NOT EXISTS user_departments (
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                department_id INTEGER REFERENCES departments(id) ON DELETE CASCADE,
                PRIMARY KEY (user_id, department_id)
            );
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS document_types (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL
            );

            CREATE TABLE IF NOT EXISTS documents (
                id SERIAL PRIMARY KEY,
                title VARCHAR(200) NOT NULL,
                description TEXT,
                filename VARCHAR(255) NOT NULL,
                file_path VARCHAR(500) NOT NULL,
                file_size BIGINT,
                mime_type VARCHAR(100),
                uploaded_by INTEGER NOT NULL,
                document_type_id INTEGER REFERENCES document_types(id),
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (uploaded_by) REFERENCES users (id)
            );

            CREATE TABLE IF NOT EXISTS document_plants (
                document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
                plant_id INTEGER REFERENCES plants(id) ON DELETE CASCADE,
                PRIMARY KEY (document_id, plant_id)
            );

            CREATE TABLE IF NOT EXISTS document_departments (
                document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
                department_id INTEGER REFERENCES departments(id) ON DELETE CASCADE,
                PRIMARY KEY (document_id, department_id)
            );
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS download_logs (
                id SERIAL PRIMARY KEY,
                document_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES documents (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                action VARCHAR(255) NOT NULL,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS document_requests (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
                requested_document_description TEXT,
                document_type_id INTEGER REFERENCES document_types(id),
                requested_format VARCHAR(50) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS admin_notifications (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
                requested_document_description TEXT,
                message TEXT NOT NULL,
                is_read BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        print("DEBUG: Created audit_logs, document_requests, admin_notifications tables.")

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS plants (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL
            );

            CREATE TABLE IF NOT EXISTS departments (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL
            );

            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(80) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                email VARCHAR(120) UNIQUE,
                role VARCHAR(20) NOT NULL DEFAULT 'user',
                is_active BOOLEAN DEFAULT TRUE,
                last_login TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS user_plants (
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                plant_id INTEGER REFERENCES plants(id) ON DELETE CASCADE,
                PRIMARY KEY (user_id, plant_id)
            );

            CREATE TABLE IF NOT EXISTS user_departments (
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                department_id INTEGER REFERENCES departments(id) ON DELETE CASCADE,
                PRIMARY KEY (user_id, department_id)
            );
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS document_types (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL
            );

            CREATE TABLE IF NOT EXISTS documents (
                id SERIAL PRIMARY KEY,
                title VARCHAR(200) NOT NULL,
                description TEXT,
                filename VARCHAR(255) NOT NULL,
                file_path VARCHAR(500) NOT NULL,
                file_size BIGINT,
                mime_type VARCHAR(100),
                uploaded_by INTEGER NOT NULL,
                document_type_id INTEGER REFERENCES document_types(id),
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (uploaded_by) REFERENCES users (id)
            );

            CREATE TABLE IF NOT EXISTS document_plants (
                document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
                plant_id INTEGER REFERENCES plants(id) ON DELETE CASCADE,
                PRIMARY KEY (document_id, plant_id)
            );

            CREATE TABLE IF NOT EXISTS document_departments (
                document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
                department_id INTEGER REFERENCES departments(id) ON DELETE CASCADE,
                PRIMARY KEY (document_id, department_id)
            );
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS download_logs (
                id SERIAL PRIMARY KEY,
                document_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES documents (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                action VARCHAR(255) NOT NULL,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS document_requests (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
                requested_document_description TEXT,
                document_type_id INTEGER REFERENCES document_types(id),
                requested_format VARCHAR(50) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS admin_notifications (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
                requested_document_description TEXT,
                message TEXT NOT NULL,
                is_read BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        
        # Add last_login column to users table if it doesn't exist
        cursor.execute('''
            ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP
        ''')

        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_uploaded_at ON documents(uploaded_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_uploader ON documents(uploaded_by)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_download_logs_document ON download_logs(document_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_download_logs_user ON download_logs(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_download_logs_date ON download_logs(downloaded_at)')
        
        conn.commit()
        print("Database tables created successfully")
        return True
        
    except psycopg2.Error as e:
        print(f"Database initialization error: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

def create_initial_data():

    """Create initial data"""

    conn = get_db_connection()

    if not conn:

        return False

    

    cursor = conn.cursor()

    

    try:

        print("Creating initial data...")

        

        # Create plants

        plants_data = [('Rudrapur',), ('Zaheerabad',), ('Palwal',)]

        cursor.executemany('INSERT INTO plants (name) VALUES (%s) ON CONFLICT (name) DO NOTHING', plants_data)



        # Create departments

        departments_data = [

            ('HR & Admin',), ('Sales & Marketing',), ('QMS',), ('Quality',),

            ('Purchase',), ('Store',), ('Dispatch',), ('Production',),

            ('NPD (New Product Development)',), ('Machine Maintenance',), ('Tool Maintenance',)

        ]

        cursor.executemany('INSERT INTO departments (name) VALUES (%s) ON CONFLICT (name) DO NOTHING', departments_data)





        # Create document types

        cursor.execute("DELETE FROM document_types WHERE name = 'Work Instructions / SOP / Standards / Drawings'")

        document_types_data = [
            ('Quality Manuals',), ('Quality Procedures',), ('Work Instructions',), ('SOP',), ('Standards',), ('Drawings',), ('General Documents',)
        ]



        cursor.executemany('INSERT INTO document_types (name) VALUES (%s) ON CONFLICT (name) DO NOTHING', document_types_data)



        # Get plant and department IDs

        cursor.execute("SELECT id, name FROM plants")

        plants = {plant['name']: plant['id'] for plant in cursor.fetchall()}

        cursor.execute("SELECT id, name FROM departments")

        departments = {dept['name']: dept['id'] for dept in cursor.fetchall()}



        # Create a single admin user

        admin_user_data = ('admin', generate_password_hash('admin123', method='pbkdf2:sha256'), 'admin@example.com', 'admin')

        cursor.execute(

            'INSERT INTO users (username, password_hash, email, role) VALUES (%s, %s, %s, %s) ON CONFLICT (username) DO NOTHING RETURNING id',

            admin_user_data

        )
        cursor.execute("SELECT id FROM users WHERE username = 'admin'")
        admin_id = cursor.fetchone()['id']

        for plant_id in plants.values():
            cursor.execute('INSERT INTO user_plants (user_id, plant_id) VALUES (%s, %s) ON CONFLICT DO NOTHING', (admin_id, plant_id,))

        for dept_id in departments.values():
            cursor.execute('INSERT INTO user_departments (user_id, department_id) VALUES (%s, %s) ON CONFLICT DO NOTHING', (admin_id, dept_id,))

        

        conn.commit()

        print("Initial data created successfully")

        return True

        

    except psycopg2.Error as e:

        print(f"Error creating initial data: {e}")

        conn.rollback()

        return False

    finally:

        cursor.close()

        conn.close()



def initialize_database():



    """Initialize database and create initial data"""



    init_db_result = init_db()



    print(f"DEBUG: init_db() returned: {init_db_result}")



    if init_db_result:



        print("OK Database initialized successfully")



        if create_initial_data():



            print("OK Initial data created successfully")



            return True



        else:



            print("X Failed to create initial data")



            return False



    else:



        print("X Failed to initialize database")



        return False