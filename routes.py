import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash, send_file, abort, current_app
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
import mimetypes
import logging

import secrets

from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature

from models import get_db_connection

from extensions import csrf
from extensions import limiter # Import limiter from extensions.py
from flask import current_app

import magic # Import the python-magic library

main = Blueprint('main', __name__)

def allowed_file(filename, file_stream):
    # 1. Check extension whitelist
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    if ext not in current_app.config['ALLOWED_EXTENSIONS']:
        return False

    # 2. Perform magic byte sniffing
    # Read a chunk of the file to determine its MIME type
    file_stream.seek(0) # Ensure we read from the beginning
    buffer = file_stream.read(1024) # Read first 1024 bytes
    file_stream.seek(0) # Reset stream position for subsequent reads

    try:
        detected_mime = magic.from_buffer(buffer, mime=True)
    except Exception as e:
        current_app.logger.error(f"Magic detection failed for {filename}: {e}")
        return False # If magic detection fails, deny the file

    # 3. Compare detected MIME type with allowed MIME types for the extension
    allowed_mimes_for_ext = current_app.config['ALLOWED_MIMETYPES'].get(ext)
    if not allowed_mimes_for_ext:
        # If extension is allowed but no specific MIME types are defined,
        # fall back to a more general check or deny. For now, deny.
        current_app.logger.warning(f"No allowed MIME types defined for extension .{ext}")
        return False

    if detected_mime not in allowed_mimes_for_ext:
        current_app.logger.warning(f"File {filename} (.{ext}) detected as {detected_mime}, but expected one of {allowed_mimes_for_ext}")
        return False

    return True

# Authentication decorators
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('main.login'))
        if session.get('role') != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

@main.route('/login', methods=['GET', 'POST'])
@csrf.exempt
# @limiter.limit("5 per minute") # Apply rate limit to login attempts
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Username and password are required', 'danger')
            return redirect(url_for('main.login'))

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cursor.fetchone()

        current_app.logger.info(f"Login attempt for user: {username}")
        current_app.logger.info(f"User from DB: {user}")

        if user and check_password_hash(user['password_hash'], password):
            current_app.logger.info("Password check successful")
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']

            cursor.execute('SELECT plant_id FROM user_plants WHERE user_id = %s', (user['id'],))
            plant_ids = [row['plant_id'] for row in cursor.fetchall()]
            session['plant_ids'] = plant_ids

            cursor.execute('SELECT department_id FROM user_departments WHERE user_id = %s', (user['id'],))
            department_ids = [row['department_id'] for row in cursor.fetchall()]
            session['department_ids'] = department_ids

            cursor.execute('UPDATE users SET last_login = NOW() WHERE id = %s', (user['id'],))
            conn.commit()
            cursor.close()
            conn.close()

            current_app.log_audit(current_app, 'login', user_id=user['id'])
            current_app.logger.info(f"Admin login successful. Session role: {session.get('role')}, Plant IDs: {session.get('plant_ids')}, Department IDs: {session.get('department_ids')}")
            return redirect(url_for('main.dashboard'))
        else:
            flash('Invalid username or password', 'danger')
            cursor.close()
            conn.close()
            return redirect(url_for('main.login'))

    return render_template('login.html')

@main.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('main.login'))

@main.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.login'))




@main.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get user info
    cursor.execute('SELECT id, username, email, role FROM users WHERE id = %s', (session['user_id'],))
    user = cursor.fetchone()
    
    if not user:
        flash('User not found.')
        return redirect(url_for('main.login'))

    plant_ids = session.get('plant_ids', [])
    department_ids = session.get('department_ids', [])

    if session['role'] == 'admin':
        cursor.execute('SELECT COUNT(*) as count FROM documents')
    else:
        if not plant_ids or not department_ids:
            flash('User session missing plant or department information.')
            return redirect(url_for('main.login'))
        cursor.execute('''
            SELECT COUNT(DISTINCT d.id) AS count
            FROM documents d
            JOIN document_plants dp ON d.id = dp.document_id
            JOIN document_departments dd ON d.id = dd.document_id
            WHERE dp.plant_id = ANY(%s) AND dd.department_id = ANY(%s)
        ''', (plant_ids, department_ids))
    document_count = cursor.fetchone()['count']
    
    documents_per_department = []
    if user['role'] == 'admin':
        cursor.execute('''
            SELECT d.name, COUNT(doc.id) AS document_count
            FROM departments d
            LEFT JOIN document_departments dd ON d.id = dd.department_id
            LEFT JOIN documents doc ON dd.document_id = doc.id
            GROUP BY d.name
            ORDER BY d.name
        ''')
        documents_per_department = cursor.fetchall()
    else:
        # For non-admin, show only their department's documents
        cursor.execute('''
            SELECT d.name, COUNT(doc.id) AS document_count
            FROM departments d
            LEFT JOIN document_departments dd ON d.id = dd.department_id
            LEFT JOIN documents doc ON dd.document_id = doc.id
            LEFT JOIN document_plants dp ON doc.id = dp.document_id
            WHERE d.id = ANY(%s) AND dp.plant_id = ANY(%s)
            GROUP BY d.name
        ''', (department_ids, plant_ids))
        documents_per_department = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template('dashboard.html', user=user, document_count=document_count, documents_per_department=documents_per_department)

