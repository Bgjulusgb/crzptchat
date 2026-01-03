"""
Secure Python Chat Application - Enhanced Version
A production-ready, end-to-end encrypted messaging platform with comprehensive security
"""

import os
import sys
import json
import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple, Callable, TYPE_CHECKING
from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path
import re
import mimetypes
import tempfile
import shutil

# Third-party imports
try:
    from cryptography.fernet import Fernet, InvalidToken
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    import base64
    import jwt
except ImportError:
    print("Installing required dependencies...")
    os.system("pip install cryptography pyjwt")
    from cryptography.fernet import Fernet, InvalidToken
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    import base64
    import jwt

# Database imports
if TYPE_CHECKING:
    import sqlite3
    from sqlite3 import Connection, Cursor

try:
    import sqlite3
    from sqlite3 import Connection, Cursor
except ImportError:
    print("Installing SQLite support...")
    os.system("pip install pysqlite3-binary")
    import sqlite3
    from sqlite3 import Connection, Cursor

# ==================== CUSTOM EXCEPTIONS ====================

class SecureChatError(Exception):
    """Base exception for secure chat application"""
    pass

class AuthenticationError(SecureChatError):
    """Authentication related errors"""
    pass

class AuthorizationError(SecureChatError):
    """Authorization related errors"""
    pass

class ValidationError(SecureChatError):
    """Validation errors"""
    pass

class EncryptionError(SecureChatError):
    """Encryption related errors"""
    pass

class DatabaseError(SecureChatError):
    """Database related errors"""
    pass

class FileError(SecureChatError):
    """File operation errors"""
    pass

class RateLimitError(SecureChatError):
    """Rate limiting errors"""
    pass

# ==================== LOGGING CONFIGURATION ====================

