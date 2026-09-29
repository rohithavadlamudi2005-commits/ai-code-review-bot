# 🤖 AI Code Review Bot

An automated, production-ready AI-powered GitHub Pull Request code reviewer built with **FastAPI**, **React (Vite)**, **Celery**, **Redis**, **PostgreSQL**, **Python AST**, **Esprima AST**, and **Google Gemini 3.5 Flash**.

---

## 📌 Overview

**AI Code Review Bot** combines deterministic static analysis with Google Gemini LLM reasoning to perform automated code reviews on GitHub Pull Requests. It analyzes PR diffs, identifies security vulnerabilities (SQL injection, XSS, hardcoded secrets, unsafe execution) and code quality issues, deduplicates findings, and automatically posts inline comments and formatted Markdown summaries to GitHub Pull Requests.

---

## 🏗 Production Architecture & Review Pipeline

```text
Developer / Test PR Creation
            │
          GitHub
            │
    GitHub Webhook (opened, synchronize, reopened)
            │
    POST /api/webhooks/github
            │ (HMAC SHA-256 Signature Verification)
    FastAPI Backend API
            │ (Check Idempotency: Repo + PR + Commit SHA)
    Dispatch Task to Redis Broker
            │
    Celery Async Worker
            │ (Retry Engine for Transient Errors / Rate Limits)
  ┌─────────┴─────────────────────────────────────────┐
  │ 1. GitHub API Service: Fetch PR & Patch Diffs     │
  │ 2. Unified Diff Parser: Map Changed Line Numbers  │
  │ 3. Static AST Analysis: Python & JS AST Engines   │
  │ 4. Gemini LLM Review: LLM Reasoning & Verification│
  │ 5. Finding Deduplication & Severity Prioritization│
  │ 6. Review Formatter: Summary Table & Line Mapping │
  │ 7. GitHub Service: Post Inline Comments & Review  │
  └───────────────────────────────────────────────────┘
            │
    Severity / Explanation / Suggested Fix
            │
      GitHub Review
```

---

## ✨ Features

- 🔐 **HMAC SHA-256 Webhook Security**: Constant-time signature verification for all incoming GitHub webhooks.
- ⚡ **Commit SHA Idempotency**: Prevents duplicate review execution for identical commit SHAs.
- 🔄 **Celery + Redis Task Queue**: Asynchronous processing with exponential backoff retries for transient 429 rate limits or network issues.
- 🎯 **Hybrid Static + LLM Analysis**: AST-based static rule engine (Python & JS/TS) coupled with Gemini 3.5 Flash LLM.
- 🧪 **Test Pull Request Creator**: Built-in test PR generator that creates a dedicated Git branch, commits sample code with vulnerabilities (`ai_review_test.py`), and opens an unmerged PR for testing.
- 🛡 **Zero False Positives on Safe Patterns**: Parameterized queries, `shell=False`, and sanitized DOM manipulations are recognized as safe.
- 💬 **Inline GitHub PR Comments**: Submits line-specific PR review comments on changed diff lines with summary fallback.
- 📊 **Real-time React Dashboard**: Live monitoring for manual code reviews, PR reviews, webhook status, test PR creation, and commit tracking.
- 🔒 **Zero Token Leakage**: Environment secrets (`GITHUB_TOKEN`, `GEMINI_API_KEY`, `GITHUB_WEBHOOK_SECRET`) are never logged or exposed.
- 🐳 **Docker Multi-container Stack**: Fully orchestrated PostgreSQL, Redis, FastAPI, Celery Worker, and Nginx/React services.

---

## 🔬 Test Workflow

The AI Code Review Bot includes an automated test workflow:

1. **Create Test PR**: The bot creates a separate Git branch (e.g. `test-ai-review-YYYYMMDD-HHMMSS`), commits a sample Python file `ai_review_test.py` containing security vulnerabilities (`eval(user_input)`), and opens a Pull Request on GitHub targeting `main`.
2. **Analyze Pull Request**: The PR triggers static AST analysis and Gemini LLM analysis.
3. **Post Review Findings**: The bot calculates combined findings, assigns severity levels (CRITICAL, HIGH, etc.), provides explanations and suggested fixes, and posts inline review comments and summary tables directly to the GitHub PR.

---

## 🛠 Technology Stack

- **Backend Framework**: Python 3.11, FastAPI, Uvicorn, Pydantic v2, HTTPX
- **Worker Queue**: Celery 5.6, Redis 7.0
- **Static Analysis**: `ast` (Python), `esprima` & `pyjsparser` (JavaScript/TypeScript)
- **AI / LLM**: Google Gemini 3.5 Flash REST API (`httpx` integration)
- **Frontend Framework**: React 18, Vite, Nginx Alpine, Vanilla CSS with custom glassmorphism styling
- **Database**: PostgreSQL 15 (schema auto-initialized via `database/schema.sql`)
- **Testing & CI**: Pytest, Pytest-Asyncio, GitHub Actions CI

