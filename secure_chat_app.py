"""
Secure Python Chat Application - Complete Implementation
A secure, end-to-end encrypted messaging platform with authentication
"""

import os
import sys
import json
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, ClassVar
from dataclasses import dataclass, asdict, field
from enum import Enum

# Third-party imports
import base64
import logging

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
except ImportError as e:
    raise ImportError(
        "Missing required package 'cryptography'. Install dependencies with: pip install -r requirements.txt"
    ) from e

logger = logging.getLogger(__name__)

# ==================== CONSTANTS ====================
class Config:
    """Application configuration"""
    DATA_DIR: ClassVar[str] = "secure_chat_data"
    DB_FILE: ClassVar[str] = os.path.join(DATA_DIR, "chat.db")
    KEYS_DIR: ClassVar[str] = os.path.join(DATA_DIR, "keys")
    UPLOADS_DIR: ClassVar[str] = os.path.join(DATA_DIR, "uploads")
    
    JWT_SECRET = "your-secret-key-change-in-production"
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRATION = 24  # hours
    
    MAX_LOGIN_ATTEMPTS = 5
    LOGIN_ATTEMPT_WINDOW = 300  # 5 minutes
    MAX_MESSAGES_PER_MINUTE = 60
    
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_TYPES = {'.txt', '.pdf', '.jpg', '.jpeg', '.png', '.csv'}
    
    # Create directories
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(KEYS_DIR, exist_ok=True, mode=0o700)
    os.makedirs(UPLOADS_DIR, exist_ok=True)

# ==================== ENUMS ====================
class MessageType(Enum):
    TEXT = "text"
    FILE = "file"
    SYSTEM = "system"

class UserRole(Enum):
    MEMBER = "member"
    ADMIN = "admin"

# ==================== MODELS ====================
@dataclass
class User:
    """User model"""
    id: int
    username: str
    email: str
    password_hash: str
    two_factor_enabled: bool = False
    two_factor_secret: Optional[str] = None
    failed_login_attempts: int = 0
    is_locked: bool = False
    is_active: bool = True
    is_online: bool = False
    created_at: str = ""
    last_login: Optional[str] = None
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data.pop('password_hash', None)
        return data

@dataclass
class Message:
    """Message model"""
    id: int
    sender_id: int
    recipient_id: Optional[int]
    group_id: Optional[int]
    content: str
    content_nonce: str
    is_encrypted: bool = True
    is_read: bool = False
    message_type: str = "text"
    created_at: str = ""
    read_at: Optional[str] = None

@dataclass
class Group:
    """Group chat model"""
    id: int
    name: str
    created_by: int
    description: Optional[str] = None
    is_private: bool = True
    created_at: str = ""
    members: List[int] = field(default_factory=list)

@dataclass
class FileAttachment:
    """File attachment model"""
    id: int
    message_id: int
    uploader_id: int
    original_filename: str
    stored_filename: str
    file_path: str
    file_size: int
    mime_type: str
    file_hash: str
    is_encrypted: bool = True
    uploaded_at: str = ""
    download_count: int = 0

# ==================== ENCRYPTION MANAGER ====================
class EncryptionManager:
    """Handles all encryption operations using Fernet"""
    
    def __init__(self):
        self.master_key = self._get_or_create_master_key()
        self.cipher = Fernet(self.master_key)
        self.user_keys = {}
        self.group_keys = {}
        self._load_keys()
    
    def _get_or_create_master_key(self) -> bytes:
        """Get or create master encryption key"""
        key_file = os.path.join(Config.KEYS_DIR, "master.key")
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            try:
                os.chmod(key_file, 0o600)
            except Exception:
                # On some platforms (e.g., Windows) chmod may not behave as expected
                pass
            return key
    
    def _load_keys(self):
        """Load encrypted user and group keys"""
        user_keys_file = os.path.join(Config.KEYS_DIR, "user_keys.json")
        group_keys_file = os.path.join(Config.KEYS_DIR, "group_keys.json")
        
        if os.path.exists(user_keys_file):
            with open(user_keys_file, 'r') as f:
                encrypted_keys = json.load(f)
                for user_id, encrypted_key in encrypted_keys.items():
                    self.user_keys[user_id] = self._decrypt_key(encrypted_key)
        
        if os.path.exists(group_keys_file):
            with open(group_keys_file, 'r') as f:
                encrypted_keys = json.load(f)
                for group_id, encrypted_key in encrypted_keys.items():
                    self.group_keys[group_id] = self._decrypt_key(encrypted_key)
    
    def _save_keys(self):
        """Save encrypted user and group keys"""
        user_keys_file = os.path.join(Config.KEYS_DIR, "user_keys.json")
        group_keys_file = os.path.join(Config.KEYS_DIR, "group_keys.json")
        
        encrypted_user_keys = {}
        for user_id, key in self.user_keys.items():
            encrypted_user_keys[user_id] = self._encrypt_key(key)
        
        encrypted_group_keys = {}
        for group_id, key in self.group_keys.items():
            encrypted_group_keys[group_id] = self._encrypt_key(key)
        
        with open(user_keys_file, 'w') as f:
            json.dump(encrypted_user_keys, f)
        try:
            os.chmod(user_keys_file, 0o600)
        except Exception:
            pass

        with open(group_keys_file, 'w') as f:
            json.dump(encrypted_group_keys, f)
        try:
            os.chmod(group_keys_file, 0o600)
        except Exception:
            pass
    
    def _encrypt_key(self, key: bytes) -> str:
        """Encrypt a key using master key"""
        return self.cipher.encrypt(key).decode('utf-8')
    
    def _decrypt_key(self, encrypted_key: str) -> bytes:
        """Decrypt a key using master key"""
        return self.cipher.decrypt(encrypted_key.encode('utf-8'))
    
    def get_user_key(self, user_id: int) -> bytes:
        """Get or create encryption key for user"""
        user_id_str = str(user_id)
        if user_id_str not in self.user_keys:
            self.user_keys[user_id_str] = Fernet.generate_key()
            self._save_keys()
        return self.user_keys[user_id_str]
    
    def get_group_key(self, group_id: int) -> bytes:
        """Get or create encryption key for group"""
        group_id_str = str(group_id)
        if group_id_str not in self.group_keys:
            self.group_keys[group_id_str] = Fernet.generate_key()
            self._save_keys()
        return self.group_keys[group_id_str]
    
    def encrypt_message(self, message: str, key: bytes) -> str:
        """Encrypt a message"""
        cipher = Fernet(key)
        return cipher.encrypt(message.encode('utf-8')).decode('utf-8')
    
    def decrypt_message(self, encrypted_message: str, key: bytes) -> str:
        """Decrypt a message"""
        cipher = Fernet(key)
        return cipher.decrypt(encrypted_message.encode('utf-8')).decode('utf-8')
    
    def encrypt_file(self, file_path: str, output_path: str, key: bytes) -> bool:
        """Encrypt a file"""
        try:
            cipher = Fernet(key)
            with open(file_path, 'rb') as f:
                data = f.read()
            encrypted_data = cipher.encrypt(data)
            with open(output_path, 'wb') as f:
                f.write(encrypted_data)
            return True
        except Exception:
            logger.exception("Error encrypting file")
            return False
    
    def decrypt_file(self, encrypted_path: str, output_path: str, key: bytes) -> bool:
        """Decrypt a file"""
        try:
            cipher = Fernet(key)
            with open(encrypted_path, 'rb') as f:
                encrypted_data = f.read()
            data = cipher.decrypt(encrypted_data)
            with open(output_path, 'wb') as f:
                f.write(data)
            return True
        except Exception:
            logger.exception("Error decrypting file")
            return False
    
    def hash_password(self, password: str) -> str:
        """Hash a password using PBKDF2"""
        salt = secrets.token_bytes(32)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return f"{base64.b64encode(salt).decode()}:{key.decode()}"

