#!/usr/bin/env python3
"""
Local user management script for Model Dashboard.

This script allows administrators to create, list, and manage local users
for the Model Dashboard application.

Usage:
    python manage_users.py create <username> <password> <display_name> [--email EMAIL]
    python manage_users.py list
    python manage_users.py disable <username>
    python manage_users.py enable <username>
    python manage_users.py reset-password <username> <new_password>
    python manage_users.py delete <username>

Environment variables:
    AUTH_DB_PATH: Path to the SQLite database (default: /data/models/.auth/users.db)
"""

import os
import sys
import argparse
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path

# Default database path
DB_PATH = os.getenv('AUTH_DB_PATH', '/data/models/.auth/users.db')


def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def init_database():
    """Initialize the database if it doesn't exist."""
    db_dir = os.path.dirname(DB_PATH)
    os.makedirs(db_dir, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
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
    
    conn.commit()
    conn.close()


def create_user(username: str, password: str, display_name: str, email: str = '') -> bool:
    """Create a new local user."""
    init_database()
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        password_hash = hash_password(password)
        
        cursor.execute('''
            INSERT INTO users (username, password_hash, display_name, email)
            VALUES (?, ?, ?, ?)
        ''', (username, password_hash, display_name, email))
        
        conn.commit()
        conn.close()
        
        print(f"✓ Created user: {username}")
        return True
        
    except sqlite3.IntegrityError:
        print(f"✗ Error: User '{username}' already exists")
        return False
    except Exception as e:
        print(f"✗ Error creating user: {e}")
        return False


def list_users() -> None:
    """List all local users."""
    init_database()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT username, display_name, email, is_active, created_at
        FROM users
        ORDER BY username
    ''')
    
    users = cursor.fetchall()
    conn.close()
    
    if not users:
        print("No users found.")
        return
    
    print("\n" + "-" * 80)
    print(f"{'Username':<20} {'Display Name':<25} {'Email':<20} {'Active':<8} {'Created':<12}")
    print("-" * 80)
    
    for user in users:
        username, display_name, email, is_active, created = user
        status = "Yes" if is_active else "No"
        created_date = created[:10] if created else "N/A"
        email = email or "N/A"
        
        print(f"{username:<20} {display_name:<25} {email:<20} {status:<8} {created_date:<12}")
    
    print("-" * 80)
    print(f"Total: {len(users)} user(s)")


def set_user_status(username: str, active: bool) -> bool:
    """Enable or disable a user."""
    init_database()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE users 
        SET is_active = ?, updated_at = ?
        WHERE username = ?
    ''', (active, datetime.utcnow().isoformat(), username))
    
    if cursor.rowcount == 0:
        print(f"✗ Error: User '{username}' not found")
        conn.close()
        return False
    
    conn.commit()
    conn.close()
    
    status = "enabled" if active else "disabled"
    print(f"✓ User '{username}' has been {status}")
    return True


def reset_password(username: str, new_password: str) -> bool:
    """Reset a user's password."""
    init_database()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    password_hash = hash_password(new_password)
    
    cursor.execute('''
        UPDATE users 
        SET password_hash = ?, updated_at = ?
        WHERE username = ?
    ''', (password_hash, datetime.utcnow().isoformat(), username))
    
    if cursor.rowcount == 0:
        print(f"✗ Error: User '{username}' not found")
        conn.close()
        return False
    
    conn.commit()
    conn.close()
    
    print(f"✓ Password reset for user '{username}'")
    return True


def delete_user(username: str) -> bool:
    """Delete a user and their API tokens."""
    init_database()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Delete API tokens first
    cursor.execute('DELETE FROM api_tokens WHERE username = ?', (username,))
    tokens_deleted = cursor.rowcount
    
    # Delete user
    cursor.execute('DELETE FROM users WHERE username = ?', (username,))
    
    if cursor.rowcount == 0:
        print(f"✗ Error: User '{username}' not found")
        conn.close()
        return False
    
    conn.commit()
    conn.close()
    
    print(f"✓ Deleted user '{username}' and {tokens_deleted} API token(s)")
    return True


def main():
    """Main entry point."""
    global DB_PATH  # Must be declared before first use
    
    parser = argparse.ArgumentParser(
        description='Model Dashboard - Local User Management',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s create admin mysecretpass "Admin User" --email admin@example.com
  %(prog)s list
  %(prog)s disable olduser
  %(prog)s enable olduser
  %(prog)s reset-password admin newpassword123
  %(prog)s delete olduser
        """
    )
    
    parser.add_argument('--db', help='Path to database file', default=DB_PATH)
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Create user command
    create_parser = subparsers.add_parser('create', help='Create a new user')
    create_parser.add_argument('username', help='Username')
    create_parser.add_argument('password', help='Password')
    create_parser.add_argument('display_name', help='Display name')
    create_parser.add_argument('--email', help='Email address', default='')
    
    # List users command
    subparsers.add_parser('list', help='List all users')
    
    # Disable user command
    disable_parser = subparsers.add_parser('disable', help='Disable a user')
    disable_parser.add_argument('username', help='Username to disable')
    
    # Enable user command
    enable_parser = subparsers.add_parser('enable', help='Enable a user')
    enable_parser.add_argument('username', help='Username to enable')
    
    # Reset password command
    reset_parser = subparsers.add_parser('reset-password', help='Reset user password')
    reset_parser.add_argument('username', help='Username')
    reset_parser.add_argument('new_password', help='New password')
    
    # Delete user command
    delete_parser = subparsers.add_parser('delete', help='Delete a user')
    delete_parser.add_argument('username', help='Username to delete')
    
    args = parser.parse_args()
    
    # Update database path if specified
    DB_PATH = args.db
    
    if not args.command:
        parser.print_help()
        return 1
    
    if args.command == 'create':
        return 0 if create_user(args.username, args.password, args.display_name, args.email) else 1
    
    elif args.command == 'list':
        list_users()
        return 0
    
    elif args.command == 'disable':
        return 0 if set_user_status(args.username, False) else 1
    
    elif args.command == 'enable':
        return 0 if set_user_status(args.username, True) else 1
    
    elif args.command == 'reset-password':
        return 0 if reset_password(args.username, args.new_password) else 1
    
    elif args.command == 'delete':
        return 0 if delete_user(args.username) else 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
