"""
Module de gestion de la base de données SQLite pour le stockage des utilisateurs et conversations.
"""
import os
import json
import sqlite3
import logging
import uuid
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union
from pathlib import Path

# Configuration du logging
logger = logging.getLogger("ohada_db_manager")

class DatabaseManager:
    """Gestionnaire de la base de données SQLite pour les utilisateurs et conversations"""
    
    def __init__(self, db_path: str = "./data/ohada_users.db"):
        """
        Initialise le gestionnaire de base de données
        
        Args:
            db_path: Chemin vers le fichier de base de données SQLite
        """
        self.db_path = db_path
        
        # Créer le répertoire parent si nécessaire
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialiser la base de données
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialise le schéma de la base de données si nécessaire"""
        # Lire le schéma SQL depuis un fichier ou l'inclure directement
        schema_sql = """
        -- Utilisateurs
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            name TEXT,
            profile_picture TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            auth_provider TEXT DEFAULT 'google'
        );

        -- Conversations
        CREATE TABLE IF NOT EXISTS conversations (
            conversation_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        );

        -- Messages dans les conversations
        CREATE TABLE IF NOT EXISTS messages (
            message_id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            is_user BOOLEAN NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT,
            FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        -- Feedback sur les réponses
        CREATE TABLE IF NOT EXISTS feedback (
            feedback_id TEXT PRIMARY KEY,
            message_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            rating INTEGER,
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (message_id) REFERENCES messages(message_id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        -- Index pour améliorer les performances
        CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
        CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
        CREATE INDEX IF NOT EXISTS idx_feedback_message ON feedback(message_id);
        """
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.executescript(schema_sql)
                conn.commit()
            logger.info(f"Base de données initialisée avec succès: {self.db_path}")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de la base de données: {e}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Obtient une connexion à la base de données"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Pour pouvoir accéder aux colonnes par leur nom
        return conn
    
    # Méthodes pour les utilisateurs
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère un utilisateur par son ID
        
        Args:
            user_id: Identifiant de l'utilisateur
            
        Returns:
            Informations sur l'utilisateur ou None si non trouvé
        """
        query = "SELECT * FROM users WHERE user_id = ?"
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(query, (user_id,))
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'utilisateur {user_id}: {e}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Récupère un utilisateur par son email
        
        Args:
            email: Adresse email de l'utilisateur
            
        Returns:
            Informations sur l'utilisateur ou None si non trouvé
        """
        query = "SELECT * FROM users WHERE email = ?"
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(query, (email,))
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'utilisateur avec l'email {email}: {e}")
            return None
    
    def create_user(self, user_info: Dict[str, Any]) -> Optional[str]:
        """
        Crée un nouvel utilisateur
        
        Args:
            user_info: Informations sur l'utilisateur (doit contenir email)
            
        Returns:
            ID de l'utilisateur créé ou None en cas d'erreur
        """
        # Vérifier que l'email est présent
        if 'email' not in user_info:
            logger.error("L'email est requis pour créer un utilisateur")
            return None
        
        # Générer un ID utilisateur si non fourni
        user_id = user_info.get('user_id', str(uuid.uuid4()))
        
        query = """
        INSERT INTO users (user_id, email, name, profile_picture, last_login, auth_provider)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        try:
            with self._get_connection() as conn:
                now = datetime.now().isoformat()
                conn.execute(query, (
                    user_id,
                    user_info['email'],
                    user_info.get('name', ''),
                    user_info.get('profile_picture', ''),
                    now,
                    user_info.get('auth_provider', 'google')
                ))
                conn.commit()
            return user_id
        except sqlite3.IntegrityError:
            # L'utilisateur existe déjà, mettre à jour last_login
            existing_user = self.get_user_by_email(user_info['email'])
            if existing_user:
                self.update_user_login(existing_user['user_id'])
                return existing_user['user_id']
            return None
        except Exception as e:
            logger.error(f"Erreur lors de la création de l'utilisateur: {e}")
            return None
    
    def update_user_login(self, user_id: str) -> bool:
        """
        Met à jour la date de dernière connexion d'un utilisateur
        
        Args:
            user_id: Identifiant de l'utilisateur
            
        Returns:
            True si la mise à jour a réussi, False sinon
        """
        query = "UPDATE users SET last_login = ? WHERE user_id = ?"
        try:
            with self._get_connection() as conn:
                now = datetime.now().isoformat()
                conn.execute(query, (now, user_id))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de la connexion de l'utilisateur {user_id}: {e}")
            return False
    
    # Méthodes pour les conversations
    
    def create_conversation(self, user_id: str, title: str) -> Optional[str]:
        """
        Crée une nouvelle conversation
        
        Args:
            user_id: Identifiant de l'utilisateur
            title: Titre de la conversation
            
        Returns:
            ID de la conversation créée ou None en cas d'erreur
        """
        # Générer un ID pour la conversation
        conversation_id = str(uuid.uuid4())
        
        query = """
        INSERT INTO conversations (conversation_id, user_id, title)
        VALUES (?, ?, ?)
        """
        try:
            with self._get_connection() as conn:
                conn.execute(query, (conversation_id, user_id, title))
                conn.commit()
            return conversation_id
        except Exception as e:
            logger.error(f"Erreur lors de la création de la conversation: {e}")
            return None
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère une conversation par son ID
        
        Args:
            conversation_id: Identifiant de la conversation
            
        Returns:
            Informations sur la conversation ou None si non trouvée
        """
        query = "SELECT * FROM conversations WHERE conversation_id = ?"
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(query, (conversation_id,))
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la conversation {conversation_id}: {e}")
            return None
    
    def get_user_conversations(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Récupère les conversations d'un utilisateur
        
        Args:
            user_id: Identifiant de l'utilisateur
            limit: Nombre maximum de conversations à récupérer
            offset: Décalage pour la pagination
            
        Returns:
            Liste des conversations de l'utilisateur
        """
        query = """
        SELECT c.*, 
               (SELECT COUNT(*) FROM messages WHERE conversation_id = c.conversation_id) AS message_count,
               (SELECT content FROM messages WHERE conversation_id = c.conversation_id AND is_user = 1 ORDER BY created_at ASC LIMIT 1) AS first_message
        FROM conversations c
        WHERE c.user_id = ?
        ORDER BY c.updated_at DESC
        LIMIT ? OFFSET ?
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(query, (user_id, limit, offset))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des conversations de l'utilisateur {user_id}: {e}")
            return []
    
    def update_conversation(self, conversation_id: str, title: str = None) -> bool:
        """
        Met à jour une conversation
        
        Args:
            conversation_id: Identifiant de la conversation
            title: Nouveau titre (optionnel)
            
        Returns:
            True si la mise à jour a réussi, False sinon
        """
        if title is None:
            # Juste mettre à jour la date de mise à jour
            query = "UPDATE conversations SET updated_at = ? WHERE conversation_id = ?"
            params = (datetime.now().isoformat(), conversation_id)
        else:
            # Mettre à jour le titre et la date
            query = "UPDATE conversations SET title = ?, updated_at = ? WHERE conversation_id = ?"
            params = (title, datetime.now().isoformat(), conversation_id)
        
        try:
            with self._get_connection() as conn:
                conn.execute(query, params)
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de la conversation {conversation_id}: {e}")
            return False
    
    def delete_conversation(self, conversation_id: str, user_id: str) -> bool:
        """
        Supprime une conversation
        
        Args:
            conversation_id: Identifiant de la conversation
            user_id: Identifiant de l'utilisateur (pour vérification)
            
        Returns:
            True si la suppression a réussi, False sinon
        """
        query = "DELETE FROM conversations WHERE conversation_id = ? AND user_id = ?"
        try:
            with self._get_connection() as conn:
                conn.execute(query, (conversation_id, user_id))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la suppression de la conversation {conversation_id}: {e}")
            return False
    
    # Méthodes pour les messages
    
    def add_message(self, conversation_id: str, user_id: str, content: str, 
                   is_user: bool, metadata: Dict[str, Any] = None) -> Optional[str]:
        """
        Ajoute un message à une conversation
        
        Args:
            conversation_id: Identifiant de la conversation
            user_id: Identifiant de l'utilisateur
            content: Contenu du message
            is_user: True si c'est un message de l'utilisateur, False si c'est une réponse IA
            metadata: Métadonnées supplémentaires (JSON)
            
        Returns:
            ID du message créé ou None en cas d'erreur
        """
        # Générer un ID pour le message
        message_id = str(uuid.uuid4())
        
        # Convertir les métadonnées en JSON si présentes
        metadata_json = json.dumps(metadata) if metadata else None
        
        query = """
        INSERT INTO messages (message_id, conversation_id, user_id, is_user, content, metadata)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        try:
            with self._get_connection() as conn:
                conn.execute(query, (
                    message_id, 
                    conversation_id, 
                    user_id, 
                    1 if is_user else 0, 
                    content, 
                    metadata_json
                ))
                # Mettre à jour la date de mise à jour de la conversation
                conn.execute(
                    "UPDATE conversations SET updated_at = ? WHERE conversation_id = ?",
                    (datetime.now().isoformat(), conversation_id)
                )
                conn.commit()
            return message_id
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout du message à la conversation {conversation_id}: {e}")
            return None
    
    def get_conversation_messages(self, conversation_id: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Récupère les messages d'une conversation
        
        Args:
            conversation_id: Identifiant de la conversation
            limit: Nombre maximum de messages à récupérer
            offset: Décalage pour la pagination
            
        Returns:
            Liste des messages de la conversation
        """
        query = """
        SELECT * FROM messages 
        WHERE conversation_id = ?
        ORDER BY created_at ASC
        LIMIT ? OFFSET ?
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(query, (conversation_id, limit, offset))
                messages = []
                for row in cursor.fetchall():
                    message = dict(row)
                    # Convertir is_user en booléen
                    message['is_user'] = bool(message['is_user'])
                    # Convertir metadata de JSON en dictionnaire
                    if message['metadata']:
                        try:
                            message['metadata'] = json.loads(message['metadata'])
                        except:
                            message['metadata'] = {}
                    else:
                        message['metadata'] = {}
                    messages.append(message)
                return messages
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des messages de la conversation {conversation_id}: {e}")
            return []
    
    # Méthodes pour les feedback
    
    def add_feedback(self, message_id: str, user_id: str, rating: int, comment: str = None) -> Optional[str]:
        """
        Ajoute un feedback sur un message
        
        Args:
            message_id: Identifiant du message
            user_id: Identifiant de l'utilisateur
            rating: Note (1-5 ou binaire 0/1)
            comment: Commentaire optionnel
            
        Returns:
            ID du feedback créé ou None en cas d'erreur
        """
        # Générer un ID pour le feedback
        feedback_id = str(uuid.uuid4())
        
        query = """
        INSERT INTO feedback (feedback_id, message_id, user_id, rating, comment)
        VALUES (?, ?, ?, ?, ?)
        """
        try:
            with self._get_connection() as conn:
                conn.execute(query, (feedback_id, message_id, user_id, rating, comment))
                conn.commit()
            return feedback_id
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout du feedback pour le message {message_id}: {e}")
            return None
    
    def get_message_feedback(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère le feedback d'un message
        
        Args:
            message_id: Identifiant du message
            
        Returns:
            Informations sur le feedback ou None si non trouvé
        """
        query = "SELECT * FROM feedback WHERE message_id = ?"
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(query, (message_id,))
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du feedback pour le message {message_id}: {e}")
            return None
    
    # Méthodes utilitaires
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Récupère des statistiques sur la base de données
        
        Returns:
            Dictionnaire de statistiques
        """
        stats = {
            "users": 0,
            "conversations": 0,
            "messages": 0,
            "feedback": 0
        }
        
        try:
            with self._get_connection() as conn:
                for table in stats.keys():
                    cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                    stats[table] = cursor.fetchone()[0]
            return stats
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des statistiques: {e}")
            return stats