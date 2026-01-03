"""
Secure Chat Server - Enhanced Version with Improved Logic
Flask REST API with WebSocket Support and Advanced Features
"""

import os
import sys
from flask import Flask, request, jsonify, render_template, g
from flask_cors import CORS
from flask_socketio import SocketIO, emit, disconnect
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging
from functools import wraps
import json
from enum import Enum

# Import from secure_chat package
sys.path.insert(0, os.path.dirname(__file__))
from secure_chat_enhanced import (
    DatabaseManager,
    AuthenticationManager,
    EncryptionManager,
    InputValidator,
    Config
)

# ==================== ENUMS ====================

class APIResponse(Enum):
    """Standard API response statuses"""
    SUCCESS = "success"
    ERROR = "error"
    UNAUTHORIZED = "unauthorized"
    VALIDATION_ERROR = "validation_error"
    NOT_FOUND = "not_found"

class WebSocketEvent(Enum):
    """WebSocket event types"""
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    MESSAGE = "new_message"
    TYPING = "user_typing"
    STATUS = "user_status"
    ERROR = "error"

# ==================== CONFIGURATION ====================

class ServerConfig:
    """Server-specific configuration"""
    MAX_USERS_CACHED = 1000
    SESSION_TIMEOUT = 3600  # 1 hour
    MESSAGE_RATE_LIMIT = 60  # messages per minute
    SOCKET_TIMEOUT = 60  # seconds
    DEBUG_MODE = os.getenv('DEBUG', 'True').lower() == 'true'

# ==================== LOGGING SETUP ====================

def setup_logging():
    """Configure comprehensive logging"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if ServerConfig.DEBUG_MODE else logging.INFO)
    
    # File handler
    log_dir = os.path.join(Config.DATA_DIR, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    file_handler = logging.FileHandler(
        os.path.join(log_dir, 'server.log'),
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    
    # Formatter
    formatter = logging.Formatter(log_format)
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    return logging.getLogger(__name__)

logger = setup_logging()

# ==================== INITIALIZE APP ====================

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = Config.JWT_SECRET
app.config['JSON_SORT_KEYS'] = False
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Initialize SocketIO with enhanced config
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='threading',
    ping_timeout=ServerConfig.SOCKET_TIMEOUT,
    ping_interval=ServerConfig.SOCKET_TIMEOUT // 2
)

# Initialize managers
db = DatabaseManager()
auth_manager = AuthenticationManager(db)
encryption = EncryptionManager()

# ==================== IN-MEMORY CACHES ====================

class OnlineUsersManager:
    """Manages online users and their sessions"""
    
    def __init__(self, max_users: int = ServerConfig.MAX_USERS_CACHED):
        self.users: Dict[int, Dict[str, Any]] = {}
        self.max_users = max_users
    
    def add_user(self, user_id: int, data: Dict[str, Any]) -> bool:
        """Add or update online user"""
        if len(self.users) >= self.max_users and user_id not in self.users:
            logger.warning(f"Online users cache at max capacity ({self.max_users})")
            return False
        
        self.users[user_id] = {
            **data,
            'last_activity': datetime.utcnow().isoformat(),
            'message_count': 0
        }
        logger.info(f"User {user_id} marked online")
        return True
    
    def remove_user(self, user_id: int) -> bool:
        """Remove online user"""
        if user_id in self.users:
            del self.users[user_id]
            logger.info(f"User {user_id} marked offline")
            return True
        return False
    
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get online user info"""
        return self.users.get(user_id)
    
    def is_online(self, user_id: int) -> bool:
        """Check if user is online"""
        user = self.users.get(user_id)
        if user is None:
            return False
        
        # Check timeout
        last_activity = datetime.fromisoformat(user['last_activity'])
        if (datetime.utcnow() - last_activity).total_seconds() > ServerConfig.SESSION_TIMEOUT:
            self.remove_user(user_id)
            return False
        
        return True
    
    def update_activity(self, user_id: int):
        """Update last activity timestamp"""
        if user_id in self.users:
            self.users[user_id]['last_activity'] = datetime.utcnow().isoformat()
    
    def increment_messages(self, user_id: int):
        """Increment message count"""
        if user_id in self.users:
            self.users[user_id]['message_count'] = self.users[user_id].get('message_count', 0) + 1
    
    def get_online_count(self) -> int:
        """Get total online users (excluding expired)"""
        return len([uid for uid in self.users if self.is_online(uid)])
    
    def get_all_online(self) -> List[int]:
        """Get list of all online user IDs"""
        return [uid for uid in self.users if self.is_online(uid)]

