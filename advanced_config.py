"""
Advanced Configuration Module for Secure Chat Application
Provides centralized configuration management, validation, and environment handling
"""

import os
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
import logging

# ==================== ENUMS ====================

class Environment(Enum):
    """Application environments"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"

class LogLevel(Enum):
    """Logging levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

# ==================== CONFIGURATION CLASSES ====================

@dataclass
class DatabaseConfig:
    """Database configuration"""
    type: str = "sqlite"
    path: str = "secure_chat_data/secure_chat.db"
    timeout: int = 30
    max_connections: int = 10
    enable_wal: bool = True
    backup_interval: int = 3600  # seconds

@dataclass
class SecurityConfig:
    """Security configuration"""
    jwt_secret: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    
    # Password policy
    min_password_length: int = 8
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_digits: bool = True
    require_special_chars: bool = True
    
    # Rate limiting
    max_login_attempts: int = 5
    login_attempt_window_seconds: int = 300
    max_messages_per_minute: int = 60
    
    # Encryption
    encryption_algorithm: str = "Fernet"
    master_key_rotation_days: int = 90

@dataclass
class ServerConfig:
    """Server configuration"""
    host: str = "0.0.0.0"
    port: int = 5000
    debug: bool = False
    threaded: bool = True
    
    # CORS
    cors_origins: str = "*"
    cors_methods: str = "GET,POST,PUT,DELETE,OPTIONS"
    
    # WebSocket
    socket_timeout: int = 60
    max_concurrent_connections: int = 1000
    
    # Performance
    max_request_size_mb: int = 50
    request_timeout_seconds: int = 30

@dataclass
class FileConfig:
    """File handling configuration"""
    upload_dir: str = "secure_chat_data/uploads"
    max_file_size_mb: int = 50
    max_file_name_length: int = 255
    
    allowed_extensions: Optional[List[str]] = None  # Will be set in __post_init__
    blocked_extensions: Optional[List[str]] = None  # Will be set in __post_init__
    
    def __post_init__(self):
        if self.allowed_extensions is None:
            self.allowed_extensions = ['txt', 'pdf', 'jpg', 'jpeg', 'png', 'gif', 'csv']
        if self.blocked_extensions is None:
            self.blocked_extensions = ['exe', 'dll', 'so', 'sh', 'bat', 'cmd']

@dataclass
class FeatureConfig:
    """Feature flags"""
    enable_groups: bool = True
    enable_file_sharing: bool = True
    enable_message_reactions: bool = True
    enable_message_editing: bool = True
    enable_message_deletion: bool = True
    enable_user_blocking: bool = True
    enable_two_factor_auth: bool = False
    enable_message_search: bool = True
    enable_user_presence: bool = True
    enable_message_encryption: bool = True

@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    format: str = '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    log_dir: str = "secure_chat_data/logs"
    file_name: str = "app.log"
    max_file_size_mb: int = 10
    backup_count: int = 5
    console_enabled: bool = True
    file_enabled: bool = True

# ==================== MAIN CONFIGURATION ====================

