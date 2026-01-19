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
# Rate limiting - ENABLED for production
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Імпортувати всі моделі для створення таблиць
from app.models import bot, user, message, translation, business_data

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Debug: Check Sentry configuration
import os
logger.info("🔍 Checking Sentry configuration...")
logger.info(f"🔍 ENV SENTRY_DSN: {os.getenv('SENTRY_DSN', 'NOT SET')[:50] if os.getenv('SENTRY_DSN') else 'NOT SET'}...")
logger.info(f"🔍 settings.SENTRY_DSN: {settings.SENTRY_DSN[:50] if settings.SENTRY_DSN else 'NOT SET'}...")
logger.info(f"🔍 settings.SENTRY_DSN type: {type(settings.SENTRY_DSN)}")

# Initialize Sentry for error tracking and performance monitoring
if settings.SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENVIRONMENT,
            traces_sample_rate=1.0,  # 100% of transactions for comprehensive monitoring
            profiles_sample_rate=0.1,  # 10% profiling
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
            ],
            # Send PII data (useful for debugging but consider privacy)
            send_default_pii=True,
            # Release tracking (optional - set via env var or git commit)
            # release=f"universal-bot-os@{os.getenv('GIT_COMMIT', 'unknown')}",
        )
        logger.info("✅ Sentry error tracking initialized successfully")
    except Exception as e:
        logger.error(f"❌ Sentry initialization failed: {e}", exc_info=True)
else:
    logger.warning("⚠️ SENTRY_DSN not configured - error tracking disabled")

app = FastAPI(
    title="Universal Bot OS",
    description="Multi-tenant bot platform for managing 100+ bots",
    version="0.1.0",
)

# Rate limiting configuration
# For Mini Apps: not needed (initData validation + CORS provide sufficient protection)
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
logger.info("✅ Rate limiting enabled")

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
    logger.info("🔍 Root endpoint / called!")
    return {
        "message": "Universal Bot OS API",
        "version": "0.1.0",
        "status": "running",
        "endpoints": {
            "/admin": "Admin UI",
            "/test-admin": "Test Admin Route",
            "/health": "Health check",
            "/api/v1/admin/bots": "Admin API - List bots"
        }
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


# Test endpoint to verify routing works
@app.get("/test-admin")
async def test_admin():
    """Test endpoint to verify HTML responses work"""
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content="<h1>Test Admin Route Works!</h1><p>If you see this, routing is working.</p>")


# Admin UI endpoint (register early to avoid conflicts)
from fastapi.responses import HTMLResponse

@app.get("/admin", response_class=HTMLResponse)
async def admin_ui():
    """Serve admin UI"""
    import pathlib
    
    logger.info("🔍 /admin endpoint called!")
    
    # Визначаємо базовий шлях
    current_file = pathlib.Path(__file__)  # app/main.py
    app_dir = current_file.parent  # app/
    project_root = app_dir.parent  # /app (в Docker) або universal-bot-os/ (локально)
    
    # Шлях до admin.html
    admin_path = app_dir / "static" / "admin.html"
    
    # Логування для дебагу
    logger.info(f"Looking for admin.html at: {admin_path}")
    logger.info(f"Current file: {current_file}")
    logger.info(f"App dir: {app_dir}")
    logger.info(f"Project root: {project_root}")
    logger.info(f"Working dir: {pathlib.Path.cwd()}")
    
    if admin_path.exists():
        try:
            html_content = admin_path.read_text(encoding='utf-8')
            logger.info(f"✅ Admin UI loaded successfully from: {admin_path}")
            return HTMLResponse(content=html_content)
        except Exception as e:
            logger.error(f"❌ Error reading admin.html: {e}", exc_info=True)
            return HTMLResponse(
                content=f"<h1>Error loading admin UI</h1><p>{str(e)}</p>",
                status_code=500
            )
    else:
        # Дебаг інформація
        debug_info = f"""
        <html>
        <head><title>Admin UI not found</title></head>
        <body style="font-family: monospace; padding: 20px;">
        <h1>Admin UI not found</h1>
        <p><strong>Expected path:</strong> {admin_path}</p>
        <p><strong>Current file:</strong> {current_file}</p>
        <p><strong>App dir:</strong> {app_dir}</p>
        <p><strong>Project root:</strong> {project_root}</p>
        <p><strong>Working dir:</strong> {pathlib.Path.cwd()}</p>
        <hr>
        <p><strong>Files in app_dir:</strong></p>
        <ul>
        {''.join(f'<li>{f.name}</li>' for f in app_dir.iterdir() if f.is_file())}
        </ul>
        <p><strong>Directories in app_dir:</strong></p>
        <ul>
        {''.join(f'<li>{d.name}/</li>' for d in app_dir.iterdir() if d.is_dir())}
        </ul>
        </body>
        </html>
        """
        logger.error(f"❌ Admin UI not found at: {admin_path}")
        return HTMLResponse(content=debug_info, status_code=404)


@app.get("/favicon.ico")
async def favicon():
    """Return empty favicon to avoid 404 errors"""
    from fastapi.responses import Response
    return Response(content="", media_type="image/x-icon")


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests"""
    start_time = time.time()
    
    # Log request with full URL
    full_url = str(request.url)
    logger.info(f"🌐 {request.method} {request.url.path} - Full URL: {full_url} - Client: {request.client.host if request.client else 'unknown'}")
    
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

# Sentry test endpoint (for verification)
from app.api.v1 import sentry_test
app.include_router(sentry_test.router, tags=["sentry"])

# Product Monitoring (separate module)
from app.api.v1 import product_monitoring
app.include_router(product_monitoring.router, prefix="/api/v1/admin", tags=["monitoring"])

# Mount static files (must be after routers to avoid conflicts)
import pathlib
static_dir = pathlib.Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    logger.info(f"✅ Static files mounted from: {static_dir}")
else:
    logger.warning(f"⚠️ Static directory not found: {static_dir}")

# Note: Rate limiting for Mini Apps is NOT needed because:
# 1. initData validation (HMAC-SHA256) provides authentication
# 2. CORS restricts access to Telegram domains only
# 3. Mini Apps is not a public API (only accessible from Telegram)
# If rate limiting is needed for other endpoints, uncomment limiter setup above

