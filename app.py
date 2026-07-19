import os
import logging
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, current_app

from flask_talisman import Talisman
from werkzeug.security import check_password_hash

import config
import models
import extensions # Import extensions module

# from flask_limiter import Limiter # Removed
# from flask_limiter.util import get_remote_address # Removed

from models import get_db_connection

# Configure logging
logging.basicConfig(filename='app.log', level=logging.DEBUG, format=f'%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')

# Define log_audit function here
def log_audit(app, action, user_id=None, details=None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO audit_logs (user_id, action, details) VALUES (%s, %s, %s)',
            (user_id, action, details)
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        current_app.logger.error(f"Failed to log audit event: {e}")

app = Flask(__name__)
app.config.from_object(config)
app.secret_key = app.config['SECRET_KEY']
app.debug = os.environ.get('FLASK_DEBUG') == '1'
extensions.init_app(app) # Initialize extensions here
app.log_audit = log_audit

# limiter is now initialized via extensions.init_app(app)
# limiter = Limiter(...) # Removed direct initialization

# Import blueprints AFTER app and extensions are initialized
from routes import main
app.register_blueprint(main)



# Relax Content Security Policy so external CDNs (Bootstrap/Font Awesome) load properly
csp = {
    'default-src': ["'self'"],
    'style-src': ["'self'", "'unsafe-inline'", 'https://cdn.jsdelivr.net', 'https://cdnjs.cloudflare.com', 'https://fonts.googleapis.com'],
    'script-src': ["'self'", "'unsafe-inline'", 'https://cdn.jsdelivr.net'],
    'font-src': ["'self'", 'https://cdnjs.cloudflare.com', 'data:', 'https://fonts.gstatic.com'],
    'img-src': ["'self'", 'data:', 'blob:'],
    'connect-src': ["'self'", 'https://cdn.jsdelivr.net'], # Added for .map files
}
Talisman(app, content_security_policy=csp)
