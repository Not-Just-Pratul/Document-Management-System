# Multi-Plant Document Management System

Flask-based document management for multi-plant organizations with department-based access control.

## Quick Start

```bash
git clone <repo-url>
cd Document-Management-System

# One-time setup
npm run setup

# Start development server
npm run dev
```

Open http://localhost:5000

**Default login:** `admin` / `admin@808`

## One-Minute Setup

1. Clone the repo
2. Run `npm run setup` (creates venv, installs deps, creates .env, initializes DB)
3. Run `npm run dev`
4. Done.

## Deploy to Railway (Free, Always-On)

### Prerequisites
- GitHub account
- Neon.tech account (free PostgreSQL)

### Steps

1. **Get free PostgreSQL from Neon**
   - Go to https://neon.tech
   - Sign up with GitHub
   - Create project: `dms-db`
   - Copy connection string: `postgresql://user:pass@ep-xyz.region.aws.neon.tech/dbname`

2. **Deploy on Railway**
   - Go to https://railway.app
   - Sign up with GitHub
   - Click **"New Project"** → **"Deploy from GitHub repo"**
   - Select repo: `Not-Just-Pratul/Document-Management-System`
   - Railway will auto-detect Python and deploy

3. **Add PostgreSQL**
   - In Railway dashboard, click **"New"** → **"Database"** → **"PostgreSQL"**
   - Copy the `DATABASE_URL` from the PostgreSQL service

4. **Set environment variables**
   In your web service, add these env vars:
   ```
   DATABASE_URL = <your PostgreSQL connection string>
   SECRET_KEY = <generate a random 32+ char string>
   FLASK_ENV = production
   FLASK_DEBUG = 0
   ```

5. **Run migrations**
   ```bash
   railway run python -c "import models; models.initialize_database()"
   ```

6. **Access your app**
   - URL: `https://document-management-system-production.up.railway.app`
   - HTTPS is automatic

### Troubleshooting Railway

**500 Internal Server Error:**
```bash
# Check logs
railway logs

# Run migrations
railway run python -c "import models; models.initialize_database()"

# Verify env vars
railway run env
```

**Database not initialized:**
```bash
railway run python -c "import models; models.initialize_database()"
```

## Commands

| Command | Description |
|---------|-------------|
| `npm run setup` | Full project setup (deps, .env, database) |
| `npm run dev` | Start development server |
| `npm run start` | Start production server (Waitress) |
| `npm run build` | Validate project structure and dependencies |
| `npm run doctor` | Check environment health |
| `npm run clean` | Remove build artifacts (.venv, .env, uploads) |
| `npm run reset` | Clean and re-setup |

## Docker

```bash
docker compose up
```

Default login: `admin` / `admin@808`

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key | Random 32-byte hex |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://dms_user:1234@localhost:5432/document_management` |
| `UPLOAD_FOLDER` | File upload directory | `uploads` |
| `MAX_FILE_SIZE` | Maximum file size in bytes | `16777216` (16MB) |
| `FLASK_ENV` | Environment (development/production) | `development` |
| `FLASK_DEBUG` | Debug mode (0/1) | `0` |

## Default Admin

| Username | Password | Role |
|----------|----------|------|
| admin | admin@808 | Admin (all plants, all departments) |

**Change this password in production.**

## Tech Stack

- **Backend**: Flask 2.2, Python 3.8+
- **Database**: PostgreSQL 15+
- **Auth**: Werkzeug password hashing (pbkdf2:sha256)
- **Security**: Flask-SeaSurf (CSRF), Flask-Talisman (headers)
- **Frontend**: Bootstrap 5, Font Awesome
- **Deployment**: Docker, Waitress (production)

## License

MIT