---

## 🔑 Environment Variables

Copy `backend/.env.example` to `backend/.env`:

```env
# Server Configuration
APP_ENV=production
DEBUG=False
HOST=0.0.0.0
PORT=8000

# PostgreSQL Configuration
POSTGRES_DB=ai_code_review_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_postgres_password

# Redis & Celery Configuration
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
USE_CELERY=True

# GitHub Integration
GITHUB_TOKEN=your_github_personal_access_token_here
GITHUB_API_URL=https://api.github.com
GITHUB_WEBHOOK_SECRET=your_github_webhook_secret_here
GITHUB_REVIEW_MODE=COMMENT

# Gemini LLM Provider
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.5-flash
```

---

## 🐳 Docker Stack Deployment

### 1. Launching the Complete Stack

To build and start all containers (PostgreSQL, Redis, Backend, Worker, Frontend) in detached mode:

```bash
docker compose up -d --build
```

### 2. Monitoring Container Status & Logs

Check container health:
```bash
docker compose ps
```

View real-time application logs:
```bash
# All services
docker compose logs -f

# Celery Worker logs only
docker compose logs -f worker

# Backend API logs only
docker compose logs -f backend
```

### 3. Stopping the Stack

Stop containers gracefully:
```bash
docker compose down
```

Stop containers and remove persistent data volumes:
```bash
docker compose down -v
```

---

## 🚀 Local Development Setup (Without Docker)

### 1. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv venv
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On Linux/macOS:
source venv/bin/activate

# Install backend dependencies
pip install -r requirements.txt

# Run backend API server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- **API Base URL**: `http://127.0.0.1:8000/api`
- **Interactive Swagger Docs**: `http://127.0.0.1:8000/docs`

---

### 2. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```

- **Dashboard**: `http://localhost:5173`

---

## 🔗 GitHub Webhook & Gemini Setup

### GitHub Webhook Configuration

1. In your GitHub Repository, go to **Settings > Webhooks > Add webhook**.
2. **Payload URL**: `https://your-public-domain.com/api/webhooks/github` (use `ngrok http 8000` for local testing).
3. **Content type**: `application/json`
4. **Secret**: Same string configured in `GITHUB_WEBHOOK_SECRET`.
5. **Which events**: Select **Pull requests**.

### Gemini AI Setup

1. Obtain an API key from [Google AI Studio](https://aistudio.google.com/).
2. Add the key to `backend/.env`:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   GEMINI_MODEL=gemini-3.5-flash
   ```
3. Test connectivity using `GET /api/health/gemini` or `GET /api/health/full`.

---

## 🧪 Testing Commands & CI Pipeline

Run all 86 automated pytest unit & integration tests locally:

```bash
pytest -q
```

Run test suite with verbose output:

```bash
pytest -v
```

### Continuous Integration (GitHub Actions)

A GitHub Actions CI workflow is configured in [`.github/workflows/ci.yml`](file:///.github/workflows/ci.yml). On every push or pull request to `main`, CI automatically:
1. Installs Python dependencies and runs the Pytest suite.
2. Installs Node dependencies and validates the React production build (`npm run build`).

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Basic service health check |
| `GET` | `/api/health/gemini` | Safe Gemini API connectivity diagnostic |
| `GET` | `/api/health/full` | Full component health check (PostgreSQL, Redis, Celery, Gemini) |
| `POST` | `/api/review/code` | Direct code snippet analysis (Static + LLM) |
| `POST` | `/api/review/pr` | Interactive PR URL review endpoint |
| `POST` | `/api/review/pr/{owner}/{repo}/{pull_number}/run` | Trigger automated PR review pipeline |
| `GET` | `/api/review/runs/{owner}/{repo}/{pull_number}` | Query status of PR review run |
| `POST` | `/api/github/repos/{owner}/{repo}/test-pr` | Create automated test branch and Pull Request |
| `POST` | `/api/webhooks/github` | GitHub Webhook receiver (HMAC verified) |

---

## 🔧 Troubleshooting

* **Webhook returns 401 Unauthorized**: Ensure `GITHUB_WEBHOOK_SECRET` matches exactly between GitHub webhook settings and your `.env` file.
* **Celery task connection refused**: Ensure Redis is running (`docker compose ps redis`) and reachable at `REDIS_URL`.
* **GitHub API 422 Unprocessable Entity**: The bot automatically falls back to posting inline findings into the main Markdown review summary if a line is outside the PR diff.
* **Gemini API 429 Rate Limit**: Celery worker automatically retries transient 429 rate limit errors with exponential backoff (up to 3 retries).

---

## ⚠️ Limitations

- **Diff Scope**: Inline comments are restricted to lines added or modified within the PR diff. Unchanged lines receive findings in the summary review table.
