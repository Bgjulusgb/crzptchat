"""
Utilities Module - Helper Functions and Classes
Provides common utilities for logging, caching, rate limiting, and error handling
"""

import hashlib
import time
from typing import Any, Callable, Dict, Optional, TypeVar, Generic
from functools import wraps
from collections import deque
from datetime import datetime, timedelta
import logging
import json

logger = logging.getLogger(__name__)

T = TypeVar('T')

# ==================== CACHING ====================

class LRUCache(Generic[T]):
    """Simple LRU (Least Recently Used) Cache"""
    
    def __init__(self, max_size: int = 128):
        self.max_size = max_size
        self.cache: Dict[str, T] = {}
        self.access_order: deque = deque()
    
    def get(self, key: str) -> Optional[T]:
        """Get value from cache"""
        if key in self.cache:
            self.access_order.remove(key)
            self.access_order.append(key)
            return self.cache[key]
        return None
    
    def put(self, key: str, value: T):
        """Put value in cache"""
        if key in self.cache:
            self.access_order.remove(key)
        elif len(self.cache) >= self.max_size:
            # Remove least recently used
            oldest = self.access_order.popleft()
            del self.cache[oldest]
        
        self.cache[key] = value
        self.access_order.append(key)
    
    def clear(self):
        """Clear cache"""
        self.cache.clear()
        self.access_order.clear()
    
    def size(self) -> int:
        """Get cache size"""
        return len(self.cache)

# ==================== RATE LIMITING ====================

class RateLimiter:
    """Token bucket rate limiter"""
    
    def __init__(self, rate: int, window_seconds: int):
        """
        Initialize rate limiter
        rate: max requests
        window_seconds: time window
        """
        self.rate = rate
        self.window = window_seconds
        self.buckets: Dict[str, deque] = {}
    
    def is_allowed(self, identifier: str) -> bool:
        """Check if request is allowed"""
        now = time.time()
        
        if identifier not in self.buckets:
            self.buckets[identifier] = deque()
        
        bucket = self.buckets[identifier]
        
        # Remove old timestamps
        while bucket and bucket[0] < now - self.window:
            bucket.popleft()
        
        # Check rate
        if len(bucket) < self.rate:
            bucket.append(now)
            return True
        
        return False
    
    def get_retry_after(self, identifier: str) -> int:
        """Get seconds to wait before next request"""
        if identifier not in self.buckets:
            return 0
        
        bucket = self.buckets[identifier]
        if not bucket:
            return 0
        
        oldest = bucket[0]
        retry_at = oldest + self.window
        return max(0, int(retry_at - time.time()))

# ==================== HASHING ====================

def hash_string(value: str, algorithm: str = 'sha256') -> str:
    """Hash a string"""
    if algorithm == 'sha256':
        return hashlib.sha256(value.encode()).hexdigest()
    elif algorithm == 'sha512':
        return hashlib.sha512(value.encode()).hexdigest()
    elif algorithm == 'md5':
        return hashlib.md5(value.encode()).hexdigest()
    else:
        raise ValueError(f"Unknown hash algorithm: {algorithm}")

def hash_file(filepath: str, algorithm: str = 'sha256') -> str:
    """Hash a file"""
    hash_obj = hashlib.sha256() if algorithm == 'sha256' else hashlib.md5()
    
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_obj.update(chunk)
    
    return hash_obj.hexdigest()

# ==================== DECORATORS ====================

def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Retry decorator with exponential backoff"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 1
            current_delay = delay
            
            while attempt <= max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts:
                        logger.error(f"Failed after {max_attempts} attempts: {e}")
                        raise
                    
                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed. "
                        f"Retrying in {current_delay}s: {e}"
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff
                    attempt += 1
        
        return wrapper
    return decorator

def timeit(func: Callable) -> Callable:
    """Time a function execution"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            elapsed = time.time() - start
            logger.debug(f"{func.__name__} took {elapsed:.3f}s")
    
    return wrapper

def log_errors(func: Callable) -> Callable:
    """Log function errors"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(
                f"Error in {func.__name__}: {e}",
                exc_info=True
            )
            raise
    
    return wrapper

# ==================== JSON UTILITIES ====================

class JSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for complex types"""
    
    def default(self, o):  # Match parent class parameter name
        if isinstance(o, datetime):
            return o.isoformat()
        elif isinstance(o, timedelta):
            return o.total_seconds()
        elif hasattr(o, '__dict__'):
            return o.__dict__
        return super().default(o)

def safe_json_dumps(obj: Any, **kwargs) -> str:
    """Safely convert object to JSON string"""
    try:
        return json.dumps(obj, cls=JSONEncoder, **kwargs)
    except Exception as e:
        logger.error(f"JSON serialization failed: {e}")
        return "{}"

def safe_json_loads(data: str) -> Optional[Dict]:
    """Safely parse JSON string"""
    try:
        return json.loads(data)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing failed: {e}")
        return None

# ==================== VALIDATION ====================

class Validator:
    """Common validation utilities"""
    
    @staticmethod
    def is_email(email: str) -> bool:
        """Validate email format"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def is_username(username: str) -> bool:
        """Validate username format"""
        import re
        pattern = r'^[a-zA-Z0-9_-]{3,50}$'
        return bool(re.match(pattern, username))
    
    @staticmethod
    def is_url(url: str) -> bool:
        """Validate URL format"""
        import re
        pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        return bool(re.match(pattern, url, re.IGNORECASE))
    
    @staticmethod
    def is_positive_int(value: Any) -> bool:
        """Check if value is positive integer"""
        try:
            return int(value) > 0
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def is_safe_filename(filename: str) -> bool:
        """Check if filename is safe"""
        import re
        # Disallow path traversal and special characters
        return bool(re.match(r'^[a-zA-Z0-9._-]+$', filename))

# ==================== STRING UTILITIES ====================

class StringUtils:
    """String manipulation utilities"""
    
    @staticmethod
    def truncate(text: str, max_length: int, suffix: str = '...') -> str:
        """Truncate string to max length"""
        if len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)] + suffix
    
    @staticmethod
    def capitalize_words(text: str) -> str:
        """Capitalize first letter of each word"""
        return ' '.join(word.capitalize() for word in text.split())
    
    @staticmethod
    def remove_duplicates(text: str) -> str:
        """Remove duplicate words"""
        words = text.split()
        seen = set()
        result = []
        for word in words:
            if word not in seen:
                seen.add(word)
                result.append(word)
        return ' '.join(result)
    
    @staticmethod
    def sanitize(text: str) -> str:
        """Sanitize string (remove harmful characters)"""
        # Remove null bytes and control characters
        return ''.join(c for c in text if ord(c) >= 32 or c == '\n')

# ==================== TIME UTILITIES ====================

class TimeUtils:
    """Time and date utilities"""
    
    @staticmethod
    def get_timestamp() -> str:
        """Get current timestamp in ISO format"""
        return datetime.utcnow().isoformat()
    
    @staticmethod
    def time_ago(timestamp: str) -> str:
        """Get human-readable time difference"""
        try:
            dt = datetime.fromisoformat(timestamp)
            delta = datetime.utcnow() - dt
            
            seconds = delta.total_seconds()
            if seconds < 60:
                return "just now"
            elif seconds < 3600:
                minutes = int(seconds // 60)
                return f"{minutes}m ago"
            elif seconds < 86400:
                hours = int(seconds // 3600)
                return f"{hours}h ago"
            else:
                days = int(seconds // 86400)
                return f"{days}d ago"
        except Exception:
            return "unknown"
    
    @staticmethod
    def is_expired(timestamp: str, days: int = 30) -> bool:
        """Check if timestamp is older than days"""
        try:
            dt = datetime.fromisoformat(timestamp)
            return datetime.utcnow() - dt > timedelta(days=days)
        except Exception:
            return False

# ==================== FILE UTILITIES ====================

class FileUtils:
    """File operation utilities"""
    
    @staticmethod
    def get_file_size(filepath: str) -> int:
        """Get file size in bytes"""
        import os
        return os.path.getsize(filepath) if os.path.exists(filepath) else 0
    
    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """Format bytes to human-readable size"""
        size_float = float(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_float < 1024.0:
                return f"{size_float:.1f}{unit}"
            size_float /= 1024.0
        return f"{size_float:.1f}PB"
    
    @staticmethod
    def is_file_safe(filepath: str, max_size_mb: int = 100) -> bool:
        """Check if file is safe to process"""
        import os
        
        if not os.path.exists(filepath):
            return False
        
        if not os.path.isfile(filepath):
            return False
        
        size = os.path.getsize(filepath)
        if size > max_size_mb * 1024 * 1024:
            return False
        
        return True

# ==================== EXAMPLE USAGE ====================

if __name__ == "__main__":
    # Test cache
    cache = LRUCache(max_size=3)
    cache.put("key1", "value1")
    cache.put("key2", "value2")
    print(f"Cache get: {cache.get('key1')}")
    
    # Test rate limiter
    limiter = RateLimiter(rate=5, window_seconds=60)
    for i in range(7):
        allowed = limiter.is_allowed("user123")
        print(f"Request {i+1}: {'allowed' if allowed else 'blocked'}")
    
    # Test validation
    print(f"Valid email: {Validator.is_email('test@example.com')}")
    print(f"Valid username: {Validator.is_username('test_user')}")
    
    # Test string utilities
    text = "hello world hello test test"
    print(f"Remove duplicates: {StringUtils.remove_duplicates(text)}")
    
    # Test time utilities
    print(f"Timestamp: {TimeUtils.get_timestamp()}")
    print(f"File size: {FileUtils.format_file_size(1024*1024*50)}")
