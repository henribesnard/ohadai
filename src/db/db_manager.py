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
        # Schéma SQL mis à jour pour l'authentification interne
        schema_sql = """
        -- Utilisateurs
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            name TEXT,
            profile_picture TEXT,
            password_hash TEXT,
            salt TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            auth_provider TEXT DEFAULT 'internal',
            reset_token TEXT,
            reset_token_expiry TIMESTAMP,
            email_verified BOOLEAN DEFAULT 0
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

        -- Table de révocation des tokens (pour la déconnexion)
        CREATE TABLE IF NOT EXISTS revoked_tokens (
            jti TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            revoked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expiry TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        );

        -- Index pour améliorer les performances
        CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
        CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
        CREATE INDEX IF NOT EXISTS idx_feedback_message ON feedback(message_id);
        CREATE INDEX IF NOT EXISTS idx_revoked_tokens_user ON revoked_tokens(user_id);
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        """
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.executescript(schema_sql)
                
                # Vérifier si nous devons ajouter de nouvelles colonnes aux tables existantes
                cursor = conn.cursor()
                
                # Vérifier et ajouter les colonnes pour l'authentification interne à la table users
                cursor.execute("PRAGMA table_info(users)")
                columns = {column[1] for column in cursor.fetchall()}
                
                # Colonnes à ajouter si elles n'existent pas
                new_columns = {
                    "password_hash": "TEXT",
                    "salt": "TEXT",
                    "reset_token": "TEXT",
                    "reset_token_expiry": "TIMESTAMP",
                    "email_verified": "BOOLEAN DEFAULT 0"
                }
                
                for column, datatype in new_columns.items():
                    if column not in columns:
                        cursor.execute(f"ALTER TABLE users ADD COLUMN {column} {datatype}")
                        logger.info(f"Colonne '{column}' ajoutée à la table users")
                
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
        
        # Construire la requête SQL dynamiquement en fonction des champs fournis
        fields = []
        placeholders = []
        values = []
        
        # Champs requis
        fields.append('user_id')
        placeholders.append('?')
        values.append(user_id)
        
        fields.append('email')
        placeholders.append('?')
        values.append(user_info['email'])
        
        # Champs optionnels avec valeurs par défaut dans la base de données
        for field in ['name', 'profile_picture', 'password_hash', 'salt', 'auth_provider']:
            if field in user_info and user_info[field] is not None:
                fields.append(field)
                placeholders.append('?')
                values.append(user_info[field])
        
        # Construction de la requête
        query = f"""
        INSERT INTO users ({', '.join(fields)}) 
        VALUES ({', '.join(placeholders)})
        """
        
        try:
            with self._get_connection() as conn:
                conn.execute(query, values)
                
                # Définir last_login
                now = datetime.now().isoformat()
                conn.execute(
                    "UPDATE users SET last_login = ? WHERE user_id = ?",
                    (now, user_id)
                )
                
                conn.commit()
            return user_id
            
        except sqlite3.IntegrityError:
            # L'utilisateur existe déjà (contrainte d'unicité sur l'email)
            logger.warning(f"Tentative de création d'un utilisateur avec un email existant: {user_info['email']}")
            return None
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de l'utilisateur: {e}")
            return None
    
    def update_user(self, user_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Met à jour les informations d'un utilisateur
        
        Args:
            user_id: Identifiant de l'utilisateur
            update_data: Données à mettre à jour
            
        Returns:
            True si la mise à jour a réussi, False sinon
        """
        if not update_data:
            return False
        
        # Construire la requête SET dynamiquement
        set_parts = []
        values = []
        
        for key, value in update_data.items():
            # Ne pas permettre la mise à jour de l'ID utilisateur
            if key == 'user_id':
                continue
                
            set_parts.append(f"{key} = ?")
            values.append(value)
        
        if not set_parts:
            return False
        
        # Ajouter l'ID utilisateur à la fin des valeurs
        values.append(user_id)
        
        query = f"""
        UPDATE users 
        SET {', '.join(set_parts)}
        WHERE user_id = ?
        """
        
        try:
            with self._get_connection() as conn:
                conn.execute(query, values)
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de l'utilisateur {user_id}: {e}")
            return False
    
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
    
    def set_password_reset_token(self, email: str, token: str, expiry: datetime) -> bool:
        """
        Définit un token de réinitialisation de mot de passe
        
        Args:
            email: Email de l'utilisateur
            token: Token de réinitialisation
            expiry: Date d'expiration du token
            
        Returns:
            True si la mise à jour a réussi, False sinon
        """
        query = """
        UPDATE users 
        SET reset_token = ?, reset_token_expiry = ? 
        WHERE email = ?
        """
        try:
            with self._get_connection() as conn:
                conn.execute(query, (token, expiry.isoformat(), email))
                conn.commit()
                
                # Vérifier que la mise à jour a bien été effectuée
                cursor = conn.execute("SELECT user_id FROM users WHERE email = ? AND reset_token = ?", 
                                     (email, token))
                return cursor.fetchone() is not None
                
        except Exception as e:
            logger.error(f"Erreur lors de la définition du token de réinitialisation: {e}")
            return False
    
    def verify_password_reset_token(self, token: str, email: str) -> Optional[str]:
        """
        Vérifie un token de réinitialisation de mot de passe
        
        Args:
            token: Token de réinitialisation
            email: Email de l'utilisateur
            
        Returns:
            ID utilisateur si le token est valide, None sinon
        """
        query = """
        SELECT user_id FROM users 
        WHERE email = ? AND reset_token = ? AND reset_token_expiry > ?
        """
        try:
            with self._get_connection() as conn:
                now = datetime.now().isoformat()
                cursor = conn.execute(query, (email, token, now))
                row = cursor.fetchone()
                return row['user_id'] if row else None
        except Exception as e:
            logger.error(f"Erreur lors de la vérification du token de réinitialisation: {e}")
            return None
    
    def clear_password_reset_token(self, user_id: str) -> bool:
        """
        Efface un token de réinitialisation après utilisation
        
        Args:
            user_id: ID de l'utilisateur
            
        Returns:
            True si la mise à jour a réussi, False sinon
        """
        query = "UPDATE users SET reset_token = NULL, reset_token_expiry = NULL WHERE user_id = ?"
        try:
            with self._get_connection() as conn:
                conn.execute(query, (user_id,))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'effacement du token de réinitialisation: {e}")
            return False
    
    def revoke_token(self, jti: str, user_id: str, expiry: datetime) -> bool:
        """
        Ajoute un token à la liste des tokens révoqués (pour la déconnexion)
        
        Args:
            jti: Identifiant du token
            user_id: Identifiant de l'utilisateur
            expiry: Date d'expiration du token
            
        Returns:
            True si l'ajout a réussi, False sinon
        """
        query = """
        INSERT INTO revoked_tokens (jti, user_id, expiry)
        VALUES (?, ?, ?)
        """
        try:
            with self._get_connection() as conn:
                conn.execute(query, (jti, user_id, expiry.isoformat()))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la révocation du token: {e}")
            return False
    
    def is_token_revoked(self, jti: str) -> bool:
        """
        Vérifie si un token est révoqué
        
        Args:
            jti: Identifiant du token
            
        Returns:
            True si le token est révoqué, False sinon
        """
        query = "SELECT 1 FROM revoked_tokens WHERE jti = ?"
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(query, (jti,))
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de révocation du token: {e}")
            return False
    
    def clean_expired_tokens(self) -> int:
        """
        Nettoie les tokens révoqués expirés
        
        Returns:
            Nombre de tokens supprimés
        """
        query = "DELETE FROM revoked_tokens WHERE expiry < ?"
        try:
            with self._get_connection() as conn:
                now = datetime.now().isoformat()
                cursor = conn.execute(query, (now,))
                deleted = cursor.rowcount
                conn.commit()
            return deleted
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage des tokens expirés: {e}")
            return 0
    
    def verify_email(self, user_id: str) -> bool:
        """
        Marque l'email d'un utilisateur comme vérifié
        
        Args:
            user_id: ID de l'utilisateur
            
        Returns:
            True si la mise à jour a réussi, False sinon
        """
        query = "UPDATE users SET email_verified = 1 WHERE user_id = ?"
        try:
            with self._get_connection() as conn:
                conn.execute(query, (user_id,))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de l'email: {e}")
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
            "feedback": 0,
            "revoked_tokens": 0
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
    
    def cleanup_database(self) -> Dict[str, int]:
        """
        Nettoie la base de données (supprime les tokens révoqués expirés)
        
        Returns:
            Statistiques sur les nettoyages effectués
        """
        cleanup_stats = {
            "revoked_tokens_removed": 0
        }
        
        try:
            # Nettoyer les tokens révoqués expirés
            cleanup_stats["revoked_tokens_removed"] = self.clean_expired_tokens()
            
            return cleanup_stats
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage de la base de données: {e}")
            return cleanup_stats