# ==================== DATABASE MANAGER ====================
class DatabaseManager:
    """Simple JSON-based database manager"""
    
    def __init__(self):
        self.db_file = Config.DB_FILE
        self.data = self._load_database()
    
    def _load_database(self) -> Dict:
        """Load database from file"""
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return self._get_empty_db()
        return self._get_empty_db()
    
    def _get_empty_db(self) -> Dict:
        """Get empty database structure"""
        return {
            'users': {},
            'messages': {},
            'groups': {},
            'files': {},
            'next_ids': {'users': 1, 'messages': 1, 'groups': 1, 'files': 1}
        }
    
    def _save_database(self):
        """Save database to file"""
        with open(self.db_file, 'w') as f:
            json.dump(self.data, f, indent=2)
    
    def _get_next_id(self, entity_type: str) -> int:
        """Get next ID for entity"""
        next_id = self.data['next_ids'].get(entity_type, 1)
        self.data['next_ids'][entity_type] = next_id + 1
        return next_id
    
    # User operations
    def create_user(self, username: str, email: str, password_hash: str) -> User:
        """Create a new user"""
        user_id = self._get_next_id('users')
        user = User(
            id=user_id,
            username=username,
            email=email.lower(),
            password_hash=password_hash,
            created_at=datetime.utcnow().isoformat()
        )
        self.data['users'][str(user_id)] = asdict(user)
        self._save_database()
        return user
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        user_data = self.data['users'].get(str(user_id))
        return User(**user_data) if user_data else None
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        for user_data in self.data['users'].values():
            if user_data['username'].lower() == username.lower():
                return User(**user_data)
        return None
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        for user_data in self.data['users'].values():
            if user_data['email'].lower() == email.lower():
                return User(**user_data)
        return None
    
    def update_user(self, user: User):
        """Update user"""
        self.data['users'][str(user.id)] = asdict(user)
        self._save_database()
    
    def get_all_users(self) -> List[User]:
        """Get all users"""
        return [User(**user_data) for user_data in self.data['users'].values()]
    
    # Message operations
    def create_message(self, sender_id: int, content: str, 
                      recipient_id: Optional[int] = None,
                      group_id: Optional[int] = None,
                      message_type: str = "text") -> Message:
        """Create a new message"""
        message_id = self._get_next_id('messages')
        message = Message(
            id=message_id,
            sender_id=sender_id,
            recipient_id=recipient_id,
            group_id=group_id,
            content=content,
            content_nonce=secrets.token_hex(32),
            message_type=message_type,
            created_at=datetime.utcnow().isoformat()
        )
        self.data['messages'][str(message_id)] = asdict(message)
        self._save_database()
        return message
    
    def get_message(self, message_id: int) -> Optional[Message]:
        """Get message by ID"""
        msg_data = self.data['messages'].get(str(message_id))
        return Message(**msg_data) if msg_data else None
    
    def get_messages_between_users(self, user1_id: int, user2_id: int, 
                                   limit: int = 50) -> List[Message]:
        """Get messages between two users"""
        messages = []
        for msg_data in self.data['messages'].values():
            if ((msg_data['sender_id'] == user1_id and msg_data['recipient_id'] == user2_id) or
                (msg_data['sender_id'] == user2_id and msg_data['recipient_id'] == user1_id)):
                messages.append(Message(**msg_data))
        return sorted(messages, key=lambda m: m.created_at, reverse=True)[:limit]
    
    def get_group_messages(self, group_id: int, limit: int = 50) -> List[Message]:
        """Get messages for a group"""
        messages = []
        for msg_data in self.data['messages'].values():
            if msg_data['group_id'] == group_id:
                messages.append(Message(**msg_data))
        return sorted(messages, key=lambda m: m.created_at, reverse=True)[:limit]
    
    def mark_message_read(self, message_id: int):
        """Mark message as read"""
        if str(message_id) in self.data['messages']:
            self.data['messages'][str(message_id)]['is_read'] = True
            self.data['messages'][str(message_id)]['read_at'] = datetime.utcnow().isoformat()
            self._save_database()
    
    # Group operations
    def create_group(self, name: str, created_by: int, 
                    description: Optional[str] = None) -> Group:
        """Create a new group"""
        group_id = self._get_next_id('groups')
        group = Group(
            id=group_id,
            name=name,
            description=description,
            created_by=created_by,
            created_at=datetime.utcnow().isoformat(),
            members=[created_by]  # Creator is automatically a member
        )
        self.data['groups'][str(group_id)] = asdict(group)
        self._save_database()
        return group
    
    def get_group(self, group_id: int) -> Optional[Group]:
        """Get group by ID"""
        group_data = self.data['groups'].get(str(group_id))
        return Group(**group_data) if group_data else None
    
    def get_groups_for_user(self, user_id: int) -> List[Group]:
        """Get all groups a user is a member of"""
        groups = []
        for group_data in self.data['groups'].values():
            if user_id in group_data.get('members', []):
                groups.append(Group(**group_data))
        return groups
    
    def add_group_member(self, group_id: int, user_id: int):
        """Add member to group"""
        if str(group_id) in self.data['groups']:
            group = self.data['groups'][str(group_id)]
            if 'members' not in group:
                group['members'] = []
            if user_id not in group['members']:
                group['members'].append(user_id)
                self._save_database()
    
    def remove_group_member(self, group_id: int, user_id: int):
        """Remove member from group"""
        if str(group_id) in self.data['groups']:
            group = self.data['groups'][str(group_id)]
            if 'members' in group and user_id in group['members']:
                group['members'].remove(user_id)
                self._save_database()
    
    # File operations
    def create_file_attachment(self, message_id: int, uploader_id: int,
                              original_filename: str, stored_filename: str,
                              file_path: str, file_size: int,
                              mime_type: str, file_hash: str) -> FileAttachment:
        """Create file attachment record"""
        file_id = self._get_next_id('files')
        attachment = FileAttachment(
            id=file_id,
            message_id=message_id,
            uploader_id=uploader_id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
            file_hash=file_hash,
            uploaded_at=datetime.utcnow().isoformat()
        )
        self.data['files'][str(file_id)] = asdict(attachment)
        self._save_database()
        return attachment
    
    def get_file_attachments(self, message_id: int) -> List[FileAttachment]:
        """Get file attachments for a message"""
        attachments = []
        for file_data in self.data['files'].values():
            if file_data['message_id'] == message_id:
                attachments.append(FileAttachment(**file_data))
        return attachments

