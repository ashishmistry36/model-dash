"""
Authentication module for Model Dashboard.
Supports LDAP authentication with AD group validation and local database users.
"""

import os
import re
import hashlib
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Tuple, List
from pathlib import Path

logger = logging.getLogger('model_dashboard.auth')

# Configuration from environment variables
LDAP_SERVER = os.getenv('LDAP_SERVER', 'ldap://ldap.example.com:389')
LDAP_BASE_DN = os.getenv('LDAP_BASE_DN', 'dc=example,dc=com')
LDAP_USER_DN_TEMPLATE = os.getenv('LDAP_USER_DN_TEMPLATE', 'uid={username},ou=users,dc=example,dc=com')
LDAP_SEARCH_FILTER = os.getenv('LDAP_SEARCH_FILTER', '(uid={username})')
LDAP_REQUIRED_GROUP = os.getenv('LDAP_REQUIRED_GROUP', 'cn=model-dashboard-users,ou=groups,dc=example,dc=com')
LDAP_GROUP_ATTRIBUTE = os.getenv('LDAP_GROUP_ATTRIBUTE', 'memberOf')

# Local database configuration
DB_PATH = os.getenv('AUTH_DB_PATH', '/data/models/.auth/users.db')

# API token settings
API_TOKEN_EXPIRY_DAYS = int(os.getenv('API_TOKEN_EXPIRY_DAYS', '30'))


@dataclass
class User:
    """User model representing an authenticated user."""
    username: str
    display_name: str
    email: str
    auth_type: str  # 'ldap' or 'local'
    groups: List[str] = None
    avatar: str = ''
    
    def __post_init__(self):
        if self.groups is None:
            self.groups = []
        if not self.avatar:
            self.avatar = make_svg_avatar(self.display_name)
    
    def items(self):
        """Return user attributes as key-value pairs."""
        return {
            'username': self.username,
            'display_name': self.display_name,
            'email': self.email,
            'auth_type': self.auth_type,
            'groups': ', '.join(self.groups) if self.groups else 'N/A'
        }.items()


def make_svg_avatar(username: str, radius: int = 20, font_size: int = 20, 
                    font_weight: int = 300, opacity: int = 75) -> str:
    """Create an SVG avatar for a user."""
    DEFAULT_FONTS = [
        'HelveticaNeue-Light', 'Helvetica Neue Light', 'Helvetica Neue',
        'Helvetica', 'Arial', 'Lucida Grande', 'sans-serif',
    ]
    DEFAULT_COLORS = [
        "#1abc9c", "#16a085", "#f1c40f", "#f39c12", "#2ecc71", "#27ae60",
        "#e67e22", "#d35400", "#3498db", "#2980b9", "#e74c3c", "#c0392b",
        "#9b59b6", "#8e44ad", "#bdc3c7", "#34495e", "#2c3e50", "#95a5a6",
        "#7f8c8d", "#ec87bf", "#d870ad", "#f69785", "#9ba37e", "#b49255",
    ]
    
    _to_style = lambda x: '; '.join([f'{k}: {v}' for k, v in x.items()])
    
    def _get_color(x):
        idx = sum(map(ord, x)) % len(DEFAULT_COLORS)
        return DEFAULT_COLORS[idx]
    
    username = str(username)
    if ' ' in username:
        parts = username.split(' ')
        initials = f'{parts[0][0]}{parts[-1][0]}'
    elif len(username) > 2:
        initials = f'{username[0]}{username[2]}'
    else:
        initials = f'{username[0]}'
    initials = initials.upper()
    
    color = _get_color(initials)
    fill_style = _to_style({'fill': color})
    text_style = _to_style({'font-weight': f'{font_weight}', 'font-size': f'{font_size}px'})
    width = int(radius * 2)
    height = width
    font_family = ','.join(DEFAULT_FONTS)
    
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" pointer-events="none" width="{width+4}" height="{height+4}">'
    svg += f'<circle cx="{radius+1}" cy="{radius+1}" r="{radius}" style="{fill_style}" fill-opacity="{opacity}%" stroke="{color}" stroke-width="1px"/>'
    svg += '<text text-anchor="middle" y="50%" x="50%" dy="0.35em" '
    svg += f'pointer-events="auto" fill="#ffffff" font-family="{font_family}" '
    svg += f'style="{text_style}">{initials}</text></svg>'
    return svg


