"""
Monitoring utilities for metrics and error tracking
"""
from typing import Dict, Any, Optional
from datetime import datetime
import logging
from functools import wraps

logger = logging.getLogger(__name__)


def track_error(
    error_type: str,
    bot_id: Optional[str] = None,
    user_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Track error for monitoring.
    
    Args:
        error_type: Type of error
        bot_id: Bot UUID (optional)
        user_id: User UUID (optional)
        metadata: Additional metadata
    """
    error_data = {
        "error_type": error_type,
        "timestamp": datetime.utcnow().isoformat(),
        "bot_id": bot_id,
        "user_id": user_id,
        "metadata": metadata or {},
    }
    
    logger.error(f"Error tracked: {error_data}")


def track_metric(
    metric_name: str,
    value: float,
    bot_id: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None
):
    """
    Track metric for monitoring.
    
    Args:
        metric_name: Name of metric
        value: Metric value
        bot_id: Bot UUID (optional)
        tags: Additional tags
    """
    metric_data = {
        "metric": metric_name,
        "value": value,
        "timestamp": datetime.utcnow().isoformat(),
        "bot_id": bot_id,
        "tags": tags or {},
    }
    
    logger.info(f"Metric: {metric_data}")


def monitor_performance(func):
    """
    Decorator to monitor function performance.
    
    Usage:
        @monitor_performance
        async def my_function():
            ...
    """
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        import time
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            
            # Track metric
            track_metric(
                f"{func.__name__}.duration",
                duration,
                tags={"status": "success"}
            )
            
            return result
        except Exception as e:
            duration = time.time() - start_time
            
            # Track error
            track_error(
                f"{func.__name__}.error",
                metadata={"error": str(e), "duration": duration}
            )
            
            # Track metric
            track_metric(
                f"{func.__name__}.duration",
                duration,
                tags={"status": "error"}
            )
            
            raise
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        import time
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            
            # Track metric
            track_metric(
                f"{func.__name__}.duration",
                duration,
                tags={"status": "success"}
            )
            
            return result
        except Exception as e:
            duration = time.time() - start_time
            
            # Track error
            track_error(
                f"{func.__name__}.error",
                metadata={"error": str(e), "duration": duration}
            )
            
            # Track metric
            track_metric(
                f"{func.__name__}.duration",
                duration,
                tags={"status": "error"}
            )
            
            raise
    
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper

