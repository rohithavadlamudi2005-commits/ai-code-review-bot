-- =============================================================================
-- AI CODE REVIEW BOT - DATABASE INITIALIZATION SCHEMA
-- Database: PostgreSQL 14+
-- Stage 2: Repositories, Pull Requests, and Changed Files Schema
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Set timezone to UTC
SET timezone = 'UTC';

-- -----------------------------------------------------------------------------
-- 1. REPOSITORIES TABLE
-- Stores tracked GitHub repository metadata
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS repositories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    github_repo_id BIGINT UNIQUE NOT NULL,
    owner VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    full_name VARCHAR(512) NOT NULL UNIQUE,
    default_branch VARCHAR(255) NOT NULL DEFAULT 'main',
    is_private BOOLEAN NOT NULL DEFAULT FALSE,
    stars INT NOT NULL DEFAULT 0,
    forks INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_repositories_owner_name UNIQUE (owner, name)
);

-- Index for searching repositories by owner/name
CREATE INDEX IF NOT EXISTS idx_repositories_owner_name ON repositories(owner, name);

-- -----------------------------------------------------------------------------
-- 2. PULL_REQUESTS TABLE
-- Stores metadata for fetched Pull Requests
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pull_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    github_pr_id BIGINT UNIQUE NOT NULL,
    pull_number INT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    author VARCHAR(255) NOT NULL,
    state VARCHAR(50) NOT NULL DEFAULT 'open',
    head_branch VARCHAR(255) NOT NULL,
    head_sha VARCHAR(100) NOT NULL,
    base_branch VARCHAR(255) NOT NULL,
    base_sha VARCHAR(100) NOT NULL,
    changed_files_count INT NOT NULL DEFAULT 0,
    additions INT NOT NULL DEFAULT 0,
    deletions INT NOT NULL DEFAULT 0,
    draft BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_pull_requests_repo_number UNIQUE (repository_id, pull_number)
);

-- Index for querying PRs by repository and pull_number
CREATE INDEX IF NOT EXISTS idx_pull_requests_repo_number ON pull_requests(repository_id, pull_number);
CREATE INDEX IF NOT EXISTS idx_pull_requests_state ON pull_requests(state);

-- -----------------------------------------------------------------------------
-- 3. PULL_REQUEST_FILES TABLE
-- Stores individual file changes and patches for a Pull Request
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pull_request_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pull_request_id UUID NOT NULL REFERENCES pull_requests(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    status VARCHAR(50) NOT NULL, -- e.g., 'added', 'modified', 'removed', 'renamed'
    additions INT NOT NULL DEFAULT 0,
    deletions INT NOT NULL DEFAULT 0,
    changes INT NOT NULL DEFAULT 0,
    patch TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_pull_request_files_pr_filename UNIQUE (pull_request_id, filename)
);

-- Index for querying files by pull_request_id
CREATE INDEX IF NOT EXISTS idx_pull_request_files_pr_id ON pull_request_files(pull_request_id);

COMMENT ON TABLE repositories IS 'GitHub repositories registered for code review';
COMMENT ON TABLE pull_requests IS 'GitHub pull requests fetched for code review analysis';
COMMENT ON TABLE pull_request_files IS 'Individual changed files and unified patches in a pull request';

-- -----------------------------------------------------------------------------
-- 4. REVIEW_RUNS TABLE
-- Tracks review execution metadata and enforces idempotency per commit SHA
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS review_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID REFERENCES repositories(id) ON DELETE CASCADE,
    pull_request_id UUID REFERENCES pull_requests(id) ON DELETE CASCADE,
    repo_full_name VARCHAR(512) NOT NULL,
    pull_number INT NOT NULL,
    commit_sha VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'queued', -- 'queued', 'running', 'completed', 'failed'
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    findings_count INT NOT NULL DEFAULT 0,
    github_review_id BIGINT,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_review_runs_repo_pr_sha UNIQUE (repo_full_name, pull_number, commit_sha)
);

CREATE INDEX IF NOT EXISTS idx_review_runs_repo_pr ON review_runs(repo_full_name, pull_number);
CREATE INDEX IF NOT EXISTS idx_review_runs_sha ON review_runs(commit_sha);

COMMENT ON TABLE review_runs IS 'Tracks automated AI code review execution runs for idempotency and status monitoring';
