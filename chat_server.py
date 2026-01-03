"""
Secure Chat Server - Flask REST API with WebSocket Support
A modern web server for the secure chat application
"""

import os
import sys
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime
from typing import Dict, List, Optional
import logging

# Import from secure_chat package
sys.path.insert(0, os.path.dirname(__file__))
from secure_chat_enhanced import (
    DatabaseManager,
    AuthenticationManager,
    EncryptionManager,
    InputValidator,
    Config
)

# Initialize Flask app
app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = Config.JWT_SECRET
CORS(app)

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize managers
db = DatabaseManager()
auth_manager = AuthenticationManager(db)
encryption = EncryptionManager()

# Track online users
online_users: Dict[str, str] = {}  # user_id -> socket_id

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==================== Helper Functions ====================

def get_user_from_token(token: str) -> Optional[int]:
    """Extract user ID from JWT token"""
    if not token:
        return None
    
    payload = auth_manager.verify_jwt_token(token)
    if payload:
        return payload.get('user_id')
    return None


# ==================== REST API Endpoints ====================

@app.route('/')
def index():
    """Serve the main chat UI"""
    return render_template('chat.html')


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'database': 'connected'
    })


@app.route('/api/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        # Validate inputs
        if not InputValidator.validate_username(username):
            return jsonify({
                'success': False,
                'message': 'Invalid username. Must be 3-50 characters, alphanumeric with _ or -'
            }), 400
        
        if not InputValidator.validate_email(email):
            return jsonify({
                'success': False,
                'message': 'Invalid email address'
            }), 400
        
        is_valid, errors = InputValidator.validate_password(password)
        if not is_valid:
            return jsonify({
                'success': False,
                'message': 'Invalid password',
                'errors': errors
            }), 400
        
        # Check if user already exists
        existing_user = db.get_user_by_username(username)
        if existing_user:
            return jsonify({
                'success': False,
                'message': 'Username already exists'
            }), 400
        
        existing_email = db.get_user_by_email(email)
        if existing_email:
            return jsonify({
                'success': False,
                'message': 'Email already registered'
            }), 400
        
        # Hash password and create user
        password_hash = auth_manager.hash_password(password)
        user = db.create_user(username, email, password_hash)
        
        if not user:
            return jsonify({
                'success': False,
                'message': 'Failed to create user'
            }), 500
        
        # Create JWT token
        token = auth_manager.create_jwt_token(user.id, user.username)
        result = {'success': True, 'token': token, 'user': user}
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': 'Registration successful',
                'token': result['token'],
                'user': {
                    'id': result['user'].id,
                    'username': result['user'].username,
                    'email': result['user'].email
                }
            }), 201
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
            
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({
            'success': False,
            'message': 'Registration failed'
        }), 500


@app.route('/api/login', methods=['POST'])
def login():
    """Login user"""
    try:
        data = request.get_json()
        username_or_email = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username_or_email or not password:
            return jsonify({
                'success': False,
                'message': 'Username/email and password are required'
            }), 400
        
        # Try to find user by username or email
        user = db.get_user_by_username(username_or_email)
        if not user:
            user = db.get_user_by_email(username_or_email)
        
        if not user:
            return jsonify({
                'success': False,
                'message': 'Invalid credentials'
            }), 401
        
        # Verify password
        if not auth_manager.verify_password(password, user.password_hash):
            return jsonify({
                'success': False,
                'message': 'Invalid credentials'
            }), 401
        
        # Update last login
        user.last_login = datetime.utcnow().isoformat()
        db.update_user(user)
        
        # Create JWT token
        token = auth_manager.create_jwt_token(user.id, user.username)
        
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'token': token,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'status': user.status,
                'display_name': user.display_name
            }
        }), 200
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({
            'success': False,
            'message': 'Login failed'
        }), 500


@app.route('/api/users', methods=['GET'])
def get_users():
    """Get all users"""
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_id = get_user_from_token(token)
        
        if not user_id:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
        users = db.get_all_users(limit=100)
        
        return jsonify({
            'success': True,
            'users': [{
                'id': user.id,
                'username': user.username,
                'display_name': user.display_name or user.username,
                'status': user.status,
                'is_online': user.id in [int(uid) for uid in online_users.keys()]
            } for user in users if user.id != user_id]
        }), 200
        
    except Exception as e:
        logger.error(f"Get users error: {e}")
        return jsonify({'success': False, 'message': 'Failed to get users'}), 500


@app.route('/api/messages/<int:other_user_id>', methods=['GET'])
def get_messages(other_user_id: int):
    """Get messages with another user"""
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_id = get_user_from_token(token)
        
        if not user_id:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        messages = db.get_messages_between_users(user_id, other_user_id, limit, offset)
        
        # Decrypt messages
        decrypted_messages = []
        for msg in messages:
            try:
                if msg.is_encrypted:
                    decrypted_content = encryption.decrypt(msg.content, msg.content_nonce)
                else:
                    decrypted_content = msg.content
                
                decrypted_messages.append({
                    'id': msg.id,
                    'sender_id': msg.sender_id,
                    'recipient_id': msg.recipient_id,
                    'content': decrypted_content,
                    'created_at': msg.created_at,
                    'is_read': msg.is_read,
                    'message_type': msg.message_type
                })
            except Exception as e:
                logger.error(f"Error decrypting message {msg.id}: {e}")
                continue
        
        return jsonify({
            'success': True,
            'messages': decrypted_messages
        }), 200
        
    except Exception as e:
        logger.error(f"Get messages error: {e}")
        return jsonify({'success': False, 'message': 'Failed to get messages'}), 500