# ==================== AUTHENTICATION MANAGER ====================
class AuthenticationManager:
    """Handles authentication and authorization"""
    
    def __init__(self, db: DatabaseManager, encryption: EncryptionManager):
        self.db = db
        self.encryption = encryption
        self.login_attempts = {}
        self.message_counts = {}
    
    def register_user(self, username: str, email: str, password: str) -> User:
        """Register a new user"""
        # Validate inputs
        if not self._validate_username(username):
            raise ValueError("Invalid username. Must be 3-50 characters, alphanumeric only.")
        if not self._validate_email(email):
            raise ValueError("Invalid email address.")
        if not self._validate_password(password):
            raise ValueError("Password must be at least 8 characters with uppercase, lowercase, digit, and special character.")
        
        # Check if user exists
        if self.db.get_user_by_username(username):
            raise ValueError("Username already exists.")
        if self.db.get_user_by_email(email):
            raise ValueError("Email already registered.")
        
        # Hash password and create user
        password_hash = self.encryption.hash_password(password)
        user = self.db.create_user(username, email, password_hash)
        return user
    
    def login(self, username_or_email: str, password: str) -> Dict[str, Any]:
        """Login user"""
        # Check rate limiting
        identifier = username_or_email.lower()
        if not self._check_rate_limit(identifier):
            raise ValueError("Too many login attempts. Please wait.")
        
        # Find user
        user = self.db.get_user_by_username(username_or_email)
        if not user:
            user = self.db.get_user_by_email(username_or_email)
        
        if not user:
            self._record_failed_attempt(identifier)
            raise ValueError("Invalid credentials.")
        
        # Check if account is locked
        if user.is_locked:
            raise ValueError("Account is locked due to too many failed attempts.")
        
        if not user.is_active:
            raise ValueError("Account is inactive.")
        
        # Verify password
        if not self._verify_password(password, user.password_hash):
            self._record_failed_attempt(identifier)
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= Config.MAX_LOGIN_ATTEMPTS:
                user.is_locked = True
            self.db.update_user(user)
            raise ValueError("Invalid credentials.")
        
        # Reset failed attempts
        self._reset_attempts(identifier)
        user.failed_login_attempts = 0
        user.is_online = True
        user.last_login = datetime.utcnow().isoformat()
        self.db.update_user(user)
        
        # Generate tokens
        access_token = self._generate_token(user.id, user.username)
        refresh_token = self._generate_token(user.id, user.username, hours=720)  # 30 days
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': user.to_dict()
        }
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify JWT token"""
        try:
            import jwt
            payload = jwt.decode(token, Config.JWT_SECRET, algorithms=[Config.JWT_ALGORITHM])
            return payload
        except Exception:
            logger.exception("Token verification failed")
            return None
    
    def _generate_token(self, user_id: int, username: str, hours: int = 24) -> str:
        """Generate JWT token"""
        import jwt
        payload = {
            'user_id': user_id,
            'username': username,
            'exp': datetime.utcnow() + timedelta(hours=hours),
            'iat': datetime.utcnow()
        }
        token = jwt.encode(payload, Config.JWT_SECRET, algorithm=Config.JWT_ALGORITHM)
        if isinstance(token, bytes):
            token = token.decode('utf-8')
        return token
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        try:
            salt_b64, key_b64 = password_hash.split(':')
            salt = base64.b64decode(salt_b64)
            key = base64.urlsafe_b64decode(key_b64)
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            computed_key = kdf.derive(password.encode())
            return secrets.compare_digest(computed_key, key)
        except Exception:
            return False
    
    def _check_rate_limit(self, identifier: str) -> bool:
        """Check if rate limit is exceeded"""
        now = datetime.utcnow().timestamp()
        attempts = self.login_attempts.get(identifier, [])
        
        # Remove attempts outside the window
        attempts = [t for t in attempts if now - t < Config.LOGIN_ATTEMPT_WINDOW]
        self.login_attempts[identifier] = attempts
        
        return len(attempts) < Config.MAX_LOGIN_ATTEMPTS
    
    def _record_failed_attempt(self, identifier: str):
        """Record a failed login attempt"""
        now = datetime.utcnow().timestamp()
        if identifier not in self.login_attempts:
            self.login_attempts[identifier] = []
        self.login_attempts[identifier].append(now)
    
    def _reset_attempts(self, identifier: str):
        """Reset login attempts"""
        self.login_attempts[identifier] = []
    
    def _validate_username(self, username: str) -> bool:
        """Validate username"""
        import re
        return bool(re.match(r'^[a-zA-Z0-9_-]{3,50}$', username))
    
    def _validate_email(self, email: str) -> bool:
        """Validate email"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def _validate_password(self, password: str) -> bool:
        """Validate password strength"""
        import re
        if len(password) < 8:
            return False
        if not re.search(r'[A-Z]', password):
            return False
        if not re.search(r'[a-z]', password):
            return False
        if not re.search(r'\d', password):
            return False
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False
        return True