@main.route('/documents')
def documents():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Preload lists for filters (always load all for public access)
    cursor.execute('SELECT id, name FROM plants ORDER BY name')
    plants = cursor.fetchall()
    cursor.execute('SELECT id, name FROM departments ORDER BY name')
    departments = cursor.fetchall()

    # Sorting params (whitelisted)
    sort = request.args.get('sort', 'uploaded_at')
    order = request.args.get('order', 'desc').lower()
    sort_map = {
        'title': 'd.title',
        'uploaded_at': 'd.uploaded_at',
        'size': 'd.file_size',
        'type': 'dt.name',
    }
    sort_col = sort_map.get(sort, 'd.uploaded_at')
    order_dir = 'DESC' if order != 'asc' else 'ASC'

    base_query = '''
        SELECT d.id, d.title, d.description, d.filename, d.file_size, d.mime_type,
               d.uploaded_at, d.updated_at,
               u.id AS uploader_id, u.username AS uploader_name,
               dt.id AS document_type_id, dt.name AS document_type_name,
               STRING_AGG(DISTINCT p.name, ', ') AS plant_names,
               STRING_AGG(DISTINCT dept.name, ', ') AS department_names
        FROM documents d
        JOIN users u ON d.uploaded_by = u.id
        JOIN document_types dt ON d.document_type_id = dt.id
        LEFT JOIN document_plants dp ON d.id = dp.document_id
        LEFT JOIN plants p ON dp.plant_id = p.id
        LEFT JOIN document_departments dd ON d.id = dd.document_id
        LEFT JOIN departments dept ON dd.department_id = dept.id
    '''
    where_clauses = []
    params = []

    # Filters (now apply to everyone, no admin check needed)
    plant_filter = request.args.get('plant_id')
    dept_filter = request.args.get('department_id')
    if plant_filter:
        where_clauses.append('d.id IN (SELECT document_id FROM document_plants WHERE plant_id = %s)')
        params.append(plant_filter)
    if dept_filter:
        where_clauses.append('d.id IN (SELECT document_id FROM document_departments WHERE department_id = %s)')
        params.append(dept_filter)

    # Search filter
    search = request.args.get('search')
    if search:
        where_clauses.append('d.title ILIKE %s')
        params.append(f'%{search}%')

    query = base_query
    if where_clauses:
        query += ' WHERE ' + ' AND '.join(where_clauses)
    query += ' GROUP BY d.id, u.id, dt.id'
    query += f' ORDER BY {sort_col} {order_dir}, d.id DESC'

    # Execute query
    cursor.execute(query, params)
    rows = cursor.fetchall()

    # Shape data for template
    shaped_documents = []
    for row in rows:
        shaped_documents.append({
            'id': row['id'],
            'title': row['title'],
            'description': row['description'],
            'filename': row['filename'],
            'file_size': row['file_size'],
            'mime_type': row['mime_type'],
            'uploaded_at': row['uploaded_at'],
            'updated_at': row['updated_at'],
            'uploader': {
                'id': row['uploader_id'],
                'username': row['uploader_name'],
            },
            'document_type': {
                'id': row['document_type_id'],
                'name': row['document_type_name'],
            },
            'plants': row['plant_names'],
            'departments': row['department_names'],
        })

    cursor.close()
    conn.close()
    return render_template(
        'documents.html',
        documents=shaped_documents,
        user={'role': session.get('role', 'guest')},
        plants=plants,
        departments=departments
    )

@main.route('/api/documents')
def api_documents():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
    except ValueError:
        page = 1
        per_page = 10
    page = max(page, 1)
    per_page = max(min(per_page, 100), 1)

    base_query = '''
        SELECT d.id, d.title, d.description, d.filename, d.file_size, d.mime_type,
               d.uploaded_at, d.updated_at,
               u.id AS uploader_id, u.username AS uploader_name,
               dt.id AS document_type_id, dt.name AS document_type_name,
               STRING_AGG(DISTINCT p.name, ', ') AS plant_names,
               STRING_AGG(DISTINCT dept.name, ', ') AS department_names
        FROM documents d
        JOIN users u ON d.uploaded_by = u.id
        JOIN document_types dt ON d.document_type_id = dt.id
        LEFT JOIN document_plants dp ON d.id = dp.document_id
        LEFT JOIN plants p ON dp.plant_id = p.id
        LEFT JOIN document_departments dd ON d.id = dd.document_id
        LEFT JOIN departments dept ON dd.department_id = dept.id
    '''
    where_clauses = []
    params = []

    # Filters (now apply to everyone, no admin check needed)
    plant_filter = request.args.get('plant_id')
    dept_filter = request.args.get('department_id')
    if plant_filter:
        where_clauses.append('d.id IN (SELECT document_id FROM document_plants WHERE plant_id = %s)')
        params.append(plant_filter)
    if dept_filter:
        where_clauses.append('d.id IN (SELECT document_id FROM document_departments WHERE department_id = %s)')
        params.append(dept_filter)

    search = request.args.get('search')
    if search:
        where_clauses.append('d.title ILIKE %s')
        params.append(f'%{search}%')

    count_query = 'SELECT COUNT(DISTINCT d.id) AS count FROM documents d'
    if where_clauses:
        count_query += ' LEFT JOIN document_plants dp ON d.id = dp.document_id LEFT JOIN document_departments dd ON d.id = dd.document_id WHERE ' + ' AND '.join(where_clauses)

    query = base_query
    if where_clauses:
        query += ' WHERE ' + ' AND '.join(where_clauses)
    query += ' GROUP BY d.id, u.id, dt.id'
    query += ' ORDER BY d.uploaded_at DESC LIMIT %s OFFSET %s'

    cursor.execute(count_query, params)
    total_count = cursor.fetchone()['count']

    paginated_params = params + [per_page, (page - 1) * per_page]
    cursor.execute(query, paginated_params)
    rows = cursor.fetchall()

    documents = []
    for row in rows:
        documents.append({
            'id': row['id'],
            'title': row['title'],
            'description': row['description'],
            'filename': row['filename'],
            'file_size': row['file_size'],
            'mime_type': row['mime_type'],
            'uploaded_at': row['uploaded_at'].isoformat() if row['uploaded_at'] else None,
            'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None,
            'uploader': {'id': row['uploader_id'], 'username': row['uploader_name']},
            'document_type': {'id': row['document_type_id'], 'name': row['document_type_name']},
            'plants': row['plant_names'],
            'departments': row['department_names'],
        })

    total_pages = (total_count + per_page - 1) // per_page
    return jsonify({
        'data': documents,
        'page': page,
        'per_page': per_page,
        'total_count': total_count,
        'total_pages': total_pages,
    })