@app.route('/api/groups', methods=['GET'])
def get_groups():
    """Get user's groups"""
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_id = get_user_from_token(token)
        
        if not user_id:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
        groups = db.get_groups_for_user(user_id)
        
        return jsonify({
            'success': True,
            'groups': [{
                'id': group.id,
                'name': group.name,
                'description': group.description,
                'member_count': group.member_count,
                'created_at': group.created_at
            } for group in groups]
        }), 200
        
    except Exception as e:
        logger.error(f"Get groups error: {e}")
        return jsonify({'success': False, 'message': 'Failed to get groups'}), 500


@app.route('/api/groups', methods=['POST'])
def create_group():
    """Create a new group"""
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_id = get_user_from_token(token)
        
        if not user_id:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
        data = request.get_json()
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        
        if not name or len(name) < 3:
            return jsonify({
                'success': False,
                'message': 'Group name must be at least 3 characters'
            }), 400
        
        group = db.create_group(name, user_id, description)
        
        if group:
            return jsonify({
                'success': True,
                'message': 'Group created successfully',
                'group': {
                    'id': group.id,
                    'name': group.name,
                    'description': group.description,
                    'created_at': group.created_at
                }
            }), 201
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to create group'
            }), 500
            
    except Exception as e:
        logger.error(f"Create group error: {e}")
        return jsonify({'success': False, 'message': 'Failed to create group'}), 500


# ==================== WebSocket Events ====================

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info("Client connected")
    emit('connected', {'message': 'Connected to server'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info("Client disconnected")
    # Note: User status will timeout after 5 minutes of inactivity
    # based on last_seen timestamp


@socketio.on('authenticate')
def handle_authenticate(data):
    """Authenticate user via WebSocket"""
    try:
        token = data.get('token')
        user_id = get_user_from_token(token)
        
        if user_id:
            # Store user as online (using user_id as key)
            # Note: We don't have access to session ID in this context reliably
            online_users[str(user_id)] = str(user_id)
            
            # Update user status in database
            user = db.get_user_by_id(user_id)
            if user:
                user.status = 'online'
                user.last_seen = datetime.utcnow().isoformat()
                db.update_user(user)
            
            emit('authenticated', {
                'success': True,
                'user_id': user_id
            })
            
            # Notify others that user is online
            emit('user_status', {
                'user_id': user_id,
                'status': 'online'
            }, broadcast=True)
        else:
            emit('authenticated', {
                'success': False,
                'message': 'Invalid token'
            })
            
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        emit('error', {'message': 'Authentication failed'})


@socketio.on('send_message')
def handle_send_message(data):
    """Handle sending a message"""
    try:
        token = data.get('token')
        sender_id = get_user_from_token(token)
        
        if not sender_id:
            emit('error', {'message': 'Unauthorized'})
            return
        
        recipient_id = data.get('recipient_id')
        content = data.get('content', '').strip()
        
        if not content:
            emit('error', {'message': 'Message content is required'})
            return
        
        # Sanitize content
        content = InputValidator.sanitize_message(content)
        
        # Encrypt message (returns tuple of encrypted_data, nonce)
        encrypted_content, nonce = encryption.encrypt(content)
        
        # Save to database
        message = db.create_message(
            sender_id=sender_id,
            recipient_id=recipient_id,
            content=encrypted_content,
            content_nonce=nonce
        )
        
        if message:
            # Emit to recipient if online
            recipient_sid = online_users.get(str(recipient_id))
            if recipient_sid:
                socketio.emit('new_message', {
                    'id': message.id,
                    'sender_id': sender_id,
                    'recipient_id': recipient_id,
                    'content': content,
                    'created_at': message.created_at
                }, to=recipient_sid)
            
            # Confirm to sender
            emit('message_sent', {
                'success': True,
                'message': {
                    'id': message.id,
                    'content': content,
                    'created_at': message.created_at
                }
            })
        else:
            emit('error', {'message': 'Failed to send message'})
            
    except Exception as e:
        logger.error(f"Send message error: {e}")
        emit('error', {'message': 'Failed to send message'})


@socketio.on('typing')
def handle_typing(data):
    """Handle typing indicator"""
    try:
        token = data.get('token')
        user_id = get_user_from_token(token)
        
        if not user_id:
            return
        
        recipient_id = data.get('recipient_id')
        is_typing = data.get('is_typing', False)
        
        # Emit to recipient if online
        recipient_sid = online_users.get(str(recipient_id))
        if recipient_sid:
            socketio.emit('user_typing', {
                'user_id': user_id,
                'is_typing': is_typing
            }, to=recipient_sid)
            
    except Exception as e:
        logger.error(f"Typing error: {e}")


# ==================== Main ====================

if __name__ == '__main__':
    print("=" * 60)
    print("Secure Chat Server")
    print("=" * 60)
    print(f"Server starting on http://localhost:5000")
    print(f"Press Ctrl+C to stop the server")
    print("=" * 60)
    
    # Run server
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
