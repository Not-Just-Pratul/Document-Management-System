-- Multi-Plant Document Management System
-- Neon PostgreSQL Setup (run as superuser)

-- Create database user
CREATE USER dms_user WITH PASSWORD '1234';

-- Create database
CREATE DATABASE document_management OWNER dms_user;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE document_management TO dms_user;