@main.route('/documents/<int:document_id>/update', methods=['POST'])
@admin_required
def update_document(document_id):
    payload = request.get_json(silent=True) or request.form

    title = payload.get('title')
    description = payload.get('description')
    document_type_id = payload.get('document_type_id')
    if request.is_json:
        plant_ids = payload.get('plant_ids', [])
        department_ids = payload.get('department_ids', [])
    else:
        plant_ids = payload.getlist('plant_ids')
        department_ids = payload.getlist('department_ids')

    if not title:
        return jsonify({'error': 'Title is required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE documents
            SET title = %s,
                description = %s,
                document_type_id = %s,
                updated_at = NOW()
            WHERE id = %s
            RETURNING id
        ''', (title, description, document_type_id, document_id))
        updated = cursor.fetchone()
        if not updated:
            conn.rollback()
            return jsonify({'error': 'Document not found'}), 404

        cursor.execute('DELETE FROM document_plants WHERE document_id = %s', (document_id,))
        cursor.execute('DELETE FROM document_departments WHERE document_id = %s', (document_id,))

        for plant_id in plant_ids:
            cursor.execute('INSERT INTO document_plants (document_id, plant_id) VALUES (%s, %s)', (document_id, plant_id))
        for department_id in department_ids:
            cursor.execute('INSERT INTO document_departments (document_id, department_id) VALUES (%s, %s)', (document_id, department_id))

        conn.commit()
        return jsonify({'message': 'Document updated successfully'})
    except Exception as e:
        current_app.logger.error(f"Error updating document {document_id}: {e}")
        conn.rollback()
        return jsonify({'error': 'Failed to update document'}), 500
    finally:
        cursor.close()
        conn.close()

@main.route('/documents/<int:document_id>')
@login_required
def document_detail(document_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Build detail query with joins
    detail_query = '''
        SELECT d.id, d.title, d.description, d.filename, d.file_path, d.file_size,
               d.mime_type, d.uploaded_at, d.updated_at,
               u.id AS uploader_id, u.username AS uploader_name,
               dt.id AS document_type_id, dt.name AS document_type_name,
               STRING_AGG(DISTINCT p.name, ', ') AS plant_names,
               STRING_AGG(DISTINCT dept.name, ', ') AS department_names
        FROM documents d
        JOIN users u ON d.uploaded_by = u.id
        JOIN document_types dt ON d.document_type_id = dt.id
        LEFT JOIN document_plants dp ON d.id = dp.document_id
        LEFT JOIN plants p ON dp.plant_id = p.id
        LEFT JOIN document_departments dd ON d.id = dd.document_id
        LEFT JOIN departments dept ON dd.department_id = dept.id
        WHERE d.id = %s
        GROUP BY d.id, u.id, dt.id
    '''
    params = [document_id]

    # Restrict for non-admin
    if session.get('role') != 'admin':
        plant_ids = session.get('plant_ids', [])
        department_ids = session.get('department_ids', [])
        if not plant_ids or not department_ids:
            flash('User session missing plant or department information.')
            return redirect(url_for('main.login'))
        
        cursor.execute('''
            SELECT 1 FROM document_plants dp
            JOIN document_departments dd ON dp.document_id = dd.document_id
            WHERE dp.document_id = %s AND dp.plant_id = ANY(%s) AND dd.department_id = ANY(%s)
        ''', (document_id, plant_ids, department_ids))
        if not cursor.fetchone():
            abort(404)

    cursor.execute(detail_query, params)
    row = cursor.fetchone()

    cursor.close()
    conn.close()

    if not row:
        abort(404)

    shaped_document = {
        'id': row['id'],
        'title': row['title'],
        'description': row['description'],
        'filename': row['filename'],
        'file_path': row['file_path'],
        'file_size': row['file_size'],
        'mime_type': row['mime_type'],
        'uploaded_at': row['uploaded_at'],
        'updated_at': row['updated_at'],
        'uploader': {
            'id': row['uploader_id'],
            'username': row['uploader_name'],
        },
        'document_type': {
            'id': row['document_type_id'],
            'name': row['document_type_name'],
        },
        'plants': row['plant_names'],
        'departments': row['department_names'],
    }

    return render_template('document_detail.html', document=shaped_document, user={'role': session.get('role', 'user')})

@main.route('/api/plants')
@login_required
def api_plants():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM plants ORDER BY name')
    plants = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(plants)

@main.route('/api/departments')
@login_required
def api_departments():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM departments ORDER BY name')
    departments = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(departments)

@main.route('/api/document-types')
@login_required
def api_document_types():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM document_types ORDER BY name')
    document_types = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(document_types)

@main.route('/api/user/profile')
@login_required
def api_user_profile():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''SELECT u.username, u.role, STRING_AGG(p.name, ', ') as plant_name, STRING_AGG(d.name, ', ') as department_name 
                      FROM users u 
                      LEFT JOIN user_plants up ON u.id = up.user_id
                      LEFT JOIN plants p ON up.plant_id = p.id 
                      LEFT JOIN user_departments ud ON u.id = ud.user_id
                      LEFT JOIN departments d ON ud.department_id = d.id 
                      WHERE u.id = %s
                      GROUP BY u.id''', (session['user_id'],))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    if user:
        return jsonify(user)
    return jsonify({'error': 'User not found'}), 404

@main.route('/documents/upload', methods=['GET', 'POST'])
@admin_required
def upload_document():
    if request.method == 'POST':
        if 'file' not in request.files:
            current_app.logger.warning('File upload failed: No file selected')
            return jsonify({'error': 'No file selected'}), 400
        
        file = request.files['file']
        if file.filename == '':
            current_app.logger.warning('File upload failed: No file selected')
            return jsonify({'error': 'No file selected'}), 400

        # Pass the file stream to allowed_file
        if file and allowed_file(file.filename, file.stream):
            try:
                filename = secure_filename(file.filename)

                plant_ids = request.form.getlist('plant_ids')
                department_ids = request.form.getlist('department_ids')

                if not plant_ids or not department_ids:
                    current_app.logger.warning('File upload failed: Plant and department information required')
                    return jsonify({'error': 'Plant and department information required'}), 400

                # Create directory structure: UPLOAD_FOLDER/year/month/day
                upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], datetime.now().strftime('%Y/%m/%d'))
                os.makedirs(upload_dir, exist_ok=True)

                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)

                # Detect MIME type (extension + magic fallback) - this is now handled by allowed_file
                # For saving to DB, we can use mimetypes.guess_type or magic.from_file again if we want the exact detected type.
                mime_type, _ = mimetypes.guess_type(file_path)
                if mime_type is None:
                    mime_type = 'application/octet-stream' # Default if detection fails

                # Save to database
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO documents (title, description, filename, file_path, file_size, mime_type, uploaded_by, document_type_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
                ''', (
                    request.form.get('title', filename),
                    request.form.get('description', ''),
                    filename,
                    file_path,
                    os.path.getsize(file_path),
                    mime_type,
                    session['user_id'],
                    request.form.get('document_type_id')
                ))
                document_id = cursor.fetchone()['id']

                for plant_id in plant_ids:
                    cursor.execute('INSERT INTO document_plants (document_id, plant_id) VALUES (%s, %s)', (document_id, plant_id))
                for department_id in department_ids:
                    cursor.execute('INSERT INTO document_departments (document_id, department_id) VALUES (%s, %s)', (document_id, department_id))

                conn.commit()
                cursor.close()
                conn.close()

                current_app.log_audit(current_app, 'document_upload', user_id=session['user_id'], details=f'Document \'{filename}\' (ID: {document_id}) uploaded')
                current_app.logger.info(f'Document {filename} uploaded successfully by user {session["username"]}')
                return jsonify({'message': 'Document uploaded successfully'})

            except Exception as e:
                current_app.logger.error(f"Error during file upload: {e}")
                return jsonify({'error': f'Upload failed: {str(e)}'}), 500
        else:
            current_app.logger.warning(f'File upload failed: File type not allowed for file {file.filename}')
            return jsonify({'error': 'File type not allowed or invalid'}), 400 # Updated error message
    # GET request
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM document_types ORDER BY name')
    document_types = cursor.fetchall()
    cursor.execute('SELECT id, name FROM plants ORDER BY name')
    plants = cursor.fetchall()
    cursor.execute('SELECT id, name FROM departments ORDER BY name')
    departments = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('upload.html', document_types=document_types, plants=plants, departments=departments)

import csv

@main.route('/documents/bulk-upload', methods=['GET', 'POST'])
@admin_required
def bulk_upload():
    if request.method == 'POST':
        files = request.files.getlist('files')
        metadata_file = request.files.get('metadata_file')

        if not files:
            return jsonify({'error': 'No files provided'}), 400

        plant_ids = request.form.getlist('plant_ids')
        department_ids = request.form.getlist('department_ids')
        document_type_id = request.form.get('document_type_id')

        if not plant_ids or not department_ids or not document_type_id:
            return jsonify({'error': 'Plant, department, and document type are required'}), 400

        metadata = {}
        if metadata_file:
            try:
                decoded_file = metadata_file.read().decode('utf-8')
                csv_reader = csv.DictReader(decoded_file.splitlines())
                for row in csv_reader:
                    metadata[row['filename']] = {
                        'title': row.get('title'),
                        'description': row.get('description')
                    }
            except Exception as e:
                current_app.logger.error(f"Error processing metadata file: {e}")
                return jsonify({'error': 'Invalid metadata file'}), 400

        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'bulk', datetime.now().strftime('%Y%m%d%H%M%S'))
        os.makedirs(upload_dir, exist_ok=True)

        saved = 0
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            for f in files:
                # Pass the file stream to allowed_file
                if not f or f.filename == '' or not allowed_file(f.filename, f.stream):
                    current_app.logger.warning(f'Bulk upload failed: File type not allowed or invalid for file {f.filename}')
                    # Continue to next file, but log the error
                    continue

                filename = secure_filename(f.filename)
                file_path = os.path.join(upload_dir, filename)
                f.save(file_path)

                mime_type, _ = mimetypes.guess_type(file_path)
                if mime_type is None:
                    mime_type = 'application/octet-stream'

                doc_metadata = metadata.get(filename, {})
                title = doc_metadata.get('title') or filename
                description = doc_metadata.get('description') or ''

                cursor.execute('''
                    INSERT INTO documents (title, description, filename, file_path, file_size, mime_type, uploaded_by, document_type_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
                ''', (
                    title,
                    description,
                    filename,
                    file_path,
                    os.path.getsize(file_path),
                    mime_type,
                    session['user_id'],
                    document_type_id
                ))
                document_id = cursor.fetchone()['id']

                for plant_id in plant_ids:
                    cursor.execute('INSERT INTO document_plants (document_id, plant_id) VALUES (%s, %s)', (document_id, plant_id))
                for department_id in department_ids:
                    cursor.execute('INSERT INTO document_departments (document_id, department_id) VALUES (%s, %s)', (document_id, department_id))

                saved += 1
            conn.commit()
        except Exception as e:
            current_app.logger.error(f"Bulk upload error: {e}")
            conn.rollback()
            return jsonify({'error': 'Bulk upload failed'}), 500
        finally:
            cursor.close()
            conn.close()

        return jsonify({'message': f'Uploaded {saved} files successfully'})

    # GET
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM document_types ORDER BY name')
    document_types = cursor.fetchall()
    cursor.execute('SELECT id, name FROM plants ORDER BY name')
    plants = cursor.fetchall()
    cursor.execute('SELECT id, name FROM departments ORDER BY name')
    departments = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('bulk_upload.html', document_types=document_types, plants=plants, departments=departments)

# --- Admin User Management ---
@main.route('/admin/users')
@admin_required
def admin_users():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.id, u.username, u.role, u.is_active, u.created_at, u.last_login,
               COALESCE(STRING_AGG(p.name, ', '), '') as plant_name, COALESCE(STRING_AGG(d.name, ', '), '') as department_name
        FROM users u
        LEFT JOIN user_plants up ON u.id = up.user_id
        LEFT JOIN plants p ON up.plant_id = p.id
        LEFT JOIN user_departments ud ON u.id = ud.user_id
        LEFT JOIN departments d ON ud.department_id = d.id
        GROUP BY u.id
        ORDER BY u.created_at DESC
    ''')
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin_users.html', users=users)

@main.route('/admin/users/create', methods=['POST'])
@admin_required
def admin_users_create():
    # Determine if the request is JSON or form data
    if request.is_json:
        payload = request.get_json()
        # For JSON, getlist is not applicable, assume lists are directly provided
        plant_ids = payload.get('plant_ids', [])
        department_ids = payload.get('department_ids', [])
    else:
        payload = request.form
        plant_ids = payload.getlist('plant_ids')
        department_ids = payload.getlist('department_ids')

    username = payload.get('username')
    password = payload.get('password')
    role = payload.get('role', 'user')

    current_app.logger.info(f"Attempting to create user: {username}, Role: {role}, Plants: {plant_ids}, Departments: {department_ids}")

    if not username or not password:
        current_app.logger.warning("User creation failed: Username or password missing.")
        return jsonify({'error': 'Username and password are required'}), 400

    if role != 'admin' and (not plant_ids or not department_ids):
        current_app.logger.warning(f"User creation failed for {username}: Non-admin user requires plant and department IDs.")
        return jsonify({'error': 'Users must have at least one plant and one department'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check if username already exists
        cursor.execute('SELECT id FROM users WHERE username = %s', (username,))
        if cursor.fetchone():
            current_app.logger.warning(f"User creation failed: Username '{username}' already exists.")
            return jsonify({'error': f'Username \'{username}\' already exists. Please choose a different username.'}), 409 # Conflict

        cursor.execute('INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s) RETURNING id', (
            username, generate_password_hash(password, method='pbkdf2:sha256'), role
        ))
        user_id = cursor.fetchone()['id']

        for plant_id in plant_ids:
            cursor.execute('INSERT INTO user_plants (user_id, plant_id) VALUES (%s, %s)', (user_id, plant_id))
        for department_id in department_ids:
            cursor.execute('INSERT INTO user_departments (user_id, department_id) VALUES (%s, %s)', (user_id, department_id))

        conn.commit()
        current_app.log_audit(current_app, 'user_create', user_id=session['user_id'], details=f'User {username} created')
        current_app.logger.info(f"User {username} created successfully with ID: {user_id}")
        return jsonify({'message': 'User created'}), 201 # Return 201 Created
    except psycopg2.Error as e:
        current_app.logger.error(f"Database error during user creation for {username}: {e}")
        conn.rollback()
        return jsonify({'error': f'Database error: {e.pgcode} - {e.pgerror}'}), 500
    except Exception as e:
        current_app.logger.error(f"Create user error for {username}: {e}", exc_info=True) # Add exc_info=True for full traceback
        conn.rollback()
        return jsonify({'error': 'Failed to create user due to an unexpected error'}), 500
    finally:
        cursor.close()
        conn.close()

@main.route('/admin/users/<int:user_id>/reset-password', methods=['POST'])
@admin_required
def admin_users_reset_password(user_id):
    payload = request.get_json(silent=True) or request.form
    new_password = payload.get('password')
    if not new_password:
        return jsonify({'error': 'Password is required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE users SET password_hash = %s WHERE id = %s RETURNING id', (
            generate_password_hash(new_password, method='pbkdf2:sha256'), user_id
        ))
        updated = cursor.fetchone()
        if not updated:
            conn.rollback()
            return jsonify({'error': 'User not found'}), 404
        conn.commit()
        return jsonify({'message': 'Password reset successful'})
    except Exception as e:
        current_app.logger.error(f"Reset password error: {e}")
        conn.rollback()
        return jsonify({'error': 'Failed to reset password'}), 500
    finally:
        cursor.close()
        conn.close()

@main.route('/admin/users/<int:user_id>/update', methods=['POST'])
@admin_required
def admin_users_update(user_id):
    if request.is_json:
        payload = request.get_json()
        plant_ids = payload.get('plant_ids', [])
        department_ids = payload.get('department_ids', [])
    else:
        payload = request.form
        plant_ids = payload.getlist('plant_ids')
        department_ids = payload.getlist('department_ids')

    username = payload.get('username')
    role = payload.get('role', 'user')

    if not username:
        return jsonify({'error': 'Username is required'}), 400

    if role != 'admin' and (not plant_ids or not department_ids):
        return jsonify({'error': 'Users must have at least one plant and one department'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''UPDATE users SET username = %s, role = %s WHERE id = %s RETURNING id''', (
            username, role, user_id
        ))
        updated = cursor.fetchone()
        if not updated:
            conn.rollback()
            return jsonify({'error': 'User not found'}), 404

        cursor.execute('DELETE FROM user_plants WHERE user_id = %s', (user_id,))
        cursor.execute('DELETE FROM user_departments WHERE user_id = %s', (user_id,))

        for plant_id in plant_ids:
            cursor.execute('INSERT INTO user_plants (user_id, plant_id) VALUES (%s, %s)', (user_id, plant_id))
        for department_id in department_ids:
            cursor.execute('INSERT INTO user_departments (user_id, department_id) VALUES (%s, %s)', (user_id, department_id))

        conn.commit()
        current_app.log_audit(current_app, 'user_update', user_id=session['user_id'], details=f'User {username} (ID: {user_id}) updated')
        return jsonify({'message': 'User updated'})
    except Exception as e:
        current_app.logger.error(f"Update user error: {e}")
        conn.rollback()
        return jsonify({'error': 'Failed to update user'}), 500
    finally:
        cursor.close()
        conn.close()

@main.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def admin_users_delete(user_id):
    # User deletion is disabled as per requirement.
    current_app.log_audit(current_app, 'user_delete_attempt', user_id=session['user_id'], details=f'Attempted to delete user ID: {user_id} (deletion disabled)')
    current_app.logger.warning(f"User deletion attempted for ID: {user_id}, but deletion is disabled.")
    return jsonify({'error': 'User deletion is currently disabled.'}), 403 # Forbidden

@main.route('/admin/users/<int:user_id>/activate', methods=['POST'])
@admin_required
def activate_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE users SET is_active = TRUE WHERE id = %s RETURNING id', (user_id,))
        updated = cursor.fetchone()
        if not updated:
            conn.rollback()
            return jsonify({'error': 'User not found'}), 404
        conn.commit()
        current_app.log_audit(current_app, 'user_activate', user_id=session['user_id'], details=f'User ID {user_id} activated')
        return jsonify({'message': 'User activated successfully'})
    except Exception as e:
        current_app.logger.error(f"Activate user error: {e}")
        conn.rollback()
        return jsonify({'error': 'Failed to activate user'}), 500
    finally:
        cursor.close()
        conn.close()

@main.route('/admin/users/<int:user_id>/deactivate', methods=['POST'])
@admin_required
def deactivate_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE users SET is_active = FALSE WHERE id = %s RETURNING id', (user_id,))
        updated = cursor.fetchone()
        if not updated:
            conn.rollback()
            return jsonify({'error': 'User not found'}), 404
        conn.commit()
        current_app.log_audit(current_app, 'user_deactivate', user_id=session['user_id'], details=f'User ID {user_id} deactivated')
        return jsonify({'message': 'User deactivated successfully'})
    except Exception as e:
        current_app.logger.error(f"Deactivate user error: {e}")
        conn.rollback()
        return jsonify({'error': 'Failed to deactivate user'}), 500
    finally:
        cursor.close()
        conn.close()

@main.route('/admin/departments/add', methods=['GET', 'POST'])
@admin_required
def add_department():
    if request.method == 'POST':
        department_name = request.form.get('name')
        print(f"Session CSRF Token: {session.get('_csrf_token')}")
        print(f"Request Form CSRF Token: {request.form.get('csrf_token')}")
        if not department_name:
            flash('Department name is required', 'danger')
            return redirect(url_for('main.add_department'))

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO departments (name) VALUES (%s) ON CONFLICT (name) DO NOTHING RETURNING id', (department_name,))
            new_department = cursor.fetchone()
            conn.commit()
            if new_department:
                flash(f'Department "{department_name}" added successfully', 'success')
                current_app.log_audit(current_app, 'add_department', user_id=session['user_id'], details=f'Department "{department_name}" (ID: {new_department["id"]}) added')
            else:
                flash(f'Department "{department_name}" already exists', 'warning')
            return redirect(url_for('main.add_department'))
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            flash(f'Department "{department_name}" already exists', 'warning')
            return redirect(url_for('main.add_department'))
        except Exception as e:
            current_app.logger.error(f"Error adding department: {e}")
            conn.rollback()
            flash('Failed to add department', 'danger')
            return redirect(url_for('main.add_department'))
        finally:
            cursor.close()
            conn.close()
    return render_template('add_department.html')

@main.route('/admin/departments/<int:department_id>/delete', methods=['POST'])
@admin_required
def delete_department(department_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT name FROM departments WHERE id = %s', (department_id,))
        department = cursor.fetchone()
        if not department:
            return jsonify({'error': 'Department not found'}), 404

        cursor.execute('DELETE FROM departments WHERE id = %s', (department_id,))
        conn.commit()
        current_app.log_audit(current_app, 'delete_department', user_id=session['user_id'], details=f'Department "{department["name"]}" (ID: {department_id}) deleted')
        return jsonify({'message': 'Department deleted successfully'}), 200
    except psycopg2.errors.ForeignKeyViolation:
        conn.rollback()
        return jsonify({'error': 'Cannot delete department because there are documents or users associated with it. Please reassign or delete associated items first.'}), 409 # Conflict
    except Exception as e:
        current_app.logger.error(f"Error deleting department {department_id}: {e}")
        conn.rollback()
        return jsonify({'error': 'Failed to delete department'}), 500
    finally:
        cursor.close()
        conn.close()


@main.route('/admin/document-types/<int:document_type_id>/delete', methods=['POST'])
@admin_required
def delete_document_type(document_type_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT name FROM document_types WHERE id = %s', (document_type_id,))
        document_type = cursor.fetchone()
        if not document_type:
            return jsonify({'error': 'Document type not found'}), 404

        cursor.execute('DELETE FROM document_types WHERE id = %s', (document_type_id,))
        conn.commit()
        current_app.log_audit(current_app, 'delete_document_type', user_id=session['user_id'], details=f'Document type "{document_type["name"]}" (ID: {document_type_id}) deleted')
        return jsonify({'message': 'Document type deleted successfully'}), 200
    except psycopg2.errors.ForeignKeyViolation:
        conn.rollback()
        return jsonify({'error': 'Cannot delete document type because there are documents associated with it. Please reassign or delete associated documents first.'}), 409 # Conflict
    except Exception as e:
        current_app.logger.error(f"Error deleting document type {document_type_id}: {e}")
        conn.rollback()
        return jsonify({'error': 'Failed to delete document type'}), 500
    finally:
        cursor.close()
        conn.close()


@main.route('/admin/departments')
@admin_required
def admin_departments():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM departments ORDER BY name')
    departments = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin_departments.html', departments=departments)


@main.route('/admin/document-types')
@admin_required
def admin_document_types():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM document_types ORDER BY name')
    document_types = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin_document_types.html', document_types=document_types)


@main.route('/admin/document-types/add', methods=['GET', 'POST'])
@admin_required
def add_document_type():
    if request.method == 'POST':
        document_type_name = request.form.get('name')
        print(f"Session CSRF Token: {session.get('_csrf_token')}")
        print(f"Request Form CSRF Token: {request.form.get('csrf_token')}")
        if not document_type_name:
            flash('Document type name is required', 'danger')
            return redirect(url_for('main.add_document_type'))

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO document_types (name) VALUES (%s) ON CONFLICT (name) DO NOTHING RETURNING id', (document_type_name,))
            new_document_type = cursor.fetchone()
            conn.commit()
            if new_document_type:
                flash(f'Document type "{document_type_name}" added successfully', 'success')
                current_app.log_audit(current_app, 'add_document_type', user_id=session['user_id'], details=f'Document type "{document_type_name}" (ID: {new_document_type["id"]}) added')
            else:
                flash(f'Document type "{document_type_name}" already exists', 'warning')
            return redirect(url_for('main.add_document_type'))
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            flash(f'Document type "{document_type_name}" already exists', 'warning')
            return redirect(url_for('main.add_document_type'))
        except Exception as e:
            current_app.logger.error(f"Error adding document type: {e}")
            conn.rollback()
            flash('Failed to add document type', 'danger')
            return redirect(url_for('main.add_document_type'))
        finally:
            cursor.close()
            conn.close()
    return render_template('add_document_type.html')


@main.route('/request-document', methods=['GET', 'POST'])
@login_required
def request_new_document():
    if request.method == 'POST':
        payload = request.get_json(silent=True)
        document_description = payload.get('document_description')
        document_type_id = payload.get('document_type_id')
        requested_format = payload.get('requested_format')

        if not document_description or not document_type_id or not requested_format:
            return jsonify({'error': 'Document description, document type, and requested format are required'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Fetch document type name for notification
            cursor.execute('SELECT name FROM document_types WHERE id = %s', (document_type_id,))
            document_type_name = cursor.fetchone()['name'] if cursor.rowcount > 0 else 'Unknown Type'

            cursor.execute('''
                INSERT INTO document_requests (user_id, requested_document_description, document_type_id, requested_format)
                VALUES (%s, %s, %s, %s)
            ''', (session['user_id'], document_description, document_type_id, requested_format))

            admin_notification_message = f"User {session['username']} requested a new document: '{document_description}' (Type: {document_type_name}) in format '{requested_format}'."
            cursor.execute('''
                INSERT INTO admin_notifications (user_id, document_id, requested_document_description, message)
                VALUES (%s, NULL, %s, %s)
            ''', (session['user_id'], document_description, admin_notification_message))
            conn.commit()
            current_app.log_audit(current_app, 'new_document_request', user_id=session['user_id'], details=f'User requested new document: {document_description} in format {requested_format}')
            return jsonify({'message': 'Document request submitted successfully'}), 201
        except Exception as e:
            current_app.logger.error(f"Error submitting new document request: {e}")
            conn.rollback()
            return jsonify({'error': 'Failed to submit document request'}), 500
        finally:
            cursor.close()
            conn.close()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM document_types ORDER BY name')
    document_types = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('request_document_form.html', document_types=document_types)

@main.route('/document/<int:document_id>/request_format', methods=['POST'])
@login_required
def request_document_format(document_id):
    payload = request.get_json(silent=True)
    requested_format = payload.get('requested_format')

    if not requested_format:
        return jsonify({'error': 'Requested format is required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO document_requests (user_id, document_id, requested_document_description, requested_format)
            VALUES (%s, %s, NULL, %s)
        ''', (session['user_id'], document_id, requested_format))

        # Insert into admin_notifications
        admin_notification_message = f"User {session['username']} requested format '{requested_format}' for document ID: {document_id}."
        cursor.execute('''
            INSERT INTO admin_notifications (user_id, document_id, requested_document_description, message)
            VALUES (%s, %s, NULL, %s)
        ''', (session['user_id'], document_id, admin_notification_message))
        conn.commit()
        current_app.log_audit(current_app, 'document_format_request', user_id=session['user_id'], details=f'User requested format \'{requested_format}\' for document ID: {document_id}')
        return jsonify({'message': 'Format request submitted successfully'})
    except Exception as e:
        current_app.logger.error(f"Error submitting format request: {e}")
        conn.rollback()
        return jsonify({'error': 'Failed to submit format request'}), 500
    finally:
        cursor.close()
        conn.close()

@main.route('/admin/requests')
@admin_required
def admin_requests():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT dr.id, u.username, d.title AS document_title, dr.document_id, dr.requested_document_description, dt.name AS requested_document_type_name, dr.requested_format, dr.status, dr.created_at
        FROM document_requests dr
        JOIN users u ON dr.user_id = u.id
        LEFT JOIN documents d ON dr.document_id = d.id
        LEFT JOIN document_types dt ON d.document_type_id = dt.id
        ORDER BY dr.created_at DESC
    ''')
    requests = cursor.fetchall()

    cursor.execute('''
        SELECT an.id, u.username, d.title AS document_title, an.document_id, an.requested_document_description, an.message, an.created_at
        FROM admin_notifications an
        JOIN users u ON an.user_id = u.id
        LEFT JOIN documents d ON an.document_id = d.id
        ORDER BY an.created_at DESC
    ''')
    notifications = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template('requests.html', requests=requests, notifications=notifications)

@main.route('/admin/requests/<int:request_id>/update', methods=['POST'])
@admin_required
def update_request_status(request_id):
    payload = request.get_json(silent=True)
    status = payload.get('status')

    if not status or status not in ['fulfilled', 'rejected']:
        return jsonify({'error': 'Invalid status'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE document_requests SET status = %s WHERE id = %s', (status, request_id))
        conn.commit()
        current_app.log_audit(current_app, 'document_request_update', user_id=session['user_id'], details=f'Request ID {request_id} status updated to {status}')
        return jsonify({'message': 'Request status updated'})
    except Exception as e:
        current_app.logger.error(f"Error updating request status: {e}")
        conn.rollback()
        return jsonify({'error': 'Failed to update request status'}), 500
    finally:
        cursor.close()
        conn.close()

@main.route('/admin/requests/<int:request_id>/delete', methods=['POST'])
@admin_required
def delete_document_request(request_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT id FROM document_requests WHERE id = %s', (request_id,))
        request_to_delete = cursor.fetchone()
        if not request_to_delete:
            return jsonify({'error': 'Document request not found'}), 404

        cursor.execute('DELETE FROM document_requests WHERE id = %s', (request_id,))
        conn.commit()
        current_app.log_audit(current_app, 'document_request_delete', user_id=session['user_id'], details=f'Document request ID {request_id} deleted')
        return jsonify({'message': 'Document request deleted successfully'}), 200
    except Exception as e:
        current_app.logger.error(f"Error deleting document request {request_id}: {e}")
        conn.rollback()
        return jsonify({'error': 'Failed to delete document request'}), 500
    finally:
        cursor.close()
        conn.close()

                    
@main.route('/documents/<int:document_id>/download')
@login_required
def download_document(document_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = 'SELECT * FROM documents WHERE id = %s'
    params = [document_id]

    if session.get('role') != 'admin':
        plant_ids = session.get('plant_ids', [])
        department_ids = session.get('department_ids', [])
        if not plant_ids or not department_ids:
            abort(403)  # Forbidden
        
        cursor.execute('''
            SELECT 1 FROM document_plants dp
            JOIN document_departments dd ON dp.document_id = dd.document_id
            WHERE dp.document_id = %s AND dp.plant_id = ANY(%s) AND dd.department_id = ANY(%s)
        ''', (document_id, plant_ids, department_ids))
        if not cursor.fetchone():
            abort(403)

    cursor.execute(query, params)
    document = cursor.fetchone()
    if not document:
        cursor.close()
        conn.close()
        abort(404)
    
    # Log download
    cursor.execute('INSERT INTO download_logs (document_id, user_id) VALUES (%s, %s)', (document_id, session['user_id']))
    conn.commit()
    cursor.close()
    conn.close()
    
    current_app.logger.info(f'Document {document["filename"]} downloaded by user {session["username"]}')
    return send_file(document['file_path'], as_attachment=True, download_name=document['filename'])

@main.route('/audit-logs')
@admin_required
def audit_logs():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch all users and documents for filter dropdowns
    cursor.execute('SELECT id, username FROM users ORDER BY username')
    all_users = cursor.fetchall()
    cursor.execute('SELECT id, title FROM documents ORDER BY title')
    all_documents = cursor.fetchall()

    # Filters & pagination
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
    except ValueError:
        page = 1
        per_page = 20
    page = max(page, 1)
    per_page = max(min(per_page, 100), 1)

    user_filter = request.args.get('user_id')
    action_filter = request.args.get('action')
    document_filter = request.args.get('document_id') # New filter
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # --- Query for audit_logs ---
    audit_log_base_query = '''
        SELECT al.id, al.timestamp, al.action, al.details,
               u.username AS username, NULL AS document_title, NULL AS document_id, 'audit' AS log_type
        FROM audit_logs al
        LEFT JOIN users u ON al.user_id = u.id
    '''
    audit_log_where_clauses = []
    audit_log_params = []

    if user_filter:
        audit_log_where_clauses.append('u.id = %s')
        audit_log_params.append(user_filter)
    if action_filter and action_filter != 'document_download': # Only apply if not filtering specifically for downloads
        audit_log_where_clauses.append('al.action = %s')
        audit_log_params.append(action_filter)
    if start_date:
        audit_log_where_clauses.append('al.timestamp >= %s')
        audit_log_params.append(start_date)
    if end_date:
        audit_log_where_clauses.append('al.timestamp <= %s')
        audit_log_params.append(end_date)

    audit_log_query = audit_log_base_query
    if audit_log_where_clauses:
        audit_log_query += ' WHERE ' + ' AND '.join(audit_log_where_clauses)

    # --- Query for download_logs ---
    download_log_base_query = '''
        SELECT dl.id, dl.downloaded_at AS timestamp, 'document_download' AS action,
               d.title AS details, u.username AS username, d.title AS document_title, d.id AS document_id, 'download' AS log_type
        FROM download_logs dl
        JOIN users u ON dl.user_id = u.id
        JOIN documents d ON dl.document_id = d.id
    '''
    download_log_where_clauses = []
    download_log_params = []

    if user_filter:
        download_log_where_clauses.append('u.id = %s')
        download_log_params.append(user_filter)
    if document_filter:
        download_log_where_clauses.append('d.id = %s')
        download_log_params.append(document_filter)
    if start_date:
        download_log_where_clauses.append('dl.downloaded_at >= %s')
        download_log_params.append(start_date)
    if end_date:
        download_log_where_clauses.append('dl.downloaded_at <= %s')
        download_log_params.append(end_date)

    download_log_query = download_log_base_query
    if download_log_where_clauses:
        download_log_query += ' WHERE ' + ' AND '.join(download_log_where_clauses)

    # Construct the combined query for total count
    total_count = 0
    if not action_filter or action_filter == 'document_download':
        cursor.execute(f'SELECT COUNT(*) FROM ({download_log_query}) AS dl_sub', download_log_params)
        total_count += cursor.fetchone()['count']
    if not action_filter or action_filter != 'document_download':
        cursor.execute(f'SELECT COUNT(*) FROM ({audit_log_query}) AS al_sub', audit_log_params)
        total_count += cursor.fetchone()['count']

    # Construct the combined query for paginated logs
    combined_log_query_parts = []
    if not action_filter or action_filter == 'document_download':
        combined_log_query_parts.append(download_log_query)
    if not action_filter or action_filter != 'document_download':
        combined_log_query_parts.append(audit_log_query)

    combined_query = ' UNION ALL '.join(combined_log_query_parts)
    combined_query += ' ORDER BY timestamp DESC LIMIT %s OFFSET %s'

    # Combine parameters for the final query
    combined_params = []
    if not action_filter or action_filter == 'document_download':
        combined_params.extend(download_log_params)
    if not action_filter or action_filter != 'document_download':
        combined_params.extend(audit_log_params)

    combined_params.extend([per_page, (page - 1) * per_page])

    cursor.execute(combined_query, combined_params)
    logs = cursor.fetchall()

    total_pages = (total_count + per_page - 1) // per_page
    cursor.close()
    conn.close()
    return render_template(
        'audit_logs.html',
        logs=logs,
        page=page,
        per_page=per_page,
        total_count=total_count,
        total_pages=total_pages,
        all_users=all_users,        # Pass for filter dropdown
        all_documents=all_documents,  # Pass for filter dropdown
        selected_user=user_filter,    # Pass back selected filter
        selected_action=action_filter,
        selected_document=document_filter,
        selected_start_date=start_date,
        selected_end_date=end_date
    )

@main.route('/admin/notifications/<int:notification_id>/mark-read', methods=['POST'])
@admin_required
def mark_notification_read(notification_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM admin_notifications WHERE id = %s', (notification_id,))
        conn.commit()
        current_app.log_audit(current_app, 'admin_notification_delete', user_id=session['user_id'], details=f'Admin notification ID {notification_id} deleted')
        return jsonify({'message': 'Notification deleted successfully'})
    except Exception as e:
        current_app.logger.error(f"Error marking notification {notification_id} as read: {e}")
        conn.rollback()
        return jsonify({'error': 'Failed to mark notification as read'}), 500
    finally:
        cursor.close()
        conn.close()




@main.route('/documents/<int:document_id>/delete', methods=['POST'])
@admin_required
def delete_document(document_id):
    current_app.logger.info(f'Attempting to delete document with ID: {document_id}')
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Delete from admin_notifications first
        cursor.execute('DELETE FROM admin_notifications WHERE document_id = %s', (document_id,))

        cursor.execute('SELECT file_path, filename FROM documents WHERE id = %s', (document_id,))
        document = cursor.fetchone()

        if not document:
            current_app.logger.warning(f'Document with ID {document_id} not found for deletion.')
            return jsonify({'error': 'Document not found'}), 404

        # Delete from database
        current_app.logger.info(f'Deleting document {document_id} from database')
        cursor.execute('DELETE FROM document_plants WHERE document_id = %s', (document_id,))
        cursor.execute('DELETE FROM document_departments WHERE document_id = %s', (document_id,))
        cursor.execute('DELETE FROM download_logs WHERE document_id = %s', (document_id,))
        cursor.execute('DELETE FROM documents WHERE id = %s', (document_id,))
        conn.commit()
        current_app.logger.info(f'Document {document_id} deleted from database')

        # Delete physical file
        current_app.logger.info(f'Deleting physical file for document {document_id}')
        if os.path.exists(document['file_path']):
            os.remove(document['file_path'])
            current_app.logger.info(f'Physical file for document {document_id} deleted')
        else:
            current_app.logger.warning(f'Physical file for document {document_id} not found')
        
        current_app.log_audit(current_app, 'document_delete', user_id=session['user_id'], details=f'Document \'{document["filename"]}\' (ID: {document_id}) deleted')
        current_app.logger.info(f'Document with id {document_id} deleted by user {session["username"]}')
        return jsonify({'message': 'Document deleted successfully'}), 200

    except psycopg2.Error as e:
        current_app.logger.error(f"Database error during document deletion: {e}")
        conn.rollback()
        return jsonify({'error': 'Failed to delete document'}), 500
    except Exception as e:
        current_app.logger.error(f"Error deleting physical file: {e}")
        return jsonify({'error': 'Failed to delete physical file'}), 500
    finally:
        cursor.close()
        conn.close()

# Error handlers
@main.app_errorhandler(403)
def forbidden(error):
    current_app.logger.warning(f'Forbidden access attempt by user {session.get("username", "anonymous")}')
    return render_template('error.html', error_code=403, error_message="Access denied"), 403

@main.app_errorhandler(404)
def not_found(error):
    return render_template('error.html', error_code=404, error_message="Page not found"), 404

@main.app_errorhandler(500)
def internal_error(error):
    current_app.logger.error(f"Internal server error: {error}")
    return render_template('error.html', error_code=500, error_message="Internal server error"), 500