class AppConfig:
    """Main application configuration"""
    
    _instance: Optional['AppConfig'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.environment = Environment(os.getenv('APP_ENV', 'development'))
        self.config_file = os.getenv('CONFIG_FILE', 'config.json')
        
        # Initialize sub-configs
        self.database = DatabaseConfig()
        self.security = SecurityConfig()
        self.server = ServerConfig()
        self.files = FileConfig()
        self.features = FeatureConfig()
        self.logging = LoggingConfig()
        
        # Load from environment and config file
        self._load_from_env()
        self._load_from_file()
        self._validate()
    
    def _load_from_env(self):
        """Load configuration from environment variables"""
        # Security
        if env_secret := os.getenv('JWT_SECRET'):
            self.security.jwt_secret = env_secret
        
        # Server
        if env_host := os.getenv('SERVER_HOST'):
            self.server.host = env_host
        if env_port := os.getenv('SERVER_PORT'):
            self.server.port = int(env_port)
        if env_debug := os.getenv('DEBUG'):
            self.server.debug = env_debug.lower() == 'true'
        
        # Database
        if env_db_path := os.getenv('DATABASE_PATH'):
            self.database.path = env_db_path
        
        # Files
        if env_upload_dir := os.getenv('UPLOAD_DIR'):
            self.files.upload_dir = env_upload_dir
    
    def _load_from_file(self):
        """Load configuration from JSON file"""
        if not os.path.exists(self.config_file):
            return
        
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            
            # Update configurations from file
            if 'database' in config:
                for key, value in config['database'].items():
                    setattr(self.database, key, value)
            
            if 'security' in config:
                for key, value in config['security'].items():
                    setattr(self.security, key, value)
            
            if 'server' in config:
                for key, value in config['server'].items():
                    setattr(self.server, key, value)
            
            if 'files' in config:
                for key, value in config['files'].items():
                    setattr(self.files, key, value)
            
            if 'features' in config:
                for key, value in config['features'].items():
                    setattr(self.features, key, value)
            
            if 'logging' in config:
                for key, value in config['logging'].items():
                    setattr(self.logging, key, value)
        
        except Exception as e:
            print(f"Warning: Failed to load config file: {e}")
    
    def _validate(self):
        """Validate configuration"""
        if self.environment == Environment.PRODUCTION:
            if self.security.jwt_secret == "change-this-in-production":
                raise ValueError("JWT secret must be changed for production!")
            if self.server.debug:
                raise ValueError("Debug mode cannot be enabled in production!")
        
        # Ensure directories exist
        os.makedirs(self.files.upload_dir, exist_ok=True)
        os.makedirs(self.logging.log_dir, exist_ok=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'environment': self.environment.value,
            'database': asdict(self.database),
            'security': asdict(self.security),
            'server': asdict(self.server),
            'files': asdict(self.files),
            'features': asdict(self.features),
            'logging': asdict(self.logging)
        }
    
    def save_to_file(self, filepath: str = 'config.json'):
        """Save current configuration to JSON file"""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    def __repr__(self) -> str:
        return f"AppConfig({self.environment.value})"

# ==================== SINGLETON INSTANCE ====================

# Get or create singleton instance
config = AppConfig()

# ==================== EXAMPLE CONFIG FILE ====================

EXAMPLE_CONFIG = {
    "database": {
        "type": "sqlite",
        "path": "secure_chat_data/secure_chat.db",
        "timeout": 30,
        "max_connections": 10,
        "enable_wal": True,
        "backup_interval": 3600
    },
    "security": {
        "jwt_secret": "your-super-secret-key-here-change-in-production",
        "jwt_algorithm": "HS256",
        "jwt_expiration_hours": 24,
        "min_password_length": 8,
        "require_uppercase": True,
        "require_lowercase": True,
        "require_digits": True,
        "require_special_chars": True,
        "max_login_attempts": 5,
        "login_attempt_window_seconds": 300,
        "max_messages_per_minute": 60,
        "encryption_algorithm": "Fernet",
        "master_key_rotation_days": 90
    },
    "server": {
        "host": "0.0.0.0",
        "port": 5000,
        "debug": False,
        "threaded": True,
        "cors_origins": "*",
        "cors_methods": "GET,POST,PUT,DELETE,OPTIONS",
        "socket_timeout": 60,
        "max_concurrent_connections": 1000,
        "max_request_size_mb": 50,
        "request_timeout_seconds": 30
    },
    "files": {
        "upload_dir": "secure_chat_data/uploads",
        "max_file_size_mb": 50,
        "max_file_name_length": 255,
        "allowed_extensions": ["txt", "pdf", "jpg", "jpeg", "png", "gif", "csv"],
        "blocked_extensions": ["exe", "dll", "so", "sh", "bat", "cmd"]
    },
    "features": {
        "enable_groups": True,
        "enable_file_sharing": True,
        "enable_message_reactions": True,
        "enable_message_editing": True,
        "enable_message_deletion": True,
        "enable_user_blocking": True,
        "enable_two_factor_auth": False,
        "enable_message_search": True,
        "enable_user_presence": True,
        "enable_message_encryption": True
    },
    "logging": {
        "level": "INFO",
        "log_dir": "secure_chat_data/logs",
        "file_name": "app.log",
        "max_file_size_mb": 10,
        "backup_count": 5,
        "console_enabled": True,
        "file_enabled": True
    }
}

# ==================== INITIALIZATION ====================

if __name__ == "__main__":
    # Print current configuration
    print("Current Configuration:")
    print(json.dumps(config.to_dict(), indent=2))
    
    # Create example config file if needed
    print("\n\nTo create a config file, use:")
    print("  python advanced_config.py --create-config")
    
    # Save example config
    with open('config.example.json', 'w') as f:
        json.dump(EXAMPLE_CONFIG, f, indent=2)
    print("\nExample config saved to: config.example.json")
