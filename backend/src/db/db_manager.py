"""
DatabaseManager for user authentication and conversation management.
Uses SQLite for simplicity.
"""

import sqlite3
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path


class DatabaseManager:
    """Manages user authentication, conversations, and messages using SQLite"""

    def __init__(self, db_path: str = "./data/ohada_users.db"):
        """Initialize database manager

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path

        # Create data directory if it doesn't exist
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_db()

    def _init_db(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        """)

        # Revoked tokens table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS revoked_tokens (
                token_id TEXT PRIMARY KEY,
                token TEXT NOT NULL,
                revoked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        # Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                message_id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                content TEXT NOT NULL,
                is_user INTEGER NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        conn.commit()
        conn.close()

    # User management
    def create_user(self, email: str, password_hash: str) -> str:
        """Create a new user"""
        user_id = str(uuid.uuid4())
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO users (user_id, email, password_hash) VALUES (?, ?, ?)",
                (user_id, email, password_hash)
            )
            conn.commit()
            return user_id
        finally:
            conn.close()

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def update_last_login(self, user_id: str):
        """Update user's last login timestamp"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE user_id = ?",
                (user_id,)
            )
            conn.commit()
        finally:
            conn.close()

    # Token management
    def revoke_token(self, token: str) -> str:
        """Revoke a JWT token"""
        token_id = str(uuid.uuid4())
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO revoked_tokens (token_id, token) VALUES (?, ?)",
                (token_id, token)
            )
            conn.commit()
            return token_id
        finally:
            conn.close()

    def is_token_revoked(self, token: str) -> bool:
        """Check if a token has been revoked"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT COUNT(*) FROM revoked_tokens WHERE token = ?", (token,))
            count = cursor.fetchone()[0]
            return count > 0
        finally:
            conn.close()

    # Conversation management
    def create_conversation(self, user_id: str, title: Optional[str] = None) -> str:
        """Create a new conversation"""
        conversation_id = str(uuid.uuid4())
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO conversations (conversation_id, user_id, title) VALUES (?, ?, ?)",
                (conversation_id, user_id, title)
            )
            conn.commit()
            return conversation_id
        finally:
            conn.close()

    def get_conversations(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get user's conversations"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT * FROM conversations WHERE user_id = ? ORDER BY updated_at DESC LIMIT ?",
                (user_id, limit)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific conversation"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM conversations WHERE conversation_id = ?", (conversation_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def update_conversation(self, conversation_id: str, title: Optional[str] = None):
        """Update conversation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            if title:
                cursor.execute(
                    "UPDATE conversations SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE conversation_id = ?",
                    (title, conversation_id)
                )
            else:
                cursor.execute(
                    "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE conversation_id = ?",
                    (conversation_id,)
                )
            conn.commit()
        finally:
            conn.close()

    def delete_conversation(self, conversation_id: str):
        """Delete a conversation and its messages"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
            cursor.execute("DELETE FROM conversations WHERE conversation_id = ?", (conversation_id,))
            conn.commit()
        finally:
            conn.close()

    # Message management
    def add_message(
        self,
        conversation_id: str,
        user_id: str,
        content: str,
        is_user: bool,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add a message to a conversation"""
        message_id = str(uuid.uuid4())
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO messages (message_id, conversation_id, user_id, content, is_user, metadata) VALUES (?, ?, ?, ?, ?, ?)",
                (message_id, conversation_id, user_id, content, 1 if is_user else 0, json.dumps(metadata) if metadata else None)
            )
            conn.commit()
            return message_id
        finally:
            conn.close()

    def get_messages(self, conversation_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get messages for a conversation"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC LIMIT ?",
                (conversation_id, limit)
            )
            rows = cursor.fetchall()
            messages = []
            for row in rows:
                message = dict(row)
                if message['metadata']:
                    message['metadata'] = json.loads(message['metadata'])
                message['is_user'] = bool(message['is_user'])
                messages.append(message)
            return messages
        finally:
            conn.close()

    # Statistics
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT COUNT(*) FROM users")
            users_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM conversations")
            conversations_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM messages")
            messages_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM revoked_tokens")
            revoked_tokens_count = cursor.fetchone()[0]

            return {
                "users": users_count,
                "conversations": conversations_count,
                "messages": messages_count,
                "revoked_tokens": revoked_tokens_count
            }
        finally:
            conn.close()

    def cleanup_database(self) -> Dict[str, int]:
        """Cleanup old revoked tokens"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Delete revoked tokens older than 7 days
            cursor.execute(
                "DELETE FROM revoked_tokens WHERE revoked_at < datetime('now', '-7 days')"
            )
            deleted_count = cursor.rowcount
            conn.commit()

            return {"deleted_revoked_tokens": deleted_count}
        finally:
            conn.close()
