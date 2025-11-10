# Multi-Plant Document Management System — Project Status

## Overview
A Flask-based document management system with department- and plant-aware access control, PostgreSQL storage, CSRF protection, security headers, and admin features for upload, delete, and metadata management.

## What’s Implemented
- Authentication
  - Login (`/login`) with secure password hashing and sessions
  - Logout (`/logout`)
  - CSRF protection (Flask-SeaSurf) and security headers (Flask-Talisman)
- Users & Roles
  - Single global Admin (`admin`) supported, regular users (`user`) can browse per plant/department
  - Self-service registration with plant/department selection
- Documents
  - List documents with filters and pagination
    - Search by title (ILIKE)
    - Admin-only filters: plant and department
    - Pagination (params: `page`, `per_page`)
  - Document details view with access control and (image) preview support
  - Download with audit log entry (`download_logs`)
  - Upload (Admin only) with allowed extensions, secure filenames, MIME detection
  - Delete (Admin only) with file removal
  - Edit Metadata (Admin only) via modal in detail view
    - Update title, description, type, plant, department
  - **Document Format Request System:**
    - Users can request new formats for documents via the document detail page.
    - Admins receive notifications for new format requests.
    - Admins can view and manage format requests and mark notifications as read.
- APIs
  - `GET /api/plants` — list plants
  - `GET /api/departments` — list departments
  - `GET /api/document-types` — list document types
  - `GET /api/user/profile` — logged-in user profile
  - `GET /api/documents` — list documents with filters and pagination (JSON)
- UI/UX
  - Bootstrap 5 components, Font Awesome icons
  - Consistent custom CSS with variables, radius, animations, focus states
  - Documents page pagination controls and counts
  - Admin edit modal in document detail, auto-populated select fields
  - Bulk upload page and endpoint for multi-file uploads
  - Audit Logs page with filters and pagination
  - Admin user management: list, create, reset password
  - **Admin Notifications display on `/admin/requests` page.**

## Files of Interest
- `app.py` — app bootstrap, login route, DB init path
- `routes.py` — all app routes and APIs (auth guards, CRUD, pagination, JSON API, document format requests, admin notifications)
- `models.py` — DB connection and initialization helpers; initial seed via Python
- `config.py` — configuration (env, upload folder, allowed extensions, DB URL)
- Templates (`templates/`)
  - `base.html`, `login.html`, `dashboard.html`, `documents.html`, `document_detail.html`, `upload.html`, `error.html`, `requests.html` (updated for admin notifications)
- Static assets (`static/`)
  - `css/style.css` (structured variables/utilities)
  - `js/main.js`
- DB SQL (`db/`)
  - `setup.sql` — create role + database (run as superuser)
  - `schema.sql` — tables, FKs, indexes
  - `seed.sql` — plants (3), departments (11), document types (4), single global admin placeholder hash
  - **Manual SQL for `admin_notifications` table creation and new document types.**

## Database Schema (high-level)
- `plants(id, name)`
- `departments(id, name)`
- `users(id, username, password_hash, email, role, plant_id, department_id, is_active, created_at)`
- `document_types(id, name)`
- `documents(id, title, description, filename, file_path, file_size, mime_type, uploaded_by, plant_id, department_id, document_type_id, uploaded_at, updated_at)`
- `download_logs(id, document_id, user_id, downloaded_at)`
- `document_requests(id, user_id, document_id, requested_format, status, created_at)`
- `admin_notifications(id, user_id, document_id, requested_format, message, is_read, created_at)`

Indexes created for users.username, documents timestamps, document relations, and download logs.

## How to Initialize (PostgreSQL)
1) Run as superuser:
- `psql -U postgres -h localhost -f db/setup.sql`
2) Create tables:
- `psql -U dms_user -h localhost -d document_management -f db/schema.sql`
3) Seed data:
- `psql -U dms_user -h localhost -d document_management -f db/seed.sql`
4) **Manually execute SQL for `admin_notifications` table and new document types (provided separately).**

Replace the placeholder PBKDF2 hash in `db/seed.sql` before production:
- Python: `from werkzeug.security import generate_password_hash; print(generate_password_hash('admin123', method='pbkdf2:sha256'))`

## How to Run
- Ensure `.env` is configured to point to `document_management` DB and credentials
- `python app.py`
- Visit `http://localhost:5000`

## Current Endpoints (selected)
- HTML
  - `/` redirect → `/dashboard`
  - `/login`, `/logout`
  - `/register` — user registration
  - `/dashboard` — summary
  - `/documents` — list with pagination and filters
  - `/documents/upload` — Admin upload
  - `/documents/bulk-upload` — Admin bulk upload
  - `/documents/<id>` — detail
  - `/documents/<id>/download` — download + audit
  - `/documents/<id>/delete` — Admin delete (POST)
  - `/documents/<id>/update` — Admin update metadata (POST)
  - `/audit-logs` — Admin audit logs page
  - `/admin/users` — Admin users list
  - `/admin/users/create` — Admin create user (POST)
  - `/admin/users/<id>/reset-password` — Admin reset password (POST)
  - `/document/<id>/request_format` — User requests new format (POST)
  - `/admin/requests` — Admin view all document format requests and notifications (HTML)
  - `/admin/requests/<id>/update` — Admin updates request status (POST)
  - `/admin/notifications/<id>/mark-read` — Admin marks notification as read (POST)
- API
  - `/api/plants`, `/api/departments`, `/api/document-types`
  - `/api/user/profile`
  - `/api/documents` (JSON, paginated, filterable)

## Security Features
- CSRF protection (SeaSurf)
- Security headers (Talisman)
- Password hashing (Werkzeug)
- Session-based auth with role checks
- Strict upload extensions, MIME detection, secure filenames

## Done vs Next
- Done
  - Single global admin support and updated startup message
  - Schema + seed SQL, and Python-based init path
  - Document list pagination and JSON API
  - Admin metadata editing from detail view
  - CSS improvements and consistent components
  - **Document Format Request System with Admin Notifications**
  - **New Document Types: List, Formats, PPAP, Training Modules**
  - Sorting for documents table (title, uploaded_at, size, type)
  - **Audit log page for `download_logs` with filters by document/user/date**
  - **Enhanced previews (inline PDF/image preview)**
  - **Bulk upload (CSV + files) and progress UI**
- Next candidates (to be implemented)
  - Rate limiting and stricter file validation (magic sniffing)

## Notes
- Admin-only actions are guarded by `admin_required` decorator
- Non-admins are restricted by session `plant_id` and `department_id`
- Ensure upload folders exist per plant/department structure as configured
