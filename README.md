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

## Commands

| Command | Description |
|---------|-------------|
| `npm run setup` | Full project setup (deps, .env, database) |
| `npm run dev` | Start development server |
| `npm run start` | Start production server (Waitress) |
| `npm run build` | Validate project structure and dependencies |
| `npm run doctor` | Check environment health |
| `npm run clean` | Remove build artifacts (.venv, .env, uploads) |
| `npm run reset` | Clean and re-run setup |

## Docker

```bash
docker compose up
```

Default login: `admin` / `admin@808`

## Prerequisites

- **Node.js** (for npm scripts)
- **Python 3.8+**
- **PostgreSQL** (or Docker)

## Troubleshooting

### PostgreSQL not found
- Install PostgreSQL from https://www.postgresql.org/download/
- Or run with Docker: `docker compose up`

### Database connection error
- Ensure PostgreSQL is running
- Check `DATABASE_URL` in `.env`
- Run `npm run doctor` to diagnose

### Port 5000 already in use
```bash
# Windows
netstat -ano | findstr :5000
taskkill /PID <pid> /F

# macOS/Linux
lsof -ti:5000 | xargs kill -9
```

### Reset everything
```bash
npm run reset
```

## Default Admin

| Username | Password | Role |
|----------|----------|------|
| admin | admin@808 | Admin (all plants, all departments) |

**Change this password in production.**