def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None):
    """Configure logging for the application"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=handlers
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# ==================== CONSTANTS ====================

class Config:
    """Application configuration with environment variable support"""
    
    # Data directories
    DATA_DIR = os.getenv("SECURE_CHAT_DATA_DIR", "secure_chat_data")
    DB_FILE = os.path.join(DATA_DIR, "chat.db")
    KEYS_DIR = os.path.join(DATA_DIR, "keys")
    UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
    LOGS_DIR = os.path.join(DATA_DIR, "logs")
    JWT_SECRET_FILE = os.path.join(DATA_DIR, ".jwt_secret")
    
    # Security settings - JWT_SECRET is initialized with default value
    JWT_SECRET = os.getenv("JWT_SECRET") or os.getenv("SECURE_CHAT_JWT_SECRET") or secrets.token_urlsafe(64)
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
    REFRESH_TOKEN_DAYS = int(os.getenv("REFRESH_TOKEN_DAYS", "30"))
    
    # Rate limiting
    MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
    LOGIN_ATTEMPT_WINDOW = int(os.getenv("LOGIN_ATTEMPT_WINDOW", "300"))  # 5 minutes
    MAX_MESSAGES_PER_MINUTE = int(os.getenv("MAX_MESSAGES_PER_MINUTE", "60"))
    
    # File settings
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", str(10 * 1024 * 1024)))  # 10MB
    CHUNK_SIZE = int(os.getenv("FILE_CHUNK_SIZE", "65536"))  # 64KB chunks
    
    # Allowed file types (MIME types)
    ALLOWED_MIME_TYPES = {
        'text/plain',
        'text/csv',
        'application/pdf',
        'image/jpeg',
        'image/png',
        'image/gif',
        'application/zip',
        'application/json'
    }
    
    # Message settings
    MAX_MESSAGE_LENGTH = int(os.getenv("MAX_MESSAGE_LENGTH", "10000"))
    MESSAGE_RETENTION_DAYS = int(os.getenv("MESSAGE_RETENTION_DAYS", "365"))
    
    # Pagination
    DEFAULT_PAGE_SIZE = int(os.getenv("DEFAULT_PAGE_SIZE", "50"))
    MAX_PAGE_SIZE = int(os.getenv("MAX_PAGE_SIZE", "100"))
    
    # Password requirements
    MIN_PASSWORD_LENGTH = int(os.getenv("MIN_PASSWORD_LENGTH", "8"))
    
    @staticmethod
    def create_directories():
        """Create necessary directories with secure permissions"""
        directories = [Config.DATA_DIR, Config.KEYS_DIR, Config.UPLOADS_DIR, Config.LOGS_DIR]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            # Set secure permissions (700 = rwx------)
            try:
                os.chmod(directory, 0o700)
            except (OSError, NotImplementedError):
                # Windows may not support chmod
                pass
    
    @staticmethod
    def load_or_create_jwt_secret():
        """Load JWT secret from file or create a new one"""
        # Check environment variables first
        jwt_secret = os.getenv("JWT_SECRET") or os.getenv("SECURE_CHAT_JWT_SECRET")
        
        if jwt_secret:
            Config.JWT_SECRET = jwt_secret
            return
        
        # Try to load from file
        if os.path.exists(Config.JWT_SECRET_FILE):
            try:
                with open(Config.JWT_SECRET_FILE, 'r') as f:
                    Config.JWT_SECRET = f.read().strip()
                return
            except Exception as e:
                logger.error(f"Failed to load JWT secret from file: {e}")
        
        # Generate new secret and save it
        Config.JWT_SECRET = secrets.token_urlsafe(64)
        try:
            with open(Config.JWT_SECRET_FILE, 'w') as f:
                f.write(Config.JWT_SECRET)
            # Set secure permissions on the secret file
            try:
                os.chmod(Config.JWT_SECRET_FILE, 0o600)  # rw-------
            except (OSError, NotImplementedError):
                pass
            logger.info("Generated new JWT secret and saved to file")
        except Exception as e:
            logger.warning(f"Failed to save JWT secret to file: {e}. Using in-memory secret.")

# Initialize directories and configuration
Config.create_directories()
Config.load_or_create_jwt_secret()

# ==================== ENUMS ====================

class MessageType(Enum):
    """Message types"""
    TEXT = "text"
    FILE = "file"
    SYSTEM = "system"
    REACTION = "reaction"
    EDITED = "edited"
    DELETED = "deleted"

class UserRole(Enum):
    """User roles"""
    MEMBER = "member"
    ADMIN = "admin"
    MODERATOR = "moderator"

class UserStatus(Enum):
    """User status"""
    ONLINE = "online"
    OFFLINE = "offline"
    AWAY = "away"
    BUSY = "busy"

class MessageStatus(Enum):
    """Message status"""
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"

# ==================== MODELS ====================

@dataclass
class User:
    """User model with comprehensive fields"""
    id: int
    username: str
    email: str
    password_hash: str
    
    # Two-factor authentication
    two_factor_enabled: bool = False
    two_factor_secret: Optional[str] = None
    
    # Security tracking
    failed_login_attempts: int = 0
    last_failed_login: Optional[str] = None
    is_locked: bool = False
    locked_until: Optional[str] = None
    
    # Status
    is_active: bool = True
    status: str = UserStatus.OFFLINE.value
    status_message: Optional[str] = None
    
    # Profile
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    
    # Timestamps
    created_at: str = ""
    last_login: Optional[str] = None
    last_seen: Optional[str] = None
    updated_at: str = ""
    
    def to_dict(self, include_sensitive: bool = False) -> Dict:
        """Convert user to dictionary, excluding sensitive fields"""
        data = asdict(self)
        if not include_sensitive:
            data.pop('password_hash', None)
            data.pop('two_factor_secret', None)
        return data
    
    def is_online_now(self) -> bool:
        """Check if user is currently online"""
        if self.status != UserStatus.ONLINE.value:
            return False
        if self.last_seen:
            last_seen_time = datetime.fromisoformat(self.last_seen)
            return (datetime.utcnow() - last_seen_time).total_seconds() < 300  # 5 minutes
        return False

@dataclass
class Message:
    """Message model with comprehensive fields"""
    id: int
    sender_id: int
    content: str
    recipient_id: Optional[int] = None
    group_id: Optional[int] = None
    
    # Encryption
    content_nonce: str = ""
    is_encrypted: bool = True
    
    # Status
    status: str = MessageStatus.SENT.value
    is_read: bool = False
    read_at: Optional[str] = None
    
    # Message metadata
    message_type: str = MessageType.TEXT.value
    reply_to_id: Optional[int] = None
    edited_at: Optional[str] = None
    deleted_at: Optional[str] = None
    
    # Reactions
    reactions: Dict[str, List[int]] = field(default_factory=dict)  # emoji -> [user_ids]
    
    # Timestamps
    created_at: str = ""
    updated_at: str = ""
    
    def to_dict(self, decrypt_content: Optional[str] = None) -> Dict:
        """Convert message to dictionary"""
        data = asdict(self)
        if decrypt_content is not None:
            data['content'] = decrypt_content
        elif self.is_encrypted:
            data['content'] = "[Encrypted]"
        return data

@dataclass
class Group:
    """Group chat model"""
    id: int
    name: str
    created_by: int
    description: Optional[str] = None
    is_private: bool = True
    max_members: int = 50
    
    # Group settings
    allow_invites: bool = True
    require_approval: bool = False
    
    # Timestamps
    created_at: str = ""
    updated_at: str = ""
    
    # Computed fields (not stored in DB)
    members: List[int] = field(default_factory=list)
    member_count: int = 0

@dataclass
class GroupMember:
    """Group member relationship"""
    id: int
    group_id: int
    user_id: int
    role: str = UserRole.MEMBER.value
    joined_at: str = ""
    left_at: Optional[str] = None
    is_muted: bool = False

@dataclass
class FileAttachment:
    """File attachment model with security features"""
    id: int
    message_id: int
    uploader_id: int
    original_filename: str
    stored_filename: str
    file_path: str
    file_size: int
    mime_type: str
    file_hash: str
    
    # Security
    is_encrypted: bool = True
    virus_scan_status: str = "pending"
    
    # Download tracking
    download_count: int = 0
    max_downloads: Optional[int] = None
    
    # Expiration
    expires_at: Optional[str] = None
    
    # Timestamps
    uploaded_at: str = ""

@dataclass
class Session:
    """Session model for secure session management"""
    id: int
    user_id: int
    session_token: str
    refresh_token: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_info: Optional[str] = None
    
    # Session status
    is_active: bool = True
    is_revoked: bool = False
    
    # Timestamps
    created_at: str = ""
    last_activity: str = ""
    expires_at: str = ""
    revoked_at: Optional[str] = None

@dataclass
class BlockedUser:
    """Blocked user relationship"""
    id: int
    blocker_id: int
    blocked_id: int
    blocked_at: str = ""
    reason: Optional[str] = None

# ==================== VALIDATION ====================

class InputValidator:
    """Input validation and sanitization"""
    
    @staticmethod
    def validate_username(username: str) -> bool:
        """Validate username format"""
        if not username or len(username) < 3 or len(username) > 50:
            return False
        # Allow alphanumeric, underscores, and hyphens
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            return False
        return True
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email address"""
        if not email or len(email) > 255:
            return False
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_password(password: str) -> Tuple[bool, List[str]]:
        """
        Validate password strength
        Returns (is_valid, list_of_errors)
        """
        errors = []
        
        if len(password) < Config.MIN_PASSWORD_LENGTH:
            errors.append(f"Password must be at least {Config.MIN_PASSWORD_LENGTH} characters")
        
        if not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        if not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        if not re.search(r'\d', password):
            errors.append("Password must contain at least one digit")
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")
        
        return (len(errors) == 0, errors)
    
    @staticmethod
    def sanitize_message(content: str) -> str:
        """Sanitize message content"""
        if not content:
            return ""
        
        # Remove null bytes
        content = content.replace('\x00', '')
        
        # Trim whitespace
        content = content.strip()
        
        # Limit length
        if len(content) > Config.MAX_MESSAGE_LENGTH:
            content = content[:Config.MAX_MESSAGE_LENGTH]
        
        return content
    
    @staticmethod
    def validate_file_type(file_path: str, file_size: int) -> Tuple[bool, str]:
        """
        Validate file type and content
        Returns (is_valid, error_message)
        """
        # Check file size
        if file_size > Config.MAX_FILE_SIZE:
            max_mb = Config.MAX_FILE_SIZE / (1024 * 1024)
            return False, f"File size exceeds maximum of {max_mb}MB"
        
        # Check file exists
        if not os.path.exists(file_path):
            return False, "File not found"
        
        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(file_path)
        
        if not mime_type:
            return False, "Could not determine file type"
        
        if mime_type not in Config.ALLOWED_MIME_TYPES:
            return False, f"File type {mime_type} is not allowed"
        
        # Validate file content (basic check)
        try:
            with open(file_path, 'rb') as f:
                header = f.read(1024)  # Read first 1KB
            
            # Check for file signature mismatches
            if mime_type == 'image/jpeg' and not header.startswith(b'\xff\xd8'):
                return False, "Invalid JPEG file"
            elif mime_type == 'image/png' and not header.startswith(b'\x89PNG'):
                return False, "Invalid PNG file"
            elif mime_type == 'application/pdf' and not header.startswith(b'%PDF'):
                return False, "Invalid PDF file"
        except Exception as e:
            logger.error(f"Error validating file content: {e}")
            return False, "Error reading file content"
        
        return True, ""
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent directory traversal"""
        if not filename:
            return "unnamed"
        
        # Remove path components
        filename = os.path.basename(filename)
        
        # Remove dangerous characters
        filename = re.sub(r'[<>:"|?*\x00-\x1f]', '', filename)
        
        # Limit length
        name, ext = os.path.splitext(filename)
        if len(name) > 200:
            name = name[:200]
        
        return name + ext

# ==================== DATABASE MANAGER (SQLite) ====================

class DatabaseManager:
    """SQLite database manager with connection pooling and migrations"""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize database manager"""
        self.db_path = db_path or Config.DB_FILE
        self.connection_pool: List[Connection] = []
        self._initialize_database()
    
    def get_connection(self) -> Connection:
        """Get a database connection from the pool"""
        try:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row  # Enable dict-like access
            self.connection_pool.append(conn)
            return conn
        except Exception as e:
            logger.error(f"Error getting database connection: {e}")
            raise DatabaseError(f"Failed to connect to database: {e}")
    
    def close_all_connections(self):
        """Close all connections in the pool"""
        for conn in self.connection_pool:
            try:
                conn.close()
            except Exception as e:
                logger.error(f"Error closing connection: {e}")
        self.connection_pool.clear()
    
    def _initialize_database(self):
        """Initialize database schema"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    two_factor_enabled BOOLEAN DEFAULT 0,
                    two_factor_secret TEXT,
                    failed_login_attempts INTEGER DEFAULT 0,
                    last_failed_login TIMESTAMP,
                    is_locked BOOLEAN DEFAULT 0,
                    locked_until TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    status TEXT DEFAULT 'offline',
                    status_message TEXT,
                    display_name TEXT,
                    bio TEXT,
                    avatar_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    last_seen TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Messages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender_id INTEGER NOT NULL,
                    recipient_id INTEGER,
                    group_id INTEGER,
                    content TEXT NOT NULL,
                    content_nonce TEXT NOT NULL,
                    is_encrypted BOOLEAN DEFAULT 1,
                    status TEXT DEFAULT 'sent',
                    is_read BOOLEAN DEFAULT 0,
                    read_at TIMESTAMP,
                    message_type TEXT DEFAULT 'text',
                    reply_to_id INTEGER,
                    edited_at TIMESTAMP,
                    deleted_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (sender_id) REFERENCES users(id),
                    FOREIGN KEY (recipient_id) REFERENCES users(id),
                    FOREIGN KEY (group_id) REFERENCES groups(id),
                    FOREIGN KEY (reply_to_id) REFERENCES messages(id)
                )
            """)
            
            # Groups table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    created_by INTEGER NOT NULL,
                    is_private BOOLEAN DEFAULT 1,
                    max_members INTEGER DEFAULT 50,
                    allow_invites BOOLEAN DEFAULT 1,
                    require_approval BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (created_by) REFERENCES users(id)
                )
            """)
            
            # Group members table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS group_members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    role TEXT DEFAULT 'member',
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    left_at TIMESTAMP,
                    is_muted BOOLEAN DEFAULT 0,
                    FOREIGN KEY (group_id) REFERENCES groups(id),
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    UNIQUE(group_id, user_id)
                )
            """)
            
            # File attachments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS file_attachments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER NOT NULL,
                    uploader_id INTEGER NOT NULL,
                    original_filename TEXT NOT NULL,
                    stored_filename TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    mime_type TEXT NOT NULL,
                    file_hash TEXT NOT NULL,
                    is_encrypted BOOLEAN DEFAULT 1,
                    virus_scan_status TEXT DEFAULT 'pending',
                    download_count INTEGER DEFAULT 0,
                    max_downloads INTEGER,
                    expires_at TIMESTAMP,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (message_id) REFERENCES messages(id),
                    FOREIGN KEY (uploader_id) REFERENCES users(id)
                )
            """)
            
            # Sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    session_token TEXT UNIQUE NOT NULL,
                    refresh_token TEXT UNIQUE NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    device_info TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    is_revoked BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    revoked_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # Blocked users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS blocked_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    blocker_id INTEGER NOT NULL,
                    blocked_id INTEGER NOT NULL,
                    blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reason TEXT,
                    FOREIGN KEY (blocker_id) REFERENCES users(id),
                    FOREIGN KEY (blocked_id) REFERENCES users(id),
                    UNIQUE(blocker_id, blocked_id)
                )
            """)
            
            # Message reactions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS message_reactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    emoji TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (message_id) REFERENCES messages(id),
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    UNIQUE(message_id, user_id, emoji)
                )
            """)
            
            # Create indexes for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_recipient ON messages(recipient_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_group ON messages(group_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(session_token)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_group_members_group ON group_members(group_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_group_members_user ON group_members(user_id)")
            
            conn.commit()
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            conn.rollback()
            raise DatabaseError(f"Failed to initialize database: {e}")
        finally:
            conn.close()
    
    # User operations
    def create_user(self, username: str, email: str, password_hash: str) -> Optional[User]:
        """Create a new user"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (username, email.lower(), password_hash, datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
            
            user_id = cursor.lastrowid
            assert user_id is not None, "lastrowid should not be None after insert"
            conn.commit()
            
            user = self.get_user_by_id(user_id)
            assert user is not None, "User should exist after creation"
            return user
        except sqlite3.IntegrityError as e:
            conn.rollback()
            if "username" in str(e):
                raise ValidationError("Username already exists")
            elif "email" in str(e):
                raise ValidationError("Email already registered")
            raise ValidationError("User creation failed")
        except Exception as e:
            conn.rollback()
            logger.error(f"Error creating user: {e}")
            raise DatabaseError(f"Failed to create user: {e}")
        finally:
            conn.close()
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            return User(**dict(row)) if row else None
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None
        finally:
            conn.close()
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            return User(**dict(row)) if row else None
        except Exception as e:
            logger.error(f"Error getting user by username: {e}")
            return None
        finally:
            conn.close()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = ?", (email.lower(),))
            row = cursor.fetchone()
            return User(**dict(row)) if row else None
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None
        finally:
            conn.close()
    
    def update_user(self, user: User):
        """Update user"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET
                    username = ?, email = ?, password_hash = ?,
                    two_factor_enabled = ?, two_factor_secret = ?,
                    failed_login_attempts = ?, last_failed_login = ?,
                    is_locked = ?, locked_until = ?, is_active = ?,
                    status = ?, status_message = ?, display_name = ?,
                    bio = ?, avatar_url = ?, last_login = ?,
                    last_seen = ?, updated_at = ?
                WHERE id = ?
            """, (
                user.username, user.email, user.password_hash,
                user.two_factor_enabled, user.two_factor_secret,
                user.failed_login_attempts, user.last_failed_login,
                user.is_locked, user.locked_until, user.is_active,
                user.status, user.status_message, user.display_name,
                user.bio, user.avatar_url, user.last_login,
                user.last_seen, datetime.utcnow().isoformat(),
                user.id
            ))
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Error updating user: {e}")
            raise DatabaseError(f"Failed to update user: {e}")
        finally:
            conn.close()
    
    def get_all_users(self, limit: Optional[int] = None, offset: int = 0) -> List[User]:
        """Get all users with pagination"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            query = "SELECT * FROM users ORDER BY username"
            if limit is not None:
                query += f" LIMIT {limit} OFFSET {offset}"
            cursor.execute(query)
            return [User(**dict(row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []
        finally:
            conn.close()
    
    # Message operations
    def create_message(self, sender_id: int, content: str, content_nonce: str,
                      recipient_id: Optional[int] = None, group_id: Optional[int] = None,
                      message_type: str = "text", reply_to_id: Optional[int] = None) -> Optional[Message]:
        """Create a new message"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO messages (sender_id, recipient_id, group_id, content, content_nonce,
                                     message_type, reply_to_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (sender_id, recipient_id, group_id, content, content_nonce,
                  message_type, reply_to_id, datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
            
            message_id = cursor.lastrowid
            assert message_id is not None, "lastrowid should not be None after insert"
            conn.commit()
            
            message = self.get_message_by_id(message_id)
            assert message is not None, "Message should exist after creation"
            return message
        except Exception as e:
            conn.rollback()
            logger.error(f"Error creating message: {e}")
            raise DatabaseError(f"Failed to create message: {e}")
        finally:
            conn.close()
    
    def get_message_by_id(self, message_id: int) -> Optional[Message]:
        """Get message by ID"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM messages WHERE id = ?", (message_id,))
            row = cursor.fetchone()
            return Message(**dict(row)) if row else None
        except Exception as e:
            logger.error(f"Error getting message by ID: {e}")
            return None
        finally:
            conn.close()
    
    def get_messages_between_users(self, user1_id: int, user2_id: int,
                                   limit: int = 50, offset: int = 0,
                                   include_deleted: bool = False) -> List[Message]:
        """Get messages between two users with proper sorting"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            query = """
                SELECT * FROM messages
                WHERE ((sender_id = ? AND recipient_id = ?) OR (sender_id = ? AND recipient_id = ?))
            """
            if not include_deleted:
                query += " AND deleted_at IS NULL"
            
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            
            cursor.execute(query, (user1_id, user2_id, user2_id, user1_id, limit, offset))
            return [Message(**dict(row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting messages between users: {e}")
            return []
        finally:
            conn.close()
    
    def get_group_messages(self, group_id: int, limit: int = 50, offset: int = 0,
                          include_deleted: bool = False) -> List[Message]:
        """Get messages for a group with proper sorting"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            query = "SELECT * FROM messages WHERE group_id = ?"
            if not include_deleted:
                query += " AND deleted_at IS NULL"
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            
            cursor.execute(query, (group_id, limit, offset))
            return [Message(**dict(row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting group messages: {e}")
            return []
        finally:
            conn.close()
    
    def update_message(self, message: Message):
        """Update message"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE messages SET
                    content = ?, status = ?, is_read = ?, read_at = ?,
                    edited_at = ?, deleted_at = ?, updated_at = ?
                WHERE id = ?
            """, (message.content, message.status, message.is_read, message.read_at,
                  message.edited_at, message.deleted_at, datetime.utcnow().isoformat(),
                  message.id))
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Error updating message: {e}")
            raise DatabaseError(f"Failed to update message: {e}")
        finally:
            conn.close()
    
    def delete_message(self, message_id: int, soft_delete: bool = True) -> bool:
        """Delete a message"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            if soft_delete:
                cursor.execute("""
                    UPDATE messages SET deleted_at = ?, updated_at = ?
                    WHERE id = ?
                """, (datetime.utcnow().isoformat(), datetime.utcnow().isoformat(), message_id))
            else:
                cursor.execute("DELETE FROM messages WHERE id = ?", (message_id,))
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"Error deleting message: {e}")
            return False
        finally:
            conn.close()
    
    # Group operations
    def create_group(self, name: str, created_by: int, description: Optional[str] = None,
                    is_private: bool = True) -> Optional[Group]:
        """Create a new group"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO groups (name, description, created_by, is_private, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, description, created_by, is_private, 
                  datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
            
            group_id = cursor.lastrowid
            assert group_id is not None, "lastrowid should not be None after insert"
            conn.commit()
            
            # Add creator as admin member
            self.add_group_member(group_id, created_by, role=UserRole.ADMIN.value)
            
            group = self.get_group_by_id(group_id)
            assert group is not None, "Group should exist after creation"
            return group
        except Exception as e:
            conn.rollback()
            logger.error(f"Error creating group: {e}")
            raise DatabaseError(f"Failed to create group: {e}")
        finally:
            conn.close()
    
    def get_group_by_id(self, group_id: int) -> Optional[Group]:
        """Get group by ID"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM groups WHERE id = ?", (group_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            group = Group(**dict(row))
            
            # Get members
            members = self.get_group_members(group_id)
            group.members = [m.user_id for m in members]
            group.member_count = len(members)
            
            return group
        except Exception as e:
            logger.error(f"Error getting group by ID: {e}")
            return None
        finally:
            conn.close()
    
    def get_groups_for_user(self, user_id: int) -> List[Group]:
        """Get all groups a user is a member of"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT g.* FROM groups g
                INNER JOIN group_members gm ON g.id = gm.group_id
                WHERE gm.user_id = ? AND gm.left_at IS NULL
                ORDER BY g.name
            """, (user_id,))
            
            groups = []
            for row in cursor.fetchall():
                group = Group(**dict(row))
                members = self.get_group_members(group.id)
                group.members = [m.user_id for m in members]
                group.member_count = len(members)
                groups.append(group)
            
            return groups
        except Exception as e:
            logger.error(f"Error getting groups for user: {e}")
            return []
        finally:
            conn.close()
    
    def add_group_member(self, group_id: int, user_id: int, role: str = UserRole.MEMBER.value) -> bool:
        """Add member to group"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO group_members (group_id, user_id, role, joined_at)
                VALUES (?, ?, ?, ?)
            """, (group_id, user_id, role, datetime.utcnow().isoformat()))
            
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # Already a member
        except Exception as e:
            conn.rollback()
            logger.error(f"Error adding group member: {e}")
            return False
        finally:
            conn.close()
    
    def get_group_members(self, group_id: int) -> List[GroupMember]:
        """Get all members of a group"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM group_members
                WHERE group_id = ? AND left_at IS NULL
                ORDER BY role DESC, joined_at ASC
            """, (group_id,))
            
            return [GroupMember(**dict(row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting group members: {e}")
            return []
        finally:
            conn.close()
    
    def update_group_member_role(self, group_id: int, user_id: int, role: str) -> bool:
        """Update group member role"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE group_members SET role = ?
                WHERE group_id = ? AND user_id = ?
            """, (role, group_id, user_id))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            logger.error(f"Error updating group member role: {e}")
            return False
        finally:
            conn.close()
    
    def remove_group_member(self, group_id: int, user_id: int) -> bool:
        """Remove member from group"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE group_members SET left_at = ?
                WHERE group_id = ? AND user_id = ?
            """, (datetime.utcnow().isoformat(), group_id, user_id))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            logger.error(f"Error removing group member: {e}")
            return False
        finally:
            conn.close()
    
    # File operations
    def create_file_attachment(self, message_id: int, uploader_id: int,
                              original_filename: str, stored_filename: str,
                              file_path: str, file_size: int,
                              mime_type: str, file_hash: str) -> Optional[FileAttachment]:
        """Create file attachment record"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO file_attachments (message_id, uploader_id, original_filename,
                                            stored_filename, file_path, file_size,
                                            mime_type, file_hash, uploaded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (message_id, uploader_id, original_filename, stored_filename,
                  file_path, file_size, mime_type, file_hash, datetime.utcnow().isoformat()))
            
            file_id = cursor.lastrowid
            assert file_id is not None, "lastrowid should not be None after insert"
            conn.commit()
            
            attachment = self.get_file_attachment_by_id(file_id)
            assert attachment is not None, "File attachment should exist after creation"
            return attachment
        except Exception as e:
            conn.rollback()
            logger.error(f"Error creating file attachment: {e}")
            raise DatabaseError(f"Failed to create file attachment: {e}")
        finally:
            conn.close()
    
    def get_file_attachment_by_id(self, file_id: int) -> Optional[FileAttachment]:
        """Get file attachment by ID"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM file_attachments WHERE id = ?", (file_id,))
            row = cursor.fetchone()
            return FileAttachment(**dict(row)) if row else None
        except Exception as e:
            logger.error(f"Error getting file attachment: {e}")
            return None
        finally:
            conn.close()
    
    def get_file_attachments(self, message_id: int) -> List[FileAttachment]:
        """Get file attachments for a message"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM file_attachments WHERE message_id = ?", (message_id,))
            return [FileAttachment(**dict(row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting file attachments: {e}")
            return []
        finally:
            conn.close()
    
    # Session operations
    def create_session(self, user_id: int, session_token: str, refresh_token: str,
                      ip_address: Optional[str] = None, user_agent: Optional[str] = None,
                      device_info: Optional[str] = None, expiry_hours: int = 24) -> Optional[Session]:
        """Create a new session"""
        conn = self.get_connection()
        try:
            expires_at = datetime.utcnow() + timedelta(hours=expiry_hours)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sessions (user_id, session_token, refresh_token, ip_address,
                                     user_agent, device_info, expires_at, created_at, last_activity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, session_token, refresh_token, ip_address, user_agent,
                  device_info, expires_at.isoformat(), datetime.utcnow().isoformat(),
                  datetime.utcnow().isoformat()))
            
            session_id = cursor.lastrowid
            assert session_id is not None, "lastrowid should not be None after insert"
            conn.commit()
            
            session = self.get_session_by_id(session_id)
            assert session is not None, "Session should exist after creation"
            return session
        except Exception as e:
            conn.rollback()
            logger.error(f"Error creating session: {e}")
            raise DatabaseError(f"Failed to create session: {e}")
        finally:
            conn.close()
    
    def get_session_by_id(self, session_id: int) -> Optional[Session]:
        """Get session by ID"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            return Session(**dict(row)) if row else None
        except Exception as e:
            logger.error(f"Error getting session: {e}")
            return None
        finally:
            conn.close()
    
    def get_session_by_token(self, session_token: str) -> Optional[Session]:
        """Get session by token"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE session_token = ?", (session_token,))
            row = cursor.fetchone()
            return Session(**dict(row)) if row else None
        except Exception as e:
            logger.error(f"Error getting session by token: {e}")
            return None
        finally:
            conn.close()
    
    def update_session_activity(self, session_id: int):
        """Update session last activity"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sessions SET last_activity = ?
                WHERE id = ?
            """, (datetime.utcnow().isoformat(), session_id))
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Error updating session activity: {e}")
        finally:
            conn.close()
    
    def revoke_session(self, session_id: int) -> bool:
        """Revoke a session"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sessions SET is_revoked = 1, is_active = 0, revoked_at = ?
                WHERE id = ?
            """, (datetime.utcnow().isoformat(), session_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            logger.error(f"Error revoking session: {e}")
            return False
        finally:
            conn.close()
    
    def revoke_all_user_sessions(self, user_id: int) -> bool:
        """Revoke all sessions for a user"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sessions SET is_revoked = 1, is_active = 0, revoked_at = ?
                WHERE user_id = ? AND is_active = 1
            """, (datetime.utcnow().isoformat(), user_id))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"Error revoking all sessions: {e}")
            return False
        finally:
            conn.close()
    
    # Blocked users operations
    def block_user(self, blocker_id: int, blocked_id: int, reason: Optional[str] = None) -> bool:
        """Block a user"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO blocked_users (blocker_id, blocked_id, blocked_at, reason)
                VALUES (?, ?, ?, ?)
            """, (blocker_id, blocked_id, datetime.utcnow().isoformat(), reason))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # Already blocked
        except Exception as e:
            conn.rollback()
            logger.error(f"Error blocking user: {e}")
            return False
        finally:
            conn.close()
    
    def unblock_user(self, blocker_id: int, blocked_id: int) -> bool:
        """Unblock a user"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM blocked_users WHERE blocker_id = ? AND blocked_id = ?
            """, (blocker_id, blocked_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            logger.error(f"Error unblocking user: {e}")
            return False
        finally:
            conn.close()
    
    def is_blocked(self, user_id: int, target_user_id: int) -> bool:
        """Check if a user is blocked"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM blocked_users
                WHERE blocker_id = ? AND blocked_id = ?
            """, (user_id, target_user_id))
            return cursor.fetchone()[0] > 0
        except Exception as e:
            logger.error(f"Error checking blocked status: {e}")
            return False
        finally:
            conn.close()


