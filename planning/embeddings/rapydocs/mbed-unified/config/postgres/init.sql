-- PostgreSQL initialization script for MBED
-- This script sets up the initial database schema and configurations

-- Create extension for vector operations (pgvector)
CREATE EXTENSION IF NOT EXISTS vector;

-- Create extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Set optimal configurations for embedding storage
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '128MB';
ALTER SYSTEM SET work_mem = '16MB';

-- Create indexes configuration
ALTER SYSTEM SET max_parallel_workers_per_gather = 2;
ALTER SYSTEM SET max_parallel_workers = 8;

-- Optimize for SSD storage
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;

-- Log slow queries for performance monitoring
ALTER SYSTEM SET log_min_duration_statement = 100;

-- Apply configuration changes
SELECT pg_reload_conf();