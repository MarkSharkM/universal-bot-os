"""
FastAPI application entry point
"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import logging
import time

from app.core.config import settings
from app.core.database import engine, Base
from app.core.logging_config import setup_logging
from app.core.health import get_health_status

# Імпортувати всі моделі для створення таблиць
from app.models import bot, user, message, translation, business_data

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Universal Bot OS",
    description="Multi-tenant bot platform for managing 100+ bots",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    """Initialize database on startup"""
    logger.info("Starting Universal Bot OS...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    # Create tables if they don't exist
    try:
        # Імпортувати всі моделі для створення таблиць
        from app.models.bot import Bot
        from app.models.user import User
        from app.models.message import Message
        from app.models.translation import Translation
        from app.models.business_data import BusinessData
        
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created/verified")
    except Exception as e:
        logger.error(f"❌ Error creating database tables: {e}")
        # Не зупиняємо додаток, якщо таблиці вже існують
    
    # Check health on startup
    health = await get_health_status()
    if health["status"] == "healthy":
        logger.info("All systems healthy")
    else:
        logger.warning(f"Health check issues: {health}")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    logger.info("Shutting down Universal Bot OS...")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Universal Bot OS API",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """
    Health check endpoint.
    Returns status of all components.
    """
    return await get_health_status()


@app.get("/health/ready")
async def readiness():
    """
    Readiness probe for Kubernetes/Railway.
    Returns 200 if ready to accept traffic.
    """
    health_status = await get_health_status()
    
    if health_status["status"] == "healthy":
        return JSONResponse(
            content=health_status,
            status_code=status.HTTP_200_OK
        )
    else:
        return JSONResponse(
            content=health_status,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )


@app.get("/health/live")
async def liveness():
    """
    Liveness probe for Kubernetes/Railway.
    Returns 200 if application is alive.
    """
    return {"status": "alive"}


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests"""
    start_time = time.time()
    
    # Log request
    logger.info(f"{request.method} {request.url.path} - {request.client.host if request.client else 'unknown'}")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            f"{request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time:.3f}s"
        )
        
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            f"{request.method} {request.url.path} - "
            f"Error: {str(e)} - "
            f"Time: {process_time:.3f}s",
            exc_info=True
        )
        raise


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions"""
    logger.error(
        f"Unhandled exception: {exc}",
        exc_info=True,
        extra={
            "path": request.url.path,
            "method": request.method,
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.DEBUG else "An error occurred"
        }
    )


# Include routers
from app.api.v1 import webhooks, mini_apps, seo, ai

app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["webhooks"])
app.include_router(mini_apps.router, prefix="/api/v1/mini-apps", tags=["mini-apps"])
app.include_router(seo.router, prefix="/api/v1/seo", tags=["seo"])
app.include_router(ai.router, prefix="/api/v1/ai", tags=["ai"])

# Admin router
from app.api.v1 import admin
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])

# Static files (Admin UI)
from fastapi.responses import FileResponse, HTMLResponse
import os

@app.get("/admin", response_class=HTMLResponse)
async def admin_ui():
    """Serve admin UI"""
    # Шлях до admin.html відносно app/main.py
    static_path = os.path.join(os.path.dirname(__file__), "static", "admin.html")
    
    if os.path.exists(static_path):
        with open(static_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    else:
        # Fallback - повернути помилку
        return HTMLResponse(
            content=f"<h1>Admin UI not found</h1><p>Path: {static_path}</p>",
            status_code=404
        )