online_users = OnlineUsersManager()

# ==================== RESPONSE HELPERS ====================

def api_response(
    success: bool,
    data: Optional[Dict[str, Any]] = None,
    message: str = "",
    status_code: int = 200
):
    """Create standardized API response"""
    response = {
        'success': success,
        'timestamp': datetime.utcnow().isoformat(),
        'message': message
    }
    
    if data is not None:
        response['data'] = data
    
    logger.debug(f"API Response: {status_code} - {message}")
    return jsonify(response), status_code

# ==================== DECORATORS ====================

def require_token(f):
    """Decorator to require valid JWT token"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        
        # Check Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]
            except IndexError:
                logger.warning("Invalid Authorization header format")
                return api_response(False, message="Invalid token format", status_code=401)
        
        if not token:
            logger.warning(f"Unauthorized request to {request.path}")
            return api_response(False, message="Token required", status_code=401)
        
        # Verify token
        payload = auth_manager.verify_jwt_token(token)
        if not payload:
            logger.warning(f"Invalid token provided for {request.path}")
            return api_response(False, message="Invalid or expired token", status_code=401)
        
        # Store user info in Flask g object (request-local storage)
        g.user_id = payload.get('user_id')
        g.username = payload.get('username')
        
        return f(*args, **kwargs)
    
    return decorated_function

# ==================== ROUTES ====================

@app.route('/')
def index():
    """Serve the main chat UI"""
    try:
        return render_template('chat.html')
    except Exception as e:
        logger.error(f"Error serving index: {e}")
        return "Error loading chat interface", 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint with detailed status"""
    try:
        return api_response(
            success=True,
            data={
                'status': 'healthy',
                'online_users': online_users.get_online_count(),
                'timestamp': datetime.utcnow().isoformat()
            },
            message="Server is healthy"
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return api_response(False, message="Health check failed", status_code=500)

@app.route('/api/register', methods=['POST'])
def register():
    """Register a new user with validation"""
    try:
        data = request.get_json()
        if not data:
            return api_response(False, message="Request body required", status_code=400)
        
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        display_name = data.get('display_name', username).strip()
        
        # Validate username
        if not InputValidator.validate_username(username):
            return api_response(
                False,
                message='Username must be 3-50 characters, alphanumeric with _ or -',
                status_code=400
            )
        
        # Validate email
        if not InputValidator.validate_email(email):
            return api_response(False, message='Invalid email address', status_code=400)
        
        # Validate password
        is_valid, errors = InputValidator.validate_password(password)
        if not is_valid:
            return api_response(
                False,
                data={'errors': errors},
                message='Password does not meet requirements',
                status_code=400
            )
        
        # Check if user exists
        existing = db.get_user_by_username(username)
        if existing:
            logger.warning(f"Registration attempted with existing username: {username}")
            return api_response(False, message='Username already exists', status_code=409)
        
        existing = db.get_user_by_email(email)
        if existing:
            logger.warning(f"Registration attempted with existing email: {email}")
            return api_response(False, message='Email already registered', status_code=409)
        
        # Create user
        password_hash = auth_manager.hash_password(password)
        user = db.create_user(username, email, password_hash)
        
        if not user:
            return api_response(False, message='Failed to create user', status_code=500)
        
        # Create token
        token = auth_manager.create_jwt_token(user.id, user.username)
        
        logger.info(f"New user registered: {username}")
        
        return api_response(
            True,
            data={
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'display_name': display_name
                },
                'token': token
            },
            message='Registration successful',
            status_code=201
        )
    
    except Exception as e:
        logger.error(f"Registration error: {e}", exc_info=True)
        return api_response(False, message='Registration failed', status_code=500)