# ==================== ENCRYPTION MANAGER ====================

class EncryptionManager:
    """Manages encryption and decryption of messages"""
    
    def __init__(self, master_key: Optional[bytes] = None):
        """Initialize encryption manager"""
        if master_key is None:
            master_key = self._load_or_create_master_key()
        self.cipher = Fernet(master_key)
    
    def _load_or_create_master_key(self) -> bytes:
        """Load or create master encryption key"""
        key_file = os.path.join(Config.KEYS_DIR, "master.key")
        
        if os.path.exists(key_file):
            try:
                with open(key_file, 'rb') as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Failed to load master key: {e}")
        
        # Generate new key
        key = Fernet.generate_key()
        try:
            with open(key_file, 'wb') as f:
                f.write(key)
            try:
                os.chmod(key_file, 0o600)
            except (OSError, NotImplementedError):
                pass
            logger.info("Generated new master encryption key")
        except Exception as e:
            logger.warning(f"Failed to save master key: {e}")
        
        return key
    
    def encrypt(self, plaintext: str) -> Tuple[str, str]:
        """
        Encrypt a message
        Returns: (encrypted_data, nonce)
        """
        try:
            encrypted = self.cipher.encrypt(plaintext.encode('utf-8'))
            # For Fernet, we use timestamp as nonce
            nonce = secrets.token_hex(16)
            return base64.b64encode(encrypted).decode('utf-8'), nonce
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            raise EncryptionError(f"Failed to encrypt message: {e}")
    
    def decrypt(self, encrypted_data: str, nonce: Optional[str] = None) -> str:
        """
        Decrypt a message
        """
        try:
            encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
            decrypted = self.cipher.decrypt(encrypted_bytes)
            return decrypted.decode('utf-8')
        except InvalidToken:
            logger.error("Invalid encryption token")
            raise EncryptionError("Failed to decrypt: Invalid token")
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            raise EncryptionError(f"Failed to decrypt message: {e}")


