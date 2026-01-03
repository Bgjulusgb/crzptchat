"""
Secure Chat CLI - Enhanced Version with Advanced Features
Terminal-based secure chat application with improved UX and logic
"""

import os
import sys
import json
from typing import Optional, List, Dict
from datetime import datetime
import time
from dataclasses import dataclass
from enum import Enum
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from secure_chat_enhanced import (
    DatabaseManager,
    AuthenticationManager,
    EncryptionManager,
    InputValidator,
    Config,
    User,
    Message,
    Group
)

# ==================== CONFIGURATION ====================

class CLIConfig:
    """CLI Configuration"""
    COLORS_ENABLED = True
    MAX_DISPLAY_LENGTH = 80
    MESSAGE_BATCH_SIZE = 20

# ==================== ENUMS ====================

class MenuOption(Enum):
    """Main menu options"""
    REGISTER = 1
    LOGIN = 2
    SEND_MESSAGE = 3
    VIEW_MESSAGES = 4
    CREATE_GROUP = 5
    MANAGE_GROUP = 6
    SEND_FILE = 7
    PROFILE = 8
    LOGOUT = 9
    EXIT = 0

# ==================== LOGGING ====================

def setup_cli_logging():
    """Setup logging for CLI"""
    log_dir = os.path.join(Config.DATA_DIR, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(log_dir, 'cli.log'))
        ]
    )
    
    return logging.getLogger(__name__)

logger = setup_cli_logging()

# ==================== COLOR UTILITIES ====================

class Colors:
    """ANSI color codes"""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Foreground
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Background
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'

def colored(text: str, color: str, bold: bool = False) -> str:
    """Apply color to text"""
    if not CLIConfig.COLORS_ENABLED:
        return text
    
    prefix = Colors.BOLD if bold else ''
    return f"{prefix}{color}{text}{Colors.RESET}"

def print_header(text: str):
    """Print formatted header"""
    print(f"\n{colored('=' * 70, Colors.CYAN, bold=True)}")
    print(colored(f"  {text.center(66)}  ", Colors.CYAN, bold=True))
    print(f"{colored('=' * 70, Colors.CYAN, bold=True)}\n")

def print_section(text: str):
    """Print section header"""
    print(f"\n{colored(f'▶ {text}', Colors.BLUE, bold=True)}\n")

def print_success(text: str):
    """Print success message"""
    print(colored(f"✓ {text}", Colors.GREEN, bold=True))

def print_error(text: str):
    """Print error message"""
    print(colored(f"✗ {text}", Colors.RED, bold=True))

def print_warning(text: str):
    """Print warning message"""
    print(colored(f"⚠ {text}", Colors.YELLOW, bold=True))

def print_info(text: str):
    """Print info message"""
    print(colored(f"ℹ {text}", Colors.BLUE))

# ==================== CHAT APPLICATION ====================

