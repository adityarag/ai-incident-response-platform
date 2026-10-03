-- ============================================================
-- AI Incident Response Platform — Database Initialization
-- ============================================================
-- This script runs when the PostgreSQL container is first created.
-- It ensures the database is ready for Alembic migrations.
-- ============================================================

-- Enable useful extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Confirm initialization
DO $$
BEGIN
    RAISE NOTICE 'Database initialized for AI Incident Response Platform';
END $$;
