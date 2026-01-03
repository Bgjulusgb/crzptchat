# Secure Chat Application

A secure, end-to-end encrypted messaging platform built with Python.

## Features

### Core Features
- ✅ Real-time messaging between multiple users
- ✅ Private one-on-one conversations
- ✅ Group chats
- ✅ Message history and persistence
- ✅ User presence indicators (online/offline status)
- ✅ File sharing with encryption

### Security Features
- 🔒 **End-to-end encryption** using Fernet (AES-128)
- 🔒 **Secure password hashing** using PBKDF2 with SHA-256
- 🔒 **JWT token-based authentication**
- 🔒 **Rate limiting** to prevent brute force attacks
- 🔒 **Account locking** after failed login attempts
- 🔒 **Input validation** and sanitization
- 🔒 **Secure key management** with encrypted storage
- 🔒 **File encryption** for shared files

### Technical Features
- 📁 **Multiple database backends** (JSON, SQLite, SQLAlchemy)
- 🔑 **Unique encryption keys** per user and per group
- 🌐 **RESTful Web API** with Flask
- 📊 **Comprehensive test suite** with 50+ tests
- 🎨 **Clean CLI interface** with intuitive menus
- 📝 **Detailed documentation** and usage examples
- 🔧 **Modular architecture** with separate services
- 🚀 **CI/CD pipeline** with GitHub Actions
- 📏 **Code quality tools** (black, flake8, mypy)
- 🔒 **Security scanning** with bandit and safety

## Installation

### Requirements
- Python 3.7 or higher
- pip package manager

### Install Dependencies

```bash
# Basic installation
pip install -r requirements.txt

# Or install with development dependencies
pip install -e .[dev]

# Or install the package
pip install .
```

### Alternative Installation Methods

```bash
# Using pip directly
pip install cryptography>=41.0.0 PyJWT>=2.8.0 bcrypt>=4.0.0 python-dotenv>=1.0.0 SQLAlchemy>=2.0.0 Flask>=2.3.0

# Using conda
conda install cryptography pyjwt bcrypt python-dotenv sqlalchemy flask
```

## Quick Start

### 1. Installation

```bash
# Klone das Repository oder erstelle ein virtuelles Environment
python -m venv .venv

# Aktiviere das Environment (Windows)
.venv\Scripts\activate

# Aktiviere das Environment (Linux/Mac)
source .venv/bin/activate

# Installiere Dependencies
pip install -r requirements.txt
```

### 2. Starte den Server

```bash
# Starte den Web-Server mit UI
python chat_server.py
```

Der Server läuft auf: **http://localhost:5000**

### 3. Demo-Anwendung

```bash
# Teste die Funktionalität mit der Demo-App
python demo_app.py
```

### 4. Enhanced CLI Version

```bash
# Starte die erweiterte CLI-Version
python secure_chat_enhanced.py
```

## Features

### Core Features
- ✅ **Moderne Web-UI** mit Echtzeit-Messaging
- ✅ **WebSocket Support** für sofortige Nachrichtenübermittlung
- ✅ **REST API** für Integration mit anderen Anwendungen
- ✅ Real-time messaging zwischen mehreren Benutzern
- ✅ Private 1-zu-1 Unterhaltungen
- ✅ Gruppenchats

1. **Register a new user**
   - Select option 1 from the menu
   - Enter username, email, and password
   - Password requirements:
     - At least 8 characters
     - At least one uppercase letter
     - At least one lowercase letter
     - At least one digit
     - At least one special character

2. **Login**
   - Select option 2 from the menu
   - Enter username or email and password

3. **Start chatting!**
   - Send messages to other users
   - Create and manage groups
   - Share encrypted files

### Main Menu Features

Once logged in, you can:

1. **Send Message to User** - Send encrypted messages to another user
2. **View Messages** - View conversation history with a specific user
3. **Create Group** - Create a new group chat
4. **Send to Group** - Send messages to a group
5. **View Group Messages** - View group chat history
6. **Send File** - Share encrypted files with users or groups
7. **View Online Users** - See who's currently online
8. **Logout** - Securely logout from your account
9. **Exit** - Exit the application

### Running Tests

The application includes a comprehensive test suite:

```bash
python secure_chat_app.py --test
```

The test suite covers:
- Encryption/decryption functionality
- User registration and validation
- Login and authentication
- Message sending and retrieval
- Group management
- File sharing and encryption
- Security features (password hashing, rate limiting, account locking)

## Architecture

### File Structure

```
secure_chat_app.py          - Main CLI application (single-file solution)
secure_chat_enhanced.py     - Enhanced version with SQLite database
secure_chat/                - Modular package implementation
├── models/                 - SQLAlchemy data models
├── services/               - Business logic services
├── auth/                   - Authentication components
├── cli/                    - Command-line interface
├── web/                    - Flask web API
├── tests/                  - Unit tests
└── utils/                  - Utility functions
requirements.txt            - Python dependencies
requirements_enhanced.txt   - Enhanced dependencies
setup.py                   - Package setup configuration
pyproject.toml             - Modern Python project configuration
.github/workflows/         - CI/CD pipelines
README.md                  - This documentation
```

