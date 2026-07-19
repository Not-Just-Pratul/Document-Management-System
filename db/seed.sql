-- Multi-Plant Document Management System
-- Neon PostgreSQL Seed Data

-- Insert plants
INSERT INTO plants (name) VALUES
  ('Rudrapur'),
  ('Zaheerabad'),
  ('Palwal')
ON CONFLICT (name) DO NOTHING;

-- Insert departments
INSERT INTO departments (name) VALUES
  ('HR & Admin'),
  ('Sales & Marketing'),
  ('QMS'),
  ('Quality'),
  ('Purchase'),
  ('Store'),
  ('Dispatch'),
  ('Production'),
  ('NPD (New Product Development)'),
  ('Machine Maintenance'),
  ('Tool Maintenance')
ON CONFLICT (name) DO NOTHING;

-- Insert document types
INSERT INTO document_types (name) VALUES
  ('Quality Manuals'),
  ('Quality Procedures'),
  ('Work Instructions'),
  ('SOP'),
  ('Standards'),
  ('Drawings'),
  ('General Documents')
ON CONFLICT (name) DO NOTHING;