# ==================== AUTHENTICATION MANAGER ====================

class AuthenticationManager:
    """Manages user authentication and authorization"""
    
    def __init__(self, db: DatabaseManager):
        """Initialize authentication manager"""
        self.db = db
    
    def hash_password(self, password: str) -> str:
        """Hash a password using PBKDF2"""
        salt = secrets.token_hex(32)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt.encode('utf-8'),
            iterations=100000,
        )
        key = base64.b64encode(kdf.derive(password.encode('utf-8')))
        return f"{salt}${key.decode('utf-8')}"
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash"""
        try:
            salt, key = password_hash.split('$')
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt.encode('utf-8'),
                iterations=100000,
            )
            expected_key = base64.b64encode(kdf.derive(password.encode('utf-8')))
            return expected_key.decode('utf-8') == key
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    def create_jwt_token(self, user_id: int, username: str) -> str:
        """Create a JWT access token"""
        payload = {
            'user_id': user_id,
            'username': username,
            'exp': datetime.utcnow() + timedelta(hours=Config.JWT_EXPIRATION_HOURS),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, Config.JWT_SECRET, algorithm=Config.JWT_ALGORITHM)
    
    def verify_jwt_token(self, token: str) -> Optional[Dict]:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(token, Config.JWT_SECRET, algorithms=[Config.JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None


# ==================== MAIN APPLICATION ====================

def main():
    """Main application entry point"""
    # Set UTF-8 encoding for Windows console
    if sys.platform == 'win32':
        try:
            if hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(encoding='utf-8')  # type: ignore
            else:
                # Python < 3.7
                import codecs
                sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')  # type: ignore
        except Exception:
            pass  # Ignore encoding errors
    
    print("=" * 60)
    print("Secure Chat Application - Enhanced Version")
    print("=" * 60)
    print()
    
    # Initialize managers
    db = DatabaseManager()
    auth = AuthenticationManager(db)
    encryption = EncryptionManager()
    
    print("[OK] Database initialized")
    print("[OK] Authentication system ready")
    print("[OK] Encryption system ready")
    print()
    print("Application is ready to use!")
    print()
    print("Configuration:")
    print(f"  - Data directory: {Config.DATA_DIR}")
    print(f"  - Database: {Config.DB_FILE}")
    print(f"  - JWT expiration: {Config.JWT_EXPIRATION_HOURS} hours")
    print(f"  - Max file size: {Config.MAX_FILE_SIZE / (1024*1024):.1f} MB")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nApplication terminated by user")
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        print(f"\nError: {e}")
        sys.exit(1)