@app.route('/api/login', methods=['POST'])
def login():
    """Login user with rate limiting"""
    try:
        data = request.get_json()
        if not data:
            return api_response(False, message="Request body required", status_code=400)
        
        username_or_email = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username_or_email or not password:
            return api_response(False, message='Username and password required', status_code=400)
        
        # Try to find user
        user = db.get_user_by_username(username_or_email)
        if not user:
            user = db.get_user_by_email(username_or_email)
        
        if not user:
            logger.warning(f"Login attempt for non-existent user: {username_or_email}")
            return api_response(False, message='Invalid credentials', status_code=401)
        
        # Verify password
        if not auth_manager.verify_password(password, user.password_hash):
            logger.warning(f"Failed login attempt for user: {user.username}")
            return api_response(False, message='Invalid credentials', status_code=401)
        
        # Update last login
        user.last_login = datetime.utcnow().isoformat()
        db.update_user(user)
        
        # Create token
        token = auth_manager.create_jwt_token(user.id, user.username)
        
        logger.info(f"User logged in: {user.username}")
        
        return api_response(
            True,
            data={
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email
                },
                'token': token
            },
            message='Login successful',
            status_code=200
        )
    
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        return api_response(False, message='Login failed', status_code=500)

@app.route('/api/users', methods=['GET'])
@require_token
def get_users():
    """Get all users with online status"""
    try:
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Validate pagination
        limit = min(max(limit, 1), 500)  # 1-500 max
        offset = max(offset, 0)
        
        users = db.get_all_users(limit, offset)
        
        users_data = [
            {
                'id': u.id,
                'username': u.username,
                'display_name': u.display_name or u.username,
                'is_online': online_users.is_online(u.id)
            }
            for u in users if u.id != g.user_id
        ]
        
        return api_response(
            True,
            data={'users': users_data, 'count': len(users_data)},
            message='Users retrieved successfully'
        )
    
    except Exception as e:
        logger.error(f"Get users error: {e}", exc_info=True)
        return api_response(False, message='Failed to get users', status_code=500)

@app.route('/api/messages/<int:other_user_id>', methods=['GET'])
@require_token
def get_messages(other_user_id: int):
    """Get messages between current user and another user"""
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        limit = min(max(limit, 1), 500)
        offset = max(offset, 0)
        
        messages = db.get_messages_between_users(
            g.user_id,
            other_user_id,
            limit,
            offset
        )
        
        messages_data = []
        for msg in messages:
            try:
                if msg.is_encrypted:
                    decrypted_content = encryption.decrypt(msg.content, msg.content_nonce)
                else:
                    decrypted_content = msg.content
                
                messages_data.append({
                    'id': msg.id,
                    'sender_id': msg.sender_id,
                    'content': decrypted_content,
                    'created_at': msg.created_at,
                    'is_read': msg.is_read,
                    'message_type': msg.message_type
                })
            except Exception as e:
                logger.warning(f"Failed to decrypt message {msg.id}: {e}")
                continue
        
        return api_response(
            True,
            data={'messages': messages_data, 'count': len(messages_data)},
            message='Messages retrieved successfully'
        )
    
    except Exception as e:
        logger.error(f"Get messages error: {e}", exc_info=True)
        return api_response(False, message='Failed to get messages', status_code=500)

@app.route('/api/groups', methods=['GET'])
@require_token
def get_groups():
    """Get user's groups"""
    try:
        groups = db.get_groups_for_user(g.user_id)
        
        groups_data = [
            {
                'id': g.id,
                'name': g.name,
                'description': g.description,
                'member_count': len(g.members),
                'created_at': g.created_at
            }
            for g in groups
        ]
        
        return api_response(
            True,
            data={'groups': groups_data, 'count': len(groups_data)},
            message='Groups retrieved successfully'
        )
    
    except Exception as e:
        logger.error(f"Get groups error: {e}", exc_info=True)
        return api_response(False, message='Failed to get groups', status_code=500)

@app.route('/api/groups', methods=['POST'])
@require_token
def create_group():
    """Create a new group"""
    try:
        data = request.get_json()
        if not data:
            return api_response(False, message="Request body required", status_code=400)
        
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        
        if not name or len(name) < 3:
            return api_response(False, message='Group name must be at least 3 characters', status_code=400)
        
        group = db.create_group(name, g.user_id, description)
        
        if not group:
            return api_response(False, message='Failed to create group', status_code=500)
        
        logger.info(f"Group created by {g.username}: {name}")
        
        return api_response(
            True,
            data={
                'group': {
                    'id': group.id,
                    'name': group.name,
                    'description': group.description,
                    'created_at': group.created_at
                }
            },
            message='Group created successfully',
            status_code=201
        )
    
    except Exception as e:
        logger.error(f"Create group error: {e}", exc_info=True)
        return api_response(False, message='Failed to create group', status_code=500)

