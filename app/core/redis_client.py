"""Redis configuration and client for Queue Management System."""
import os
from typing import Optional
import redis
from redis import Redis, ConnectionPool
import logging

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client wrapper with connection pooling and error handling."""
    
    _instance: Optional[Redis] = None
    _pool: Optional[ConnectionPool] = None
    
    @classmethod
    def get_client(cls) -> Redis:
        """Get Redis client instance (singleton pattern with connection pooling)."""
        if cls._instance is None:
            try:
                redis_url = os.getenv(
                    "REDIS_URL",
                    "redis://localhost:6379/0"
                )
                
                cls._pool = ConnectionPool.from_url(
                    redis_url,
                    max_connections=50,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                )
                
                cls._instance = Redis(connection_pool=cls._pool)
                
                # Test connection
                cls._instance.ping()
                logger.info(f"✅ Connected to Redis at {redis_url}")
                
            except redis.ConnectionError as e:
                logger.warning(f"⚠️ Redis connection failed: {e}. Running without cache.")
                # Return a mock client that does nothing
                return MockRedisClient()
            except Exception as e:
                logger.error(f"❌ Unexpected Redis error: {e}")
                return MockRedisClient()
        
        return cls._instance
    
    @classmethod
    def close(cls):
        """Close Redis connection."""
        if cls._instance:
            cls._instance.close()
            cls._instance = None
        if cls._pool:
            cls._pool.disconnect()
            cls._pool = None
            logger.info("Redis connection closed")


class MockRedisClient:
    """Mock Redis client for when Redis is unavailable."""
    
    def __getattr__(self, name):
        """Return a no-op function for any method call."""
        def noop(*args, **kwargs):
            return None
        return noop


# Cache decorators
def cache_result(ttl: int = 300):
    """
    Decorator to cache function results in Redis.
    
    Args:
        ttl: Time to live in seconds (default 5 minutes)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and args
            cache_key = f"cache:{func.__name__}:{str(args)}:{str(kwargs)}"
            
            redis_client = RedisClient.get_client()
            
            # Try to get from cache
            try:
                cached_value = redis_client.get(cache_key)
                if cached_value:
                    logger.debug(f"Cache hit for {cache_key}")
                    import json
                    return json.loads(cached_value)
            except Exception as e:
                logger.warning(f"Cache read error: {e}")
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Store in cache
            try:
                import json
                redis_client.setex(
                    cache_key,
                    ttl,
                    json.dumps(result, default=str)
                )
                logger.debug(f"Cached result for {cache_key}")
            except Exception as e:
                logger.warning(f"Cache write error: {e}")
            
            return result
        
        return wrapper
    return decorator


def invalidate_cache(pattern: str):
    """
    Invalidate cache keys matching a pattern.
    
    Args:
        pattern: Redis key pattern (e.g., "cache:get_queue_*")
    """
    redis_client = RedisClient.get_client()
    try:
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
            logger.info(f"Invalidated {len(keys)} cache keys matching '{pattern}'")
    except Exception as e:
        logger.warning(f"Cache invalidation error: {e}")


# Rate limiting with Redis
class RedisRateLimiter:
    """Redis-based rate limiter using sliding window algorithm."""
    
    @staticmethod
    def check_rate_limit(
        key: str,
        limit: int,
        window: int = 60
    ) -> tuple[bool, int]:
        """
        Check if rate limit is exceeded.
        
        Args:
            key: Unique identifier (e.g., IP address, user ID)
            limit: Maximum number of requests
            window: Time window in seconds
            
        Returns:
            Tuple of (allowed: bool, remaining: int)
        """
        redis_client = RedisClient.get_client()
        rate_key = f"rate_limit:{key}"
        
        try:
            current_time = int(datetime.now().timestamp())
            window_start = current_time - window
            
            # Remove old entries
            redis_client.zremrangebyscore(rate_key, 0, window_start)
            
            # Count requests in current window
            request_count = redis_client.zcard(rate_key)
            
            if request_count < limit:
                # Add new request
                redis_client.zadd(rate_key, {str(current_time): current_time})
                redis_client.expire(rate_key, window)
                return True, limit - request_count - 1
            else:
                return False, 0
                
        except Exception as e:
            logger.warning(f"Rate limit check error: {e}. Allowing request.")
            # Fail open - allow request if Redis is down
            return True, limit
