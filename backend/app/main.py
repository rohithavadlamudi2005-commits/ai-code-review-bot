from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, github, analyze, review, webhooks
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description="Automated AI-powered Pull Request Review System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(health.router, prefix="/api", tags=["Health Check"])
app.include_router(github.router, prefix="/api/github", tags=["GitHub Integration"])
app.include_router(analyze.router, prefix="/api/analyze", tags=["Static Code Analysis"])
app.include_router(review.router, prefix="/api/review", tags=["AI Code Review Engine"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["GitHub Webhooks"])


@app.get("/", summary="Root Endpoint")
async def root():
    """
    Root endpoint for system welcome message.
    """
    return {
        "message": "Welcome to AI Code Review Bot API",
        "docs": "/docs",
        "health": "/api/health"
    }