def init_database():
    """Initialize the local user database."""
    db_dir = os.path.dirname(DB_PATH)
    os.makedirs(db_dir, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            display_name TEXT NOT NULL,
            email TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create API tokens table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            token_hash TEXT UNIQUE NOT NULL,
            description TEXT,
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used_at TIMESTAMP,
            FOREIGN KEY (username) REFERENCES users (username)
        )
    ''')
    
    # Create session tokens table for web sessions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            session_token TEXT UNIQUE NOT NULL,
            auth_type TEXT NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info(f"Database initialized at {DB_PATH}")


def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def hash_token(token: str) -> str:
    """Hash an API token using SHA-256."""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def authenticate_ldap(username: str, password: str) -> Tuple[bool, Optional[User], str]:
    """
    Authenticate a user against LDAP and verify group membership.
    
    Returns:
        Tuple of (success, user, error_message)
    """
    try:
        import ldap3
        from ldap3 import Server, Connection, ALL, SUBTREE
    except ImportError:
        logger.warning("ldap3 library not installed. LDAP authentication disabled.")
        return False, None, "LDAP authentication is not available"
    
    try:
        # Connect to LDAP server
        server = Server(LDAP_SERVER, get_info=ALL)
        user_dn = LDAP_USER_DN_TEMPLATE.format(username=username)
        
        conn = Connection(server, user=user_dn, password=password, auto_bind=True)
        
        if not conn.bind():
            logger.warning(f"LDAP bind failed for user: {username}")
            return False, None, "Invalid username or password"
        
        # Search for user info and group membership
        search_filter = LDAP_SEARCH_FILTER.format(username=username)
        conn.search(
            search_base=LDAP_BASE_DN,
            search_filter=search_filter,
            search_scope=SUBTREE,
            attributes=['cn', 'mail', 'displayName', LDAP_GROUP_ATTRIBUTE]
        )
        
        if not conn.entries:
            logger.warning(f"User not found in LDAP: {username}")
            return False, None, "User not found"
        
        entry = conn.entries[0]
        
        # Get user groups
        groups = []
        if LDAP_GROUP_ATTRIBUTE in entry:
            groups = [str(g) for g in entry[LDAP_GROUP_ATTRIBUTE]]
        
        # Check if user is in required group
        if LDAP_REQUIRED_GROUP and LDAP_REQUIRED_GROUP not in groups:
            logger.warning(f"User {username} is not in required group: {LDAP_REQUIRED_GROUP}")
            return False, None, "You are not authorized to access this application"
        
        # Extract user info
        display_name = str(entry.displayName) if hasattr(entry, 'displayName') else username
        email = str(entry.mail) if hasattr(entry, 'mail') else ''
        
        user = User(
            username=username,
            display_name=display_name,
            email=email,
            auth_type='ldap',
            groups=groups
        )
        
        conn.unbind()
        logger.info(f"LDAP authentication successful for user: {username}")
        return True, user, ""
        
    except Exception as e:
        logger.error(f"LDAP authentication error: {e}")
        return False, None, f"Authentication error: {str(e)}"


def authenticate_local(username: str, password: str) -> Tuple[bool, Optional[User], str]:
    """
    Authenticate a user against the local database.
    
    Returns:
        Tuple of (success, user, error_message)
    """
    try:
        init_database()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        password_hash = hash_password(password)
        
        cursor.execute('''
            SELECT username, display_name, email, is_active 
            FROM users 
            WHERE username = ? AND password_hash = ?
        ''', (username, password_hash))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            logger.warning(f"Local authentication failed for user: {username}")
            return False, None, "Invalid username or password"
        
        if not result[3]:  # is_active
            logger.warning(f"Inactive user attempted login: {username}")
            return False, None, "User account is disabled"
        
        user = User(
            username=result[0],
            display_name=result[1],
            email=result[2] or '',
            auth_type='local',
            groups=['local-users']
        )
        
        logger.info(f"Local authentication successful for user: {username}")
        return True, user, ""
        
    except Exception as e:
        logger.error(f"Local authentication error: {e}")
        return False, None, f"Authentication error: {str(e)}"


def authenticate(username: str, password: str, auth_type: str = 'ldap') -> Tuple[bool, Optional[User], str]:
    """
    Authenticate a user using the specified authentication type.
    
    Args:
        username: The username
        password: The password
        auth_type: Either 'ldap' or 'local'
    
    Returns:
        Tuple of (success, user, error_message)
    """
    if auth_type == 'ldap':
        return authenticate_ldap(username, password)
    elif auth_type == 'local':
        return authenticate_local(username, password)
    else:
        return False, None, f"Unknown authentication type: {auth_type}"


def create_local_user(username: str, password: str, display_name: str, email: str = '') -> Tuple[bool, str]:
    """
    Create a new local user.
    
    Returns:
        Tuple of (success, message)
    """
    try:
        init_database()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        password_hash = hash_password(password)
        
        cursor.execute('''
            INSERT INTO users (username, password_hash, display_name, email)
            VALUES (?, ?, ?, ?)
        ''', (username, password_hash, display_name, email))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Created local user: {username}")
        return True, "User created successfully"
        
    except sqlite3.IntegrityError:
        logger.warning(f"Attempted to create duplicate user: {username}")
        return False, "Username already exists"
    except Exception as e:
        logger.error(f"Error creating local user: {e}")
        return False, f"Error creating user: {str(e)}"


def validate_api_token(token: str) -> Tuple[bool, Optional[User], str]:
    """
    Validate an API token and return the associated user.
    
    Returns:
        Tuple of (success, user, error_message)
    """
    try:
        init_database()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        token_hash = hash_token(token)
        
        cursor.execute('''
            SELECT t.username, u.display_name, u.email, t.expires_at
            FROM api_tokens t
            JOIN users u ON t.username = u.username
            WHERE t.token_hash = ? AND u.is_active = 1
        ''', (token_hash,))
        
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return False, None, "Invalid API token"
        
        # Check expiration
        if result[3]:
            expires_at = datetime.fromisoformat(result[3])
            if datetime.utcnow() > expires_at:
                conn.close()
                return False, None, "API token has expired"
        
        # Update last used timestamp
        cursor.execute('''
            UPDATE api_tokens SET last_used_at = ? WHERE token_hash = ?
        ''', (datetime.utcnow().isoformat(), token_hash))
        conn.commit()
        conn.close()
        
        user = User(
            username=result[0],
            display_name=result[1],
            email=result[2] or '',
            auth_type='api_token',
            groups=['api-users']
        )
        
        return True, user, ""
        
    except Exception as e:
        logger.error(f"API token validation error: {e}")
        return False, None, f"Token validation error: {str(e)}"


def create_api_token(username: str, description: str = '') -> Tuple[bool, str, str]:
    """
    Create a new API token for a user.
    
    Returns:
        Tuple of (success, token, message)
    """
    import secrets
    
    try:
        init_database()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Verify user exists
        cursor.execute('SELECT username FROM users WHERE username = ? AND is_active = 1', (username,))
        if not cursor.fetchone():
            conn.close()
            return False, '', "User not found or inactive"
        
        # Generate token
        token = secrets.token_urlsafe(32)
        token_hash = hash_token(token)
        expires_at = (datetime.utcnow() + timedelta(days=API_TOKEN_EXPIRY_DAYS)).isoformat()
        
        cursor.execute('''
            INSERT INTO api_tokens (username, token_hash, description, expires_at)
            VALUES (?, ?, ?, ?)
        ''', (username, token_hash, description, expires_at))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Created API token for user: {username}")
        return True, token, "API token created successfully"
        
    except Exception as e:
        logger.error(f"Error creating API token: {e}")
        return False, '', f"Error creating token: {str(e)}"


def revoke_api_token(token: str) -> Tuple[bool, str]:
    """
    Revoke an API token.
    
    Returns:
        Tuple of (success, message)
    """
    try:
        init_database()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        token_hash = hash_token(token)
        
        cursor.execute('DELETE FROM api_tokens WHERE token_hash = ?', (token_hash,))
        
        if cursor.rowcount == 0:
            conn.close()
            return False, "Token not found"
        
        conn.commit()
        conn.close()
        
        logger.info("API token revoked")
        return True, "Token revoked successfully"
        
    except Exception as e:
        logger.error(f"Error revoking API token: {e}")
        return False, f"Error revoking token: {str(e)}"


def list_user_tokens(username: str) -> List[dict]:
    """List all API tokens for a user (without exposing the actual tokens)."""
    try:
        init_database()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, description, expires_at, created_at, last_used_at
            FROM api_tokens
            WHERE username = ?
            ORDER BY created_at DESC
        ''', (username,))
        
        tokens = []
        for row in cursor.fetchall():
            tokens.append({
                'id': row[0],
                'description': row[1] or 'No description',
                'expires_at': row[2],
                'created_at': row[3],
                'last_used_at': row[4]
            })
        
        conn.close()
        return tokens
        
    except Exception as e:
        logger.error(f"Error listing tokens: {e}")
        return []


# Initialize database on module load
init_database()