class SecureChatCLI:
    """Enhanced CLI Chat Application"""
    
    def __init__(self):
        """Initialize the chat application"""
        self.db = DatabaseManager()
        self.auth = AuthenticationManager(self.db)
        self.encryption = EncryptionManager()
        
        self.current_user: Optional[User] = None
        self.session_start: Optional[datetime] = None
        
        print_header("SECURE CHAT - CLI VERSION")
        print_info("End-to-end encrypted messaging platform")
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        return self.current_user is not None
    
    def require_auth(self, operation: str = "Operation") -> bool:
        """Require authentication for operation"""
        if not self.is_authenticated():
            print_error(f"{operation} requires authentication")
            return False
        return True
    
    # ==================== AUTHENTICATION ====================
    
    def register_user(self):
        """Register a new user"""
        print_section("Register New Account")
        
        try:
            while True:
                username = input(colored("Username (3-50 chars): ", Colors.CYAN)).strip()
                if InputValidator.validate_username(username):
                    break
                print_error("Invalid username format")
            
            while True:
                email = input(colored("Email: ", Colors.CYAN)).strip()
                if InputValidator.validate_email(email):
                    break
                print_error("Invalid email format")
            
            while True:
                password = input(colored("Password: ", Colors.CYAN))
                is_valid, errors = InputValidator.validate_password(password)
                if is_valid:
                    break
                print_error("Password requirements:")
                for error in errors:
                    print(f"  - {error}")
            
            display_name = input(colored("Display Name (optional): ", Colors.CYAN)).strip() or username
            
            # Check if user exists
            if self.db.get_user_by_username(username):
                print_error("Username already exists")
                return
            
            if self.db.get_user_by_email(email):
                print_error("Email already registered")
                return
            
            # Create user
            password_hash = self.auth.hash_password(password)
            user = self.db.create_user(username, email, password_hash)
            
            if user:
                print_success(f"Account created successfully!")
                print_info(f"User ID: {user.id}")
                print_info(f"Display Name: {display_name}")
                logger.info(f"New user registered: {username}")
            else:
                print_error("Failed to create account")
        
        except Exception as e:
            print_error(f"Registration failed: {e}")
            logger.error(f"Registration error: {e}")
    
    def login_user(self):
        """Login user"""
        print_section("Login")
        
        try:
            username_or_email = input(colored("Username or Email: ", Colors.CYAN)).strip()
            password = input(colored("Password: ", Colors.CYAN))
            
            # Find user
            user = self.db.get_user_by_username(username_or_email)
            if not user:
                user = self.db.get_user_by_email(username_or_email)
            
            if not user:
                print_error("User not found")
                return
            
            # Verify password
            if not self.auth.verify_password(password, user.password_hash):
                print_error("Incorrect password")
                return
            
            # Update last login
            user.last_login = datetime.utcnow().isoformat()
            self.db.update_user(user)
            
            self.current_user = user
            self.session_start = datetime.utcnow()
            
            print_success(f"Welcome back, {user.username}!")
            print_info(f"Last login: {user.last_login}")
            logger.info(f"User logged in: {username_or_email}")
        
        except Exception as e:
            print_error(f"Login failed: {e}")
            logger.error(f"Login error: {e}")
    
    def logout_user(self):
        """Logout user"""
        if not self.require_auth("Logout"):
            return
        
        username = self.current_user.username if self.current_user else "User"
        self.current_user = None
        self.session_start = None
        
        print_success(f"Logged out successfully, {username}!")
        logger.info(f"User logged out: {username}")
    
    # ==================== MESSAGING ====================
    
    def send_message(self):
        """Send a message to another user"""
        if not self.require_auth("Messaging"):
            return
        
        print_section("Send Message")
        
        try:
            if not self.current_user or not self.current_user.id:
                print_error("Not logged in properly")
                return
            
            # Get recipient
            recipient_name = input(colored("Recipient username: ", Colors.CYAN)).strip()
            recipient = self.db.get_user_by_username(recipient_name)
            
            if not recipient:
                print_error(f"User '{recipient_name}' not found")
                return
            
            if recipient.id == self.current_user.id:
                print_error("Cannot send message to yourself")
                return
            
            # Get message content
            print_info("Enter message content (max 10000 chars):")
            content = input(colored("> ", Colors.CYAN)).strip()
            
            if not content:
                print_error("Message cannot be empty")
                return
            
            # Sanitize and validate
            content = InputValidator.sanitize_message(content)
            
            # Encrypt message
            encrypted_content, nonce = self.encryption.encrypt(content)
            
            # Save message
            message = self.db.create_message(
                sender_id=self.current_user.id,
                recipient_id=recipient.id,
                content=encrypted_content,
                content_nonce=nonce
            )
            
            if message:
                print_success(f"Message sent to {recipient.username}")
                print_info(f"Message ID: {message.id}")
                logger.info(f"Message sent from {self.current_user.username} to {recipient.username}")
            else:
                print_error("Failed to send message")
        
        except Exception as e:
            print_error(f"Message error: {e}")
            logger.error(f"Send message error: {e}")
    
    def view_messages(self):
        """View messages with another user"""
        if not self.require_auth("Viewing messages"):
            return
        
        print_section("View Messages")
        
        if not self.current_user or not self.current_user.id:
            print_error("Not logged in properly")
            return
        
        try:
            # Get conversation partner
            other_user_name = input(colored("View messages with: ", Colors.CYAN)).strip()
            other_user = self.db.get_user_by_username(other_user_name)
            
            if not other_user:
                print_error(f"User '{other_user_name}' not found")
                return
            
            # Get messages
            messages = self.db.get_messages_between_users(
                self.current_user.id,
                other_user.id,
                limit=CLIConfig.MESSAGE_BATCH_SIZE
            )
            
            if not messages:
                print_warning("No messages yet")
                return
            
            # Display messages
            print_section(f"Conversation with {other_user.username}")
            
            for msg in messages:
                try:
                    if msg.is_encrypted:
                        decrypted = self.encryption.decrypt(msg.content, msg.content_nonce)
                    else:
                        decrypted = msg.content
                    
                    sender = "You" if msg.sender_id == self.current_user.id else other_user.username
                    timestamp = msg.created_at
                    
                    # Format message
                    sender_color = Colors.GREEN if msg.sender_id == self.current_user.id else Colors.BLUE
                    print(f"{colored(sender, sender_color, bold=True)} [{timestamp}]:")
                    print(f"  {decrypted}\n")
                
                except Exception as e:
                    print_error(f"Failed to decrypt message: {e}")
                    continue
        
        except Exception as e:
            print_error(f"View messages error: {e}")
            logger.error(f"View messages error: {e}")
    
    # ==================== GROUPS ====================
    
    def create_group(self):
        """Create a new group"""
        if not self.require_auth("Creating groups"):
            return
        
        print_section("Create Group")
        
        if not self.current_user or not self.current_user.id:
            print_error("Not logged in properly")
            return
        
        try:
            name = input(colored("Group name: ", Colors.CYAN)).strip()
            if len(name) < 3:
                print_error("Group name must be at least 3 characters")
                return
            
            description = input(colored("Description (optional): ", Colors.CYAN)).strip()
            
            # Create group
            group = self.db.create_group(name, self.current_user.id, description)
            
            if group:
                print_success(f"Group '{name}' created successfully!")
                print_info(f"Group ID: {group.id}")
                logger.info(f"Group created by {self.current_user.username}: {name}")
            else:
                print_error("Failed to create group")
        
        except Exception as e:
            print_error(f"Group creation error: {e}")
            logger.error(f"Create group error: {e}")
    
    def view_groups(self):
        """View user's groups"""
        if not self.require_auth("Viewing groups"):
            return
        
        print_section("Your Groups")
        
        if not self.current_user or not self.current_user.id:
            print_error("Not logged in properly")
            return
        
        try:
            groups = self.db.get_groups_for_user(self.current_user.id)
            
            if not groups:
                print_warning("You are not a member of any groups")
                return
            
            for group in groups:
                print(colored(f"▸ {group.name}", Colors.BLUE, bold=True))
                if group.description:
                    print(f"  Description: {group.description}")
                print(f"  ID: {group.id}")
                print(f"  Created: {group.created_at}\n")
        
        except Exception as e:
            print_error(f"View groups error: {e}")
            logger.error(f"View groups error: {e}")
    
    # ==================== PROFILE ====================
    
    def view_profile(self):
        """View/Edit user profile"""
        if not self.require_auth("Profile"):
            return
        
        print_section("User Profile")
        
        if not self.current_user:
            print_error("Not logged in properly")
            return
        
        try:
            user = self.current_user
            
            print(colored("Profile Information:", Colors.BLUE, bold=True))
            if user:
                print(f"  Username: {user.username if user else 'Unknown'}")
                print(f"  Email: {user.email if user else 'Unknown'}")
                print(f"  Display Name: {user.display_name or 'Not set' if user else 'Unknown'}")
                print(f"  Status: {user.status if user else 'Unknown'}")
                print(f"  Created: {user.created_at if user else 'Unknown'}")
                if user and user.last_login:
                    print(f"  Last Login: {user.last_login}")
            
            if self.session_start:
                session_duration = datetime.utcnow() - self.session_start
                print(f"  Session Duration: {session_duration}")
        
        except Exception as e:
            print_error(f"Profile error: {e}")
            logger.error(f"Profile error: {e}")
    
    # ==================== MAIN MENU ====================
    
    def show_main_menu(self):
        """Display main menu"""
        print_header("MAIN MENU")
        
        if self.is_authenticated():
            if self.current_user and self.current_user.username:
                print_info(f"Logged in as: {colored(self.current_user.username, Colors.GREEN, bold=True)}")
            else:
                print_error("Failed to load user information")
        
        print(colored(f"{'1':<2} - Register", Colors.CYAN))
        print(colored(f"{'2':<2} - Login", Colors.CYAN))
        print(colored(f"{'3':<2} - Send Message", Colors.CYAN))
        print(colored(f"{'4':<2} - View Messages", Colors.CYAN))
        print(colored(f"{'5':<2} - Create Group", Colors.CYAN))
        print(colored(f"{'6':<2} - View Groups", Colors.CYAN))
        print(colored(f"{'7':<2} - Profile", Colors.CYAN))
        print(colored(f"{'8':<2} - Logout", Colors.CYAN))
        print(colored(f"{'0':<2} - Exit", Colors.RED))
        print()
    
    def handle_menu_choice(self, choice: str):
        """Handle menu selection"""
        try:
            option = int(choice)
            
            if option == 1:
                self.register_user()
            elif option == 2:
                self.login_user()
            elif option == 3:
                self.send_message()
            elif option == 4:
                self.view_messages()
            elif option == 5:
                self.create_group()
            elif option == 6:
                self.view_groups()
            elif option == 7:
                self.view_profile()
            elif option == 8:
                self.logout_user()
            elif option == 0:
                return False
            else:
                print_error("Invalid option")
            
            return True
        
        except ValueError:
            print_error("Invalid input")
            return True
    
    def run(self):
        """Run the CLI application"""
        try:
            while True:
                self.show_main_menu()
                choice = input(colored("Select option: ", Colors.CYAN))
                
                if not self.handle_menu_choice(choice):
                    break
                
                input(colored("\nPress Enter to continue...", Colors.DIM))
        
        except KeyboardInterrupt:
            print()
            print_info("Application terminated by user")
        except Exception as e:
            print_error(f"Application error: {e}")
            logger.error(f"Application error: {e}")
        finally:
            print_header("GOODBYE!")

# ==================== MAIN ====================

if __name__ == "__main__":
    try:
        app = SecureChatCLI()
        app.run()
    except Exception as e:
        print(f"Fatal error: {e}")
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
