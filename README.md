# Multi-Plant Document Management System

22A comprehensive Flask-based document management system designed for multi-plant organizations with department-based access control.

## Features

### Core Functionality
- **Multi-Plant Support**: Rudrapur, Zaheerabad, and Palwal plants
- **Department-Based Access Control**: 11 departments with role-based permissions
- **Document Management**: Upload, download, view, and manage documents
- **User Authentication**: Secure login with session management
- **File Type Support**: PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX, JPG, PNG

### Security Features
- **CSRF Protection**: Flask-SeaSurf integration
- **Security Headers**: Flask-Talisman for security headers
- **Password Hashing**: Secure password storage
- **Session Management**: Flask-Session with secure configuration
- **Access Control**: Department and plant-based restrictions

### User Roles
- **Admin**: Full CRUD operations within assigned departments
- **User**: View and download only within assigned departments

## Installation

### Prerequisites
- Python 3.8+
- PostgreSQL 12+
- pip (Python package manager)

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd multi-plant-dms
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Set up PostgreSQL database**
   ```sql
   CREATE DATABASE document_management;
   CREATE USER dms_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE document_management TO dms_user;
   ```

6. **Update database configuration**
   Edit `.env` file:
   ```
   DATABASE_URL=postgresql+pg8000://dms_user:your_password@localhost:5432/document_management
   SECRET_KEY=your-secret-key-here
   ```

7. **Initialize the application**
   ```bash
   python app.py
   ```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key | `dev-secret-key-change-in-production` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+pg8000://user:password@localhost/document_management` |
| `UPLOAD_FOLDER` | File upload directory | `uploads` |
| `MAX_FILE_SIZE` | Maximum file size in bytes | `16777216` (16MB) |
| `FLASK_ENV` | Environment (development/production) | `development` |

### Database Schema

The system includes the following main tables:
- `plants`: Plant/organization information
- `departments`: Department definitions
- `users`: User accounts with role-based access
- `user_departments`: Many-to-many relationship between users and departments
- `documents`: Document metadata and file information
- `document_types`: Document categorization
- `download_logs`: Audit trail for document access

## Usage

### Default Admin Accounts

The system creates default admin accounts for each plant:

| Plant | Username | Password |
|-------|----------|----------|
| admin | `admin` | `admin123` |

**Important**: Change these default passwords in production!

### Departments

The system includes 11 departments:
1. HR & Admin
2. Sales & Marketing
3. QMS
4. Quality
5. Purchase
6. Store
7. Dispatch
8. Production
9. NPD (New Product Development)
10. Machine Maintenance
11. Tool Maintenance

### Document Types

Four document types are supported:
- Quality Manuals
- Quality Procedures
- WI / SOP / Standards / Drawings
- General Documents

## API Endpoints

### Authentication
- `POST /login` - User login
- `GET /logout` - User logout
- `GET /api/user/profile` - Get user profile

### Document Management
- `GET /documents` - List documents (filtered by department)
- `POST /documents/upload` - Upload document (Admin only)
- `GET /documents/{id}` - View document details
- `GET /documents/{id}/download` - Download document
- `DELETE /documents/{id}` - Delete document (Admin only)

### System Information
- `GET /api/plants` - List plants
- `GET /api/departments` - List departments
- `GET /api/document-types` - List document types

## Deployment

### Development
```bash
python app.py
```

### Production with Waitress
```bash
waitress-serve --host=0.0.0.0 --port=5000 wsgi:application
```

### Production with Gunicorn
```bash
gunicorn --bind 0.0.0.0:5000 wsgi:application
```

### Docker Deployment
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["waitress-serve", "--host=0.0.0.0", "--port=5000", "wsgi:application"]
```

## Security Considerations

1. **Change default passwords** in production
2. **Use HTTPS** in production environments
3. **Configure proper database credentials**
4. **Set up file upload restrictions**
5. **Enable security headers** (Flask-Talisman)
6. **Regular security updates** for dependencies

## File Structure

```
multi-plant-dms/
├── app.py                 # Main Flask application
├── models.py             # Database models
├── routes.py             # Route handlers
├── config.py             # Configuration settings
├── wsgi.py              # WSGI entry point
├── requirements.txt      # Python dependencies
├── templates/           # HTML templates
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── documents.html
│   ├── upload.html
│   ├── document_detail.html
│   └── error.html
├── static/              # Static assets
│   ├── css/style.css
│   └── js/main.js
└── uploads/             # File upload directory
```

## Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Verify PostgreSQL is running
   - Check database credentials in `.env`
   - Ensure database exists

2. **File Upload Issues**
   - Check `UPLOAD_FOLDER` permissions
   - Verify file size limits
   - Ensure allowed file types

3. **Session Issues**
   - Clear browser cookies
   - Check `SECRET_KEY` configuration
   - Verify session storage permissions

### Logs

Application logs are written to `app.log` by default. Check this file for error details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the documentation

## Changelog

### Version 1.0.0
- Initial release
- Multi-plant support
- Department-based access control
- Document management system
- User authentication and authorization
- File upload and download
- Responsive web interface