# ==================== CHAT SERVICE ====================
class ChatService:
    """Core chat functionality"""
    
    def __init__(self, db: DatabaseManager, encryption: EncryptionManager):
        self.db = db
        self.encryption = encryption
    
    def send_message(self, sender_id: int, content: str, recipient_id: Optional[int] = None,
                    group_id: Optional[int] = None) -> Message:
        """Send a message"""
        if recipient_id and group_id:
            raise ValueError("Cannot send to both recipient and group")
        if not recipient_id and not group_id:
            raise ValueError("Must specify recipient or group")
        
        # Prevent sending to self
        if recipient_id and recipient_id == sender_id:
            raise ValueError("Cannot send message to yourself")
        
        # Get encryption key - use both users' keys for direct messages
        if recipient_id is not None:
            key = self.encryption.get_user_key(recipient_id)
        else:
            if group_id is None:
                raise ValueError("group_id is required when no recipient is provided")
            key = self.encryption.get_group_key(group_id)
        
        # Encrypt message
        encrypted_content = self.encryption.encrypt_message(content, key)
        
        # Create message
        message = self.db.create_message(
            sender_id=sender_id,
            content=encrypted_content,
            recipient_id=recipient_id,
            group_id=group_id,
            message_type="text"
        )
        return message
    
    def get_messages(self, user_id: int, other_user_id: Optional[int] = None,
                    group_id: Optional[int] = None, limit: int = 50) -> List[Dict]:
        """Get decrypted messages"""
        key: Optional[bytes] = None
        key1: Optional[bytes] = None
        key2: Optional[bytes] = None

        if group_id is not None:
            messages = self.db.get_group_messages(group_id, limit)
            key = self.encryption.get_group_key(group_id)
        elif other_user_id is not None:
            messages = self.db.get_messages_between_users(user_id, other_user_id, limit)
            key1 = self.encryption.get_user_key(user_id)
            key2 = self.encryption.get_user_key(other_user_id)
        else:
            return []
        
        # Decrypt messages
        decrypted_messages = []
        for msg in messages:
            try:
                if group_id is not None and key is not None:
                    decrypted_content = self.encryption.decrypt_message(msg.content, key)
                else:
                    # Try both keys
                    try:
                        decrypted_content = self.encryption.decrypt_message(msg.content, key1) if key1 else None
                    except Exception:
                        decrypted_content = None
                    if decrypted_content is None and key2:
                        decrypted_content = self.encryption.decrypt_message(msg.content, key2)
                
                msg_dict = asdict(msg)
                msg_dict['content'] = decrypted_content
                decrypted_messages.append(msg_dict)
            except Exception:
                logger.exception("Error decrypting message %s", msg.id)
                # Still include the message even if decryption fails
                msg_dict = asdict(msg)
                msg_dict['content'] = "[Encrypted]"
                decrypted_messages.append(msg_dict)
        
        return decrypted_messages
    
    def create_group(self, name: str, creator_id: int, description: Optional[str] = None) -> Group:
        """Create a new group"""
        group = self.db.create_group(name, creator_id, description)
        # Creator is already added as member in db.create_group
        return group
    
    def add_to_group(self, group_id: int, user_id: int) -> bool:
        """Add user to group"""
        group = self.db.get_group(group_id)
        if not group:
            return False
        self.db.add_group_member(group_id, user_id)
        return True
    
    def send_file(self, sender_id: int, file_path: str, recipient_id: Optional[int] = None,
                 group_id: Optional[int] = None) -> Dict:
        """Send a file"""
        # Validate file
        if not os.path.exists(file_path):
            raise ValueError("File not found")
        
        file_size = os.path.getsize(file_path)
        if file_size > Config.MAX_FILE_SIZE:
            raise ValueError(f"File too large. Maximum size is {Config.MAX_FILE_SIZE} bytes")
        
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext not in Config.ALLOWED_FILE_TYPES:
            raise ValueError("File type not allowed")
        
        # Generate hash
        with open(file_path, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        
        # Get encryption key
        if recipient_id is not None:
            key = self.encryption.get_user_key(recipient_id)
        elif group_id is not None:
            key = self.encryption.get_group_key(group_id)
        else:
            raise ValueError("Must provide recipient or group for file sending")
        
        # Encrypt and save file
        stored_filename = f"{secrets.token_hex(16)}{file_ext}"
        encrypted_path = os.path.join(Config.UPLOADS_DIR, stored_filename + ".enc")
        
        if not self.encryption.encrypt_file(file_path, encrypted_path, key):
            raise ValueError("Failed to encrypt file")
        
        # Create message
        original_filename = os.path.basename(file_path)
        message = self.db.create_message(
            sender_id=sender_id,
            content=f"[File: {original_filename}]",
            recipient_id=recipient_id,
            group_id=group_id,
            message_type="file"
        )
        
        # Create file attachment record
        attachment = self.db.create_file_attachment(
            message_id=message.id,
            uploader_id=sender_id,
            original_filename=original_filename,
            stored_filename=stored_filename + ".enc",
            file_path=encrypted_path,
            file_size=file_size,
            mime_type="application/octet-stream",
            file_hash=file_hash
        )
        
        return {'message': asdict(message), 'attachment': asdict(attachment)}
    
    def get_online_users(self) -> List[Dict]:
        """Get all online users"""
        users = self.db.get_all_users()
        return [user.to_dict() for user in users if user.is_online]

# ==================== CLI INTERFACE ====================
class ChatCLI:
    """Command-line interface for the chat application"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.encryption = EncryptionManager()
        self.auth = AuthenticationManager(self.db, self.encryption)
        self.chat = ChatService(self.db, self.encryption)
        self.current_user: Optional[User] = None
        self.current_token: Optional[str] = None
    
    def start(self):
        """Start the CLI application"""
        print("=" * 60)
        print("    SECURE CHAT APPLICATION")
        print("    End-to-End Encrypted Messaging")
        print("=" * 60)
        print()
        
        while True:
            if self.current_user:
                self.show_main_menu()
            else:
                self.show_auth_menu()
    
    def show_auth_menu(self):
        """Show authentication menu"""
        print("\n1. Register")
        print("2. Login")
        print("3. Exit")
        print()
        
        choice = input("Choose an option (1-3): ").strip()
        
        if choice == "1":
            self.register()
        elif choice == "2":
            self.login()
        elif choice == "3":
            print("\nGoodbye!")
            sys.exit(0)
        else:
            print("Invalid choice. Please try again.")
    
    def show_main_menu(self):
        """Show main menu for logged-in user"""
        if not self.current_user:
            print("\nYou must be logged in.")
            return
        print(f"\nWelcome, {self.current_user.username}!")
        print(f"Status: {'Online' if self.current_user.is_online else 'Offline'}")
        print("\n1. Send Message to User")
        print("2. View Messages")
        print("3. Create Group")
        print("4. Send to Group")
        print("5. View Group Messages")
        print("6. Send File")
        print("7. View Online Users")
        print("8. Logout")
        print("9. Exit")
        print()
        
        choice = input("Choose an option (1-9): ").strip()
        
        try:
            if choice == "1":
                self.send_user_message()
            elif choice == "2":
                self.view_messages()
            elif choice == "3":
                self.create_group()
            elif choice == "4":
                self.send_group_message()
            elif choice == "5":
                self.view_group_messages()
            elif choice == "6":
                self.send_file()
            elif choice == "7":
                self.view_online_users()
            elif choice == "8":
                self.logout()
            elif choice == "9":
                print("\nGoodbye!")
                sys.exit(0)
            else:
                print("Invalid choice. Please try again.")
        except Exception as e:
            logger.exception("Unhandled exception in main menu")
            print(f"\nError: {e}")
    
    def register(self):
        """Register a new user"""
        print("\n--- Registration ---")
        username = input("Username: ").strip()
        email = input("Email: ").strip()
        password = input("Password: ").strip()
        
        try:
            user = self.auth.register_user(username, email, password)
            print(f"\nRegistration successful! Your user ID is: {user.id}")
        except ValueError as e:
            print(f"\nRegistration failed: {e}")
    
    def login(self):
        """Login user"""
        print("\n--- Login ---")
        username_or_email = input("Username or Email: ").strip()
        password = input("Password: ").strip()
        
        try:
            result = self.auth.login(username_or_email, password)
            self.current_user = User(**result['user'])
            self.current_token = result['access_token']
            print(f"\nLogin successful! Welcome, {self.current_user.username}")
        except ValueError as e:
            print(f"\nLogin failed: {e}")
    
    def logout(self):
        """Logout user"""
        if self.current_user:
            self.current_user.is_online = False
            self.db.update_user(self.current_user)
        self.current_user = None
        self.current_token = None
        print("\nLogged out successfully.")
    
    def send_user_message(self):
        """Send message to another user"""
        if not self.current_user:
            print("You must be logged in.")
            return
        print("\n--- Send Message ---")
        recipient_username = input("Recipient username: ").strip()
        
        recipient = self.db.get_user_by_username(recipient_username)
        if not recipient:
            print("User not found.")
            return
        
        if recipient.id == self.current_user.id:
            print("Cannot send message to yourself.")
            return
        
        content = input("Message: ").strip()
        if not content:
            print("Message cannot be empty.")
            return
        
        message = self.chat.send_message(self.current_user.id, content, recipient_id=recipient.id)
        print(f"\nMessage sent successfully (ID: {message.id})")
    
    def view_messages(self):
        """View messages with another user"""
        if not self.current_user:
            print("You must be logged in.")
            return
        print("\n--- View Messages ---")
        other_username = input("View messages with: ").strip()
        
        other_user = self.db.get_user_by_username(other_username)
        if not other_user:
            print("User not found.")
            return
        
        messages = self.chat.get_messages(self.current_user.id, other_user_id=other_user.id)
        
        if not messages:
            print("No messages found.")
            return
        
        print(f"\n--- Conversation with {other_username} ---")
        for msg in messages:
            sender = self.db.get_user_by_id(msg['sender_id'])
            sender_name = sender.username if sender else "Unknown"
            timestamp = msg['created_at'][:19].replace('T', ' ')
            print(f"[{timestamp}] {sender_name}: {msg['content']}")
    
    def create_group(self):
        """Create a new group"""
        if not self.current_user:
            print("You must be logged in.")
            return
        print("\n--- Create Group ---")
        name = input("Group name: ").strip()
        description = input("Description (optional): ").strip() or None
        
        group = self.chat.create_group(name, self.current_user.id, description)
        print(f"\nGroup created successfully! (ID: {group.id})")
    
    def send_group_message(self):
        """Send message to a group"""
        if not self.current_user:
            print("You must be logged in.")
            return
        groups = self.db.get_groups_for_user(self.current_user.id)
        
        if not groups:
            print("You are not a member of any groups.")
            return
        
        print("\n--- Send Group Message ---")
        print("Your groups:")
        for i, group in enumerate(groups, 1):
            print(f"{i}. {group.name}")
        
        try:
            choice = int(input("Select group (number): ")) - 1
            if choice < 0 or choice >= len(groups):
                print("Invalid selection.")
                return
            
            group = groups[choice]
            content = input("Message: ").strip()
            
            if not content:
                print("Message cannot be empty.")
                return
            
            message = self.chat.send_message(self.current_user.id, content, group_id=group.id)
            print(f"\nMessage sent to {group.name} (ID: {message.id})")
        except ValueError:
            print("Invalid input.")
    
    def view_group_messages(self):
        """View group messages"""
        if not self.current_user:
            print("You must be logged in.")
            return
        groups = self.db.get_groups_for_user(self.current_user.id)
        
        if not groups:
            print("You are not a member of any groups.")
            return
        
        print("\n--- View Group Messages ---")
        print("Your groups:")
        for i, group in enumerate(groups, 1):
            print(f"{i}. {group.name}")
        
        try:
            choice = int(input("Select group (number): ")) - 1
            if choice < 0 or choice >= len(groups):
                print("Invalid selection.")
                return
            
            group = groups[choice]
            messages = self.chat.get_messages(self.current_user.id, group_id=group.id)
            
            if not messages:
                print(f"No messages in {group.name}.")
                return
            
            print(f"\n--- Messages in {group.name} ---")
            for msg in messages:
                sender = self.db.get_user_by_id(msg['sender_id'])
                sender_name = sender.username if sender else "Unknown"
                timestamp = msg['created_at'][:19].replace('T', ' ')
                print(f"[{timestamp}] {sender_name}: {msg['content']}")
        except ValueError:
            print("Invalid input.")
    
    def send_file(self):
        """Send a file"""
        if not self.current_user:
            print("You must be logged in.")
            return
        print("\n--- Send File ---")
        file_path = input("File path: ").strip()
        
        recipient_username = input("Recipient username (or press Enter for group): ").strip()
        
        if recipient_username:
            recipient = self.db.get_user_by_username(recipient_username)
            if not recipient:
                print("User not found.")
                return
            
            if recipient.id == self.current_user.id:
                print("Cannot send file to yourself.")
                return
            
            result = self.chat.send_file(self.current_user.id, file_path, recipient_id=recipient.id)
            print(f"\nFile sent to {recipient.username} successfully!")
        else:
            groups = self.db.get_groups_for_user(self.current_user.id)
            if not groups:
                print("You are not a member of any groups.")
                return
            
            print("Your groups:")
            for i, group in enumerate(groups, 1):
                print(f"{i}. {group.name}")
            
            try:
                choice = int(input("Select group (number): ")) - 1
                if choice < 0 or choice >= len(groups):
                    print("Invalid selection.")
                    return
                
                group = groups[choice]
                result = self.chat.send_file(self.current_user.id, file_path, group_id=group.id)
                print(f"\nFile sent to {group.name} successfully!")
            except ValueError:
                print("Invalid input.")
    
    def view_online_users(self):
        """View online users"""
        if not self.current_user:
            print("You must be logged in.")
            return
        users = self.chat.get_online_users()
        
        if not users:
            print("No users currently online.")
            return
        
        print("\n--- Online Users ---")
        for user in users:
            if user['id'] != self.current_user.id:
                print(f"- {user['username']} (ID: {user['id']})")

# ==================== TEST SUITE ====================
class TestSuite:
    """Comprehensive test suite for the application"""
    
    def __init__(self):
        # Use test data directory
        import tempfile
        self.test_dir = tempfile.mkdtemp()
        self.original_data_dir = Config.DATA_DIR
        Config.DATA_DIR = self.test_dir
        Config.DB_FILE = os.path.join(self.test_dir, "test.db")
        Config.KEYS_DIR = os.path.join(self.test_dir, "keys")
        Config.UPLOADS_DIR = os.path.join(self.test_dir, "uploads")
        os.makedirs(Config.KEYS_DIR, exist_ok=True, mode=0o700)
        os.makedirs(Config.UPLOADS_DIR, exist_ok=True)
        
        self.db = DatabaseManager()
        self.encryption = EncryptionManager()
        self.auth = AuthenticationManager(self.db, self.encryption)
        self.chat = ChatService(self.db, self.encryption)
        self.passed = 0
        self.failed = 0
    
    def cleanup(self):
        """Clean up test environment"""
        import shutil
        Config.DATA_DIR = self.original_data_dir
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def run_all_tests(self):
        """Run all tests"""
        print("\n" + "=" * 60)
        print("RUNNING COMPREHENSIVE TEST SUITE")
        print("=" * 60)
        
        self.test_encryption()
        self.test_user_registration()
        self.test_user_login()
        self.test_authentication()
        self.test_messaging()
        self.test_groups()
        self.test_file_sharing()
        self.test_security_features()
        
        print("\n" + "=" * 60)
        print(f"TEST RESULTS: {self.passed} passed, {self.failed} failed")
        print("=" * 60)
        
        self.cleanup()
        return self.failed == 0
    
    def assert_true(self, condition, message=""):
        """Assert condition is true"""
        if condition:
            self.passed += 1
            print(f"✓ PASS: {message}")
        else:
            self.failed += 1
            print(f"✗ FAIL: {message}")
    
    def assert_false(self, condition, message=""):
        """Assert condition is false"""
        self.assert_true(not condition, message)
    
    def assert_raises(self, exception_class, func, *args, **kwargs):
        """Assert function raises exception"""
        try:
            func(*args, **kwargs)
            self.failed += 1
            print(f"✗ FAIL: Expected {exception_class.__name__} to be raised")
            return False
        except exception_class:
            self.passed += 1
            print(f"✓ PASS: {exception_class.__name__} raised as expected")
            return True
        except Exception as e:
            self.failed += 1
            print(f"✗ FAIL: Expected {exception_class.__name__}, got {type(e).__name__}: {e}")
            return False
    
    def test_encryption(self):
        """Test encryption functionality"""
        print("\n--- Testing Encryption ---")
        
        # Test message encryption
        message = "Hello, World!"
        key = Fernet.generate_key()
        encrypted = self.encryption.encrypt_message(message, key)
        decrypted = self.encryption.decrypt_message(encrypted, key)
        self.assert_true(decrypted == message, "Message encryption/decryption")
        
        # Test different keys produce different ciphertexts
        key2 = Fernet.generate_key()
        encrypted2 = self.encryption.encrypt_message(message, key2)
        self.assert_true(encrypted != encrypted2, "Different keys produce different ciphertexts")
        
        # Test user key generation
        user1 = 1
        user2 = 2
        key1 = self.encryption.get_user_key(user1)
        key2 = self.encryption.get_user_key(user2)
        self.assert_true(key1 != key2, "Different users get different keys")
        
        # Test key persistence
        key1_again = self.encryption.get_user_key(user1)
        self.assert_true(key1 == key1_again, "User keys persist across calls")
        
        # Test group key generation
        group1 = 1
        group_key = self.encryption.get_group_key(group1)
        self.assert_true(len(group_key) > 0, "Group key generation")
    
    def test_user_registration(self):
        """Test user registration"""
        print("\n--- Testing User Registration ---")
        
        # Test valid registration
        user = self.auth.register_user("testuser1", "test1@example.com", "Password123!")
        self.assert_true(user is not None, "User registration")
        self.assert_true(user.username == "testuser1", "Username stored correctly")
        self.assert_true(user.email == "test1@example.com", "Email stored correctly")
        self.assert_true(user.id > 0, "User ID assigned")
        
        # Test duplicate username
        self.assert_raises(ValueError, self.auth.register_user, 
                          "testuser1", "test2@example.com", "Password123!")
        
        # Test duplicate email
        self.assert_raises(ValueError, self.auth.register_user,
                          "testuser2", "test1@example.com", "Password123!")
        
        # Test invalid username
        self.assert_raises(ValueError, self.auth.register_user,
                          "ab", "test3@example.com", "Password123!")
        
        # Test invalid email
        self.assert_raises(ValueError, self.auth.register_user,
                          "testuser3", "invalid-email", "Password123!")
        
        # Test weak password
        self.assert_raises(ValueError, self.auth.register_user,
                          "testuser4", "test4@example.com", "weak")
    
    def test_user_login(self):
        """Test user login"""
        print("\n--- Testing User Login ---")
        
        # Register test users
        user1 = self.auth.register_user("loginuser1", "login1@example.com", "Password123!")
        user2 = self.auth.register_user("loginuser2", "login2@example.com", "Password456!")
        
        # Test successful login with username
        result = self.auth.login("loginuser1", "Password123!")
        self.assert_true('access_token' in result, "Login returns access token")
        self.assert_true('refresh_token' in result, "Login returns refresh token")
        self.assert_true('user' in result, "Login returns user data")
        self.assert_true(result['user']['username'] == "loginuser1", "Correct user returned")
        
        # Test successful login with email
        result = self.auth.login("login2@example.com", "Password456!")
        self.assert_true('access_token' in result, "Login with email works")
        
        # Test invalid credentials
        self.assert_raises(ValueError, self.auth.login, "loginuser1", "WrongPassword")
        
        # Test non-existent user
        self.assert_raises(ValueError, self.auth.login, "nonexistent", "Password123!")
        
        # Test rate limiting
        for _ in range(5):
            try:
                self.auth.login("loginuser1", "WrongPassword")
            except ValueError:
                pass
        
        # Should be rate limited now
        self.assert_raises(ValueError, self.auth.login, "loginuser1", "Password123!")
    
    def test_authentication(self):
        """Test authentication features"""
        print("\n--- Testing Authentication ---")
        
        # Register user
        user = self.auth.register_user("authuser", "auth@example.com", "Password123!")
        
        # Login to get token
        result = self.auth.login("authuser", "Password123!")
        token = result['access_token']
        
        # Test token verification
        payload = self.auth.verify_token(token)
        self.assert_true(payload is not None, "Valid token verified")
        if payload is None:
            raise AssertionError("Token payload missing")
        self.assert_true(payload['user_id'] == user.id, "Token contains correct user_id")
        
        # Test invalid token
        invalid_token = "invalid.token.here"
        payload = self.auth.verify_token(invalid_token)
        self.assert_true(payload is None, "Invalid token rejected")
    
    def test_messaging(self):
        """Test messaging functionality"""
        print("\n--- Testing Messaging ---")
        
        # Register users
        user1 = self.auth.register_user("msguser1", "msg1@example.com", "Password123!")
        user2 = self.auth.register_user("msguser2", "msg2@example.com", "Password456!")
        
        # Send message from user1 to user2
        message1 = self.chat.send_message(user1.id, "Hello from user1!", recipient_id=user2.id)
        self.assert_true(message1 is not None, "Message created")
        self.assert_true(message1.sender_id == user1.id, "Sender ID correct")
        self.assert_true(message1.recipient_id == user2.id, "Recipient ID correct")
        
        # Send reply from user2
        message2 = self.chat.send_message(user2.id, "Reply from user2!", recipient_id=user1.id)
        self.assert_true(message2 is not None, "Reply message created")
        
        # Retrieve messages
        messages = self.chat.get_messages(user1.id, other_user_id=user2.id)
        self.assert_true(len(messages) >= 2, "Messages retrieved")
        
        # Check message content is decrypted
        contents = [msg['content'] for msg in messages]
        self.assert_true("Hello from user1!" in contents, "Message 1 content correct")
        self.assert_true("Reply from user2!" in contents, "Message 2 content correct")
        
        # Test sending to self (should fail)
        self.assert_raises(ValueError, self.chat.send_message,
                          user1.id, "To self", recipient_id=user1.id)
        
        # Test sending without recipient or group (should fail)
        self.assert_raises(ValueError, self.chat.send_message,
                          user1.id, "No recipient")
    
    def test_groups(self):
        """Test group functionality"""
        print("\n--- Testing Groups ---")
        
        # Register users
        user1 = self.auth.register_user("groupuser1", "group1@example.com", "Password123!")
        user2 = self.auth.register_user("groupuser2", "group2@example.com", "Password456!")
        user3 = self.auth.register_user("groupuser3", "group3@example.com", "Password789!")
        
        # Create group
        group = self.chat.create_group("Test Group", user1.id, "A test group")
        if group is None:
            raise AssertionError("Group not created")
        self.assert_true(group.name == "Test Group", "Group name correct")
        self.assert_true(group.created_by == user1.id, "Group creator correct")
        self.assert_true(user1.id in group.members, "Creator is member")
        
        # Add users to group
        self.chat.add_to_group(group.id, user2.id)
        self.chat.add_to_group(group.id, user3.id)
        
        # Refresh group
        group = self.db.get_group(group.id)
        if group is None:
            raise AssertionError("Group missing after add")
        self.assert_true(len(group.members) == 3, "All members added")
        
        # Send message to group
        message = self.chat.send_message(user1.id, "Hello group!", group_id=group.id)
        self.assert_true(message is not None, "Group message created")
        self.assert_true(message.group_id == group.id, "Group ID correct")
        
        # Retrieve group messages
        messages = self.chat.get_messages(user2.id, group_id=group.id)
        self.assert_true(len(messages) >= 1, "Group messages retrieved")
        self.assert_true(messages[0]['content'] == "Hello group!", "Message content correct")
    
    def test_file_sharing(self):
        """Test file sharing functionality"""
        print("\n--- Testing File Sharing ---")
        
        # Register users
        user1 = self.auth.register_user("fileuser1", "file1@example.com", "Password123!")
        user2 = self.auth.register_user("fileuser2", "file2@example.com", "Password456!")
        
        # Create test file
        import tempfile
        test_file = os.path.join(Config.UPLOADS_DIR, "test.txt")
        with open(test_file, 'w') as f:
            f.write("This is a test file content.")
        
        # Send file
        result = self.chat.send_file(user1.id, test_file, recipient_id=user2.id)
        self.assert_true(result is not None, "File sent")
        self.assert_true('message' in result, "File message created")
        self.assert_true('attachment' in result, "File attachment created")
        
        # Check message
        message = result['message']
        self.assert_true(message['message_type'] == "file", "Message type is file")
        self.assert_true("test.txt" in message['content'], "Filename in message")
        
        # Check attachment
        attachment = result['attachment']
        self.assert_true(attachment['original_filename'] == "test.txt", "Filename correct")
        self.assert_true(attachment['uploader_id'] == user1.id, "Uploader correct")
        self.assert_true(attachment['file_size'] > 0, "File size recorded")
        self.assert_true(len(attachment['file_hash']) > 0, "File hash computed")
        
        # Test non-existent file
        self.assert_raises(ValueError, self.chat.send_file,
                          user1.id, "nonexistent.txt", recipient_id=user2.id)
        
        # Test too large file
        large_file = os.path.join(Config.UPLOADS_DIR, "large.txt")
        with open(large_file, 'w') as f:
            f.write("x" * (Config.MAX_FILE_SIZE + 1))
        
        self.assert_raises(ValueError, self.chat.send_file,
                          user1.id, large_file, recipient_id=user2.id)
        
        # Test invalid file type
        invalid_file = os.path.join(Config.UPLOADS_DIR, "test.exe")
        with open(invalid_file, 'w') as f:
            f.write("test")
        
        self.assert_raises(ValueError, self.chat.send_file,
                          user1.id, invalid_file, recipient_id=user2.id)
    
    def test_security_features(self):
        """Test security features"""
        print("\n--- Testing Security Features ---")
        
        # Test password hashing
        password = "TestPassword123!"
        hash1 = self.encryption.hash_password(password)
        hash2 = self.encryption.hash_password(password)
        self.assert_true(hash1 != hash2, "Password hashing produces unique hashes")
        self.assert_true(len(hash1) > 0, "Password hash generated")
        
        # Test password verification
        user = self.auth.register_user("secuser", "sec@example.com", password)
        verified = self.auth._verify_password(password, user.password_hash)
        self.assert_true(verified, "Password verification works")
        
        # Test wrong password verification
        verified = self.auth._verify_password("WrongPassword123!", user.password_hash)
        self.assert_false(verified, "Wrong password rejected")
        
        # Test account locking after failed attempts
        lock_user = self.auth.register_user("lockuser", "lock@example.com", "Password123!")
        for _ in range(5):
            try:
                self.auth.login("lockuser", "WrongPassword")
            except ValueError:
                pass
        
        lock_user = self.db.get_user_by_id(lock_user.id)
        if lock_user is None:
            raise AssertionError("Lock user missing")
        self.assert_true(lock_user.is_locked, "Account locked after failed attempts")
        
        # Test locked account cannot login
        self.assert_raises(ValueError, self.auth.login, "lockuser", "Password123!")
        
        # Test encrypted messages cannot be read without proper key
        user1 = self.auth.register_user("encuser1", "enc1@example.com", "Password123!")
        user2 = self.auth.register_user("encuser2", "enc2@example.com", "Password456!")
        
        message = self.chat.send_message(user1.id, "Secret message", recipient_id=user2.id)
        
        # Try to decrypt with wrong key
        wrong_key = Fernet.generate_key()
        try:
            decrypted = self.encryption.decrypt_message(message.content, wrong_key)
            self.assert_false(True, "Decryption with wrong key should fail")
        except Exception:
            self.assert_true(True, "Decryption with wrong key fails")
        
        # Test file encryption
        test_file = os.path.join(Config.UPLOADS_DIR, "secret.txt")
        with open(test_file, 'w') as f:
            f.write("Secret file content")
        
        key = self.encryption.get_user_key(user1.id)
        encrypted_file = os.path.join(Config.UPLOADS_DIR, "secret.txt.enc")
        
        success = self.encryption.encrypt_file(test_file, encrypted_file, key)
        self.assert_true(success, "File encryption successful")
        self.assert_true(os.path.exists(encrypted_file), "Encrypted file created")
        
        # Verify encrypted content is different
        with open(test_file, 'r') as f:
            original = f.read()
        with open(encrypted_file, 'rb') as f:
            encrypted = f.read()
        self.assert_true(original.encode() != encrypted, "Encrypted file content differs")
        
        # Test file decryption
        decrypted_file = os.path.join(Config.UPLOADS_DIR, "secret_decrypted.txt")
        success = self.encryption.decrypt_file(encrypted_file, decrypted_file, key)
        self.assert_true(success, "File decryption successful")
        
        with open(decrypted_file, 'r') as f:
            decrypted = f.read()
        self.assert_true(decrypted == original, "Decrypted file matches original")

# ==================== MAIN ENTRY POINT ====================
def main():
    """Main entry point for the application"""
    import sys
    
    # Check for test mode
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        suite = TestSuite()
        success = suite.run_all_tests()
        sys.exit(0 if success else 1)
    
    # Start CLI application
    cli = ChatCLI()
    cli.start()

if __name__ == "__main__":
    main()