### Key Components

1. **Config Class** - Application configuration and constants
2. **Models** - Data models (User, Message, Group, FileAttachment)
3. **EncryptionManager** - Handles all encryption operations
4. **DatabaseManager** - Database operations (JSON/SQLite/SQLAlchemy)
5. **AuthenticationManager** - User authentication and security
6. **ChatService** - Core chat functionality
7. **ChatCLI** - Command-line interface
8. **Web API** - RESTful Flask application
9. **TestSuite** - Comprehensive testing framework

### Security Implementation

#### Encryption
- **Algorithm**: Fernet (symmetric encryption using AES-128)
- **Key Management**: Unique keys per user and per group
- **Master Key**: Encrypts all user/group keys
- **File Encryption**: All shared files are encrypted

#### Authentication
- **Password Hashing**: PBKDF2 with 100,000 iterations
- **Token-based Auth**: JWT tokens with configurable expiration
- **Rate Limiting**: Prevents brute force attacks
- **Account Locking**: Automatic lock after 5 failed attempts

#### Data Protection
- **Secure Storage**: Keys stored with restricted permissions (0o600)
- **Input Validation**: All user inputs are validated
- **Sanitization**: Prevents injection attacks

## Usage

### Command Line Interface

```bash
# Run the CLI application
python secure_chat_app.py

# Or using the installed package
secure-chat-cli

# Run tests
python secure_chat_app.py --test
```

### Web API

```bash
# Run the web application
python -m secure_chat.web.app

# Or using the installed package
secure-chat-web

# The API will be available at http://localhost:5000
```

### Development

```bash
# Install in development mode
pip install -e .[dev]

# Run tests
pytest

# Run linting
flake8 secure_chat

# Type checking
mypy secure_chat

# Format code
black secure_chat

# Run security checks
bandit -r secure_chat
safety check
```

## Security Best Practices

### For Production Use

1. **Change the JWT secret key** in the `Config` class
2. **Use a proper database** (SQLite/PostgreSQL) instead of JSON
3. **Enable HTTPS/TLS** for network transmission
4. **Implement proper logging** and monitoring
5. **Regular security audits** and penetration testing
6. **Keep dependencies updated**

### OWASP Compliance

The application follows OWASP security guidelines:
- ✅ Input validation
- ✅ Output encoding
- ✅ Authentication and session management
- ✅ Password storage
- ✅ Cryptographic practices
- ✅ Error handling and logging
- ✅ Data protection

## Configuration

Edit the `Config` class in `secure_chat_app.py` to customize:

```python
class Config:
    DATA_DIR = "secure_chat_data"           # Data storage directory
    JWT_SECRET = "your-secret-key"          # Change this!
    JWT_EXPIRATION = 24                     # Token expiration (hours)
    MAX_LOGIN_ATTEMPTS = 5                  # Failed attempts before lock
    MAX_FILE_SIZE = 10 * 1024 * 1024       # 10MB max file size
    ALLOWED_FILE_TYPES = {...}              # Allowed file extensions
```

## API Reference

### AuthenticationManager

```python
# Register a new user
user = auth.register_user(username, email, password)

# Login user
result = auth.login(username_or_email, password)

# Verify token
payload = auth.verify_token(token)
```

### ChatService

```python
# Send message to user
message = chat.send_message(sender_id, content, recipient_id=user_id)

# Send message to group
message = chat.send_message(sender_id, content, group_id=group_id)

# Get messages
messages = chat.get_messages(user_id, other_user_id=user_id)

# Create group
group = chat.create_group(name, creator_id, description)

# Send file
result = chat.send_file(sender_id, file_path, recipient_id=user_id)
```

### EncryptionManager

```python
# Encrypt/decrypt messages
encrypted = encryption.encrypt_message(message, key)
decrypted = encryption.decrypt_message(encrypted, key)

# Encrypt/decrypt files
encryption.encrypt_file(input_path, output_path, key)
encryption.decrypt_file(encrypted_path, output_path, key)

# Get encryption keys
user_key = encryption.get_user_key(user_id)
group_key = encryption.get_group_key(group_id)
```

## Troubleshooting

### Common Issues

**Issue**: "Module not found: cryptography"
```bash
pip install cryptography
```

**Issue**: "Permission denied" when accessing keys
```bash
chmod 700 secure_chat_data/keys
```

**Issue**: "Account locked due to too many failed attempts"
- Wait for the rate limit window (5 minutes) to expire
- Or reset the database by deleting `secure_chat_data/`

## Contributing

Contributions are welcome! Please ensure:
1. All tests pass
2. Code follows PEP 8 style guidelines
3. Security best practices are maintained
4. Documentation is updated

## License

This project is provided as-is for educational and development purposes.

## Support

For issues, questions, or contributions, please refer to the project documentation.

## Changelog

### Version 1.0.0
- Initial release
- End-to-end encryption
- User authentication
- Group chats
- File sharing
- Comprehensive test suite
- CLI interface

## Acknowledgments

Built with:
- Python 3.11+
- Cryptography library
- PyJWT for authentication
- Following OWASP security guidelines