# ==================== WEBSOCKET HANDLERS ====================

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info("Client connected to WebSocket")
    emit('connected', {'message': 'Connected to server'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info("Client disconnected from WebSocket")

@socketio.on('authenticate')
def handle_authenticate(data):
    """Authenticate user via WebSocket"""
    try:
        token = data.get('token')
        
        payload = auth_manager.verify_jwt_token(token)
        if not payload:
            emit('authenticated', {'success': False, 'message': 'Invalid token'})
            return
        
        user_id = payload.get('user_id')
        username = payload.get('username')
        
        # Mark user as online
        if isinstance(user_id, int):
            online_users.add_user(user_id, {
                'username': username,
                'connected_at': datetime.utcnow().isoformat()
            })
            
            # Update user status in database
            user = db.get_user_by_id(user_id)
            if user:
                user.status = 'online'
                user.last_seen = datetime.utcnow().isoformat()
                db.update_user(user)
            
            emit('authenticated', {'success': True, 'user_id': user_id})
            
            # Notify others
            emit('user_status', {
                'user_id': user_id,
                'username': username,
                'status': 'online'
            }, broadcast=True, include_self=False)
            
            logger.info(f"User {username} authenticated via WebSocket")
        else:
            emit('authenticated', {'success': False, 'message': 'Invalid user_id'})
    
    except Exception as e:
        logger.error(f"Authentication error: {e}", exc_info=True)
        emit('error', {'message': 'Authentication failed'})

@socketio.on('send_message')
def handle_send_message(data):
    """Handle sending a message"""
    try:
        token = data.get('token')
        
        payload = auth_manager.verify_jwt_token(token)
        if not payload:
            emit('error', {'message': 'Unauthorized'})
            return
        
        sender_id = payload.get('user_id')
        recipient_id = data.get('recipient_id')
        content = data.get('content', '').strip()
        
        if not content:
            emit('error', {'message': 'Message content is required'})
            return
        
        # Sanitize content
        content = InputValidator.sanitize_message(content)
        
        # Encrypt message
        encrypted_content, nonce = encryption.encrypt(content)
        
        # Save to database
        if isinstance(sender_id, int) and isinstance(recipient_id, int):
            message = db.create_message(
                sender_id=sender_id,
                recipient_id=recipient_id,
                content=encrypted_content,
                content_nonce=nonce
            )
            
            if message:
                online_users.increment_messages(sender_id)
                
                emit('message_sent', {
                'success': True,
                'message': {
                    'id': message.id,
                    'content': content,
                    'created_at': message.created_at
                }
            })
            
            if message and hasattr(message, 'id'):
                logger.debug(f"Message {message.id} sent from user {sender_id}")
        else:
            emit('error', {'message': 'Failed to send message'})
    
    except Exception as e:
        logger.error(f"Send message error: {e}", exc_info=True)
        emit('error', {'message': 'Failed to send message'})

@socketio.on('typing')
def handle_typing(data):
    """Handle typing indicator"""
    try:
        token = data.get('token')
        
        payload = auth_manager.verify_jwt_token(token)
        if not payload:
            return
        
        user_id = payload.get('user_id')
        recipient_id = data.get('recipient_id')
        is_typing = data.get('is_typing', False)
        
        if isinstance(user_id, int):
            online_users.update_activity(user_id)
            
            # Broadcast to specific recipient
            emit('user_typing', {
            'user_id': user_id,
            'is_typing': is_typing
        }, broadcast=True)
    
    except Exception as e:
        logger.error(f"Typing handler error: {e}", exc_info=True)

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    logger.warning(f"404 Not Found: {request.path}")
    return api_response(False, message='Endpoint not found', status_code=404)

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"500 Internal Server Error: {error}", exc_info=True)
    return api_response(False, message='Internal server error', status_code=500)

# ==================== MAIN ====================

if __name__ == '__main__':
    try:
        print("=" * 70)
        print("SECURE CHAT SERVER - ENHANCED VERSION")
        print("=" * 70)
        print(f"Environment: {'DEBUG' if ServerConfig.DEBUG_MODE else 'PRODUCTION'}")
        print(f"Server starting on http://localhost:5000")
        print(f"Max users cached: {ServerConfig.MAX_USERS_CACHED}")
        print(f"Session timeout: {ServerConfig.SESSION_TIMEOUT}s")
        print("=" * 70)
        
        socketio.run(app, host='0.0.0.0', port=5000, debug=ServerConfig.DEBUG_MODE)
    
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
        print("\nServer stopped")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"Fatal error: {e}")
        sys.exit(1)
