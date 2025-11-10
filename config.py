import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')
MAX_CONTENT_LENGTH = int(os.environ.get('MAX_FILE_SIZE', 16 * 1024 * 1024))  # 16MB
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'jpg', 'jpeg', 'png', 'txt', 'dwg'}

# Mapping of file extensions to a list of allowed MIME types for stricter validation
ALLOWED_MIMETYPES = {
    'pdf': ['application/pdf'],
    'doc': ['application/msword'],
    'docx': ['application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/zip'],
    'xls': ['application/vnd.ms-excel'],
    'xlsx': ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/zip'],
    'ppt': ['application/vnd.openxmlformats-officedocument.presentationml.presentation'],
    'pptx': ['application/vnd.openxmlformats-officedocument.presentationml.presentation', 'application/zip'],
    'jpg': ['image/jpeg'],
    'jpeg': ['image/jpeg'],
    'png': ['image/png'],
    'txt': ['text/plain'],
    'dwg': ['image/vnd.dwg', 'application/acad', 'application/x-acad', 'application/autocad_dwg', 'application/dwg', 'application/x-dwg', 'application/x-autocad', 'drawing/dwg'],
}

DATABASE_URL = 'postgresql://dms_user:1234@localhost:5432/document_management'

# Flask Session and CSRF Configuration
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_HTTPONLY = False