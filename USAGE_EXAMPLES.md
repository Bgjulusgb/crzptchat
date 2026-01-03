# Secure Chat Application - Usage Examples

This document provides detailed examples of how to use the Secure Chat Application.

## Table of Contents

1. [Installation](#installation)
2. [First-Time Setup](#first-time-setup)
3. [Basic Usage](#basic-usage)
4. [Advanced Features](#advanced-features)
5. [Security Features](#security-features)
6. [Testing](#testing)
7. [Troubleshooting](#troubleshooting)

## Installation

### Step 1: Install Python Dependencies

```bash
# Install all required packages
pip install -r requirements.txt

# Or install individually
pip install cryptography>=41.0.0
pip install bcrypt>=4.0.0
pip install PyJWT>=2.8.0
```

### Step 2: Verify Installation

```bash
python secure_chat_app.py --test
```

You should see test results showing all tests passing.

## First-Time Setup

### Example 1: Registering Your First User

```
============================================================
    SECURE CHAT APPLICATION
    End-to-End Encrypted Messaging
============================================================

1. Register
2. Login
3. Exit

Choose an option (1-3): 1

--- Registration ---
Username: alice
Email: alice@example.com
Password: SecurePass123!

Registration successful! Your user ID is: 1
```

### Example 2: Registering Multiple Users

```
Choose an option (1-3): 1

--- Registration ---
Username: bob
Email: bob@example.com
Password: StrongPass456!

Registration successful! Your user ID is: 2

Choose an option (1-3): 1

--- Registration ---
Username: charlie
Email: charlie@example.com
Password: ComplexPass789!

Registration successful! Your user ID is: 3
```

## Basic Usage

### Example 3: Logging In

```
1. Register
2. Login
3. Exit

Choose an option (1-3): 2

--- Login ---
Username or Email: alice
Password: SecurePass123!

Login successful! Welcome, alice
```

### Example 4: Sending a Message to Another User

```
Welcome, alice!
Status: Online

1. Send Message to User
2. View Messages
3. Create Group
4. Send to Group
5. View Group Messages
6. Send File
7. View Online Users
8. Logout
9. Exit

Choose an option (1-9): 1

--- Send Message ---
Recipient username: bob
Message: Hey Bob, how are you?

Message sent successfully (ID: 1)
```

### Example 5: Viewing Messages

```
Choose an option (1-9): 2

--- View Messages ---
View messages with: bob

--- Conversation with bob ---
[2024-01-15 10:30:45] alice: Hey Bob, how are you?
[2024-01-15 10:31:20] bob: Hey Alice! I'm doing great, thanks for asking!
[2024-01-15 10:32:10] alice: That's wonderful! Want to chat more later?
```

## Advanced Features

### Example 6: Creating a Group

```
Choose an option (1-9): 3

--- Create Group ---
Group name: Development Team
Description: Team for discussing development topics

Group created successfully! (ID: 1)
```

### Example 7: Sending Messages to a Group

```
Choose an option (1-9): 4

--- Send Group Message ---
Your groups:
1. Development Team

Select group (number): 1
Message: Welcome everyone to the Development Team group!

Message sent to Development Team (ID: 2)
```

### Example 8: Viewing Group Messages

```
Choose an option (1-9): 5

--- View Group Messages ---
Your groups:
1. Development Team

Select group (number): 1

--- Messages in Development Team ---
[2024-01-15 11:00:00] alice: Welcome everyone to the Development Team group!
[2024-01-15 11:05:30] bob: Thanks Alice! Excited to be here.
[2024-01-15 11:10:45] charlie: Great to meet everyone!
```

### Example 9: Sending Files

First, create a test file:

```bash
echo "This is a secret document" > secret.txt
```

Then send it via the application:

```
Choose an option (1-9): 6

--- Send File ---
File path: secret.txt
Recipient username (or press Enter for group): bob

File sent to bob successfully!
```

### Example 10: Sending Files to Groups

```
Choose an option (1-9): 6

--- Send File ---
File path: project_plan.pdf
Recipient username (or press Enter for group): 

Your groups:
1. Development Team

Select group (number): 1

File sent to Development Team successfully!
```

### Example 11: Viewing Online Users

```
Choose an option (1-9): 7

--- Online Users ---
- bob (ID: 2)
- charlie (ID: 3)
```

## Security Features

### Example 12: Password Requirements

The application enforces strong password requirements:

```
--- Registration ---
Username: newuser
Email: newuser@example.com
Password: weak

Registration failed: Password must be at least 8 characters with uppercase, lowercase, digit, and special character.
```

Valid password examples:
- `SecurePass123!`
- `MyStrong@Password456`
- `Complex#Pass789Word`

### Example 13: Account Locking

After 5 failed login attempts, the account is automatically locked:

```
--- Login ---
Username or Email: alice
Password: wrongpassword

Login failed: Invalid credentials.

[Repeat 4 more times...]

--- Login ---
Username or Email: alice
Password: SecurePass123!

Login failed: Account locked due to too many failed attempts.
```

## Testing

### Example 14: Running the Test Suite

```bash
python secure_chat_app.py --test
```

Expected output:

```
============================================================
RUNNING COMPREHENSIVE TEST SUITE
============================================================

--- Testing Encryption ---
✓ PASS: Message encryption/decryption
✓ PASS: Different keys produce different ciphertexts
✓ PASS: Different users get different keys
✓ PASS: User keys persist across calls
✓ PASS: Group key generation

--- Testing User Registration ---
✓ PASS: User registration
✓ PASS: Username stored correctly
✓ PASS: Email stored correctly
✓ PASS: User ID assigned
✓ PASS: Duplicate username rejected
✓ PASS: Duplicate email rejected
✓ PASS: Invalid username rejected
✓ PASS: Invalid email rejected
✓ PASS: Weak password rejected

--- Testing User Login ---
✓ PASS: Login returns access token
✓ PASS: Login returns refresh token
✓ PASS: Login returns user data
✓ PASS: Correct user returned
✓ PASS: Login with email works
✓ PASS: Invalid credentials rejected
✓ PASS: Non-existent user rejected
✓ PASS: Rate limiting works

... [more tests]

============================================================
TEST RESULTS: 50+ passed, 0 failed
============================================================
```

## Troubleshooting

### Example 15: Module Import Errors

**Problem**:
```
ModuleNotFoundError: No module named 'cryptography'
```

**Solution**:
```bash
pip install cryptography
```

### Example 16: Permission Errors

**Problem**:
```
PermissionError: [Errno 13] Permission denied: 'secure_chat_data/keys/master.key'
```

**Solution**:
```bash
chmod 700 secure_chat_data/keys/
```

### Example 17: Database Corruption

**Problem**: Application crashes or behaves unexpectedly

**Solution**: Reset the database
```bash
rm -rf secure_chat_data/
```

**Warning**: This will delete all users, messages, and files!

## API Usage Examples

### Example 18: Programmatic Usage

```python
from secure_chat_app import (
    DatabaseManager, EncryptionManager, 
    AuthenticationManager, ChatService
)

# Initialize components
db = DatabaseManager()
encryption = EncryptionManager()
auth = AuthenticationManager(db, encryption)
chat = ChatService(db, encryption)

# Register a user
user = auth.register_user("alice", "alice@example.com", "SecurePass123!")

# Login
result = auth.login("alice", "SecurePass123!")
token = result['access_token']
user_id = result['user']['id']

# Send a message
message = chat.send_message(user_id, "Hello!", recipient_id=2)

# Get messages
messages = chat.get_messages(user_id, other_user_id=2)
```

## Conclusion

These examples cover the main features and use cases of the Secure Chat Application. For more information, refer to the main README.md file.

Remember:
- All messages are end-to-end encrypted
- All files are encrypted before storage
- User passwords are securely hashed
- The application follows OWASP security guidelines

Happy secure chatting! 🔒