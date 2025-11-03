"""
Module de gestion de l'authentification avec système interne de mots de passe et JWT.
"""
import os
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
import uuid
import secrets
import hashlib
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Configuration du logging
logger = logging.getLogger("ohada_auth")

# Gestionnaire d'authentification
class AuthManager:
    """Gestionnaire d'authentification pour le système interne"""
    
    def __init__(self, db_manager):
        """
        Initialise le gestionnaire d'authentification
        
        Args:
            db_manager: Instance du gestionnaire de base de données
        """
        self.db_manager = db_manager
        self.security = HTTPBearer()
        
        # Configuration JWT
        self.jwt_secret = os.getenv("JWT_SECRET_KEY", secrets.token_hex(32))
        self.jwt_algorithm = "HS256"
        self.jwt_expiration = int(os.getenv("JWT_EXPIRATION_MINUTES", "1440"))  # 24 heures par défaut
    
    def _hash_password(self, password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """
        Génère un hash sécurisé d'un mot de passe
        
        Args:
            password: Mot de passe en clair
            salt: Sel optionnel (généré si non fourni)
            
        Returns:
            Tuple (hash du mot de passe, sel utilisé)
        """
        if salt is None:
            salt = secrets.token_hex(16)
        
        # Combiner le mot de passe et le sel
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # Nombre d'itérations
        ).hex()
        
        return key, salt
    
    def verify_password(self, password: str, stored_hash: str, salt: str) -> bool:
        """
        Vérifie si un mot de passe correspond au hash stocké
        
        Args:
            password: Mot de passe à vérifier
            stored_hash: Hash stocké dans la base de données
            salt: Sel utilisé pour le hash
            
        Returns:
            True si le mot de passe est correct, False sinon
        """
        new_hash, _ = self._hash_password(password, salt)
        return new_hash == stored_hash
    
    def create_jwt_token(self, user_id: str, email: str) -> Dict[str, Any]:
        """
        Crée un token JWT pour un utilisateur
        
        Args:
            user_id: Identifiant de l'utilisateur
            email: Email de l'utilisateur
            
        Returns:
            Dictionnaire contenant le token et sa date d'expiration
        """
        # Définir la date d'expiration
        expiration = datetime.utcnow() + timedelta(minutes=self.jwt_expiration)
        
        # Créer le payload du token
        payload = {
            "sub": user_id,
            "email": email,
            "iat": datetime.utcnow(),
            "exp": expiration,
            "jti": str(uuid.uuid4())  # Identifiant unique du token
        }
        
        # Générer le token
        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_at": expiration.isoformat()
        }
    
    def verify_jwt_token(self, token: str) -> Dict[str, Any]:
        """
        Vérifie un token JWT et retourne les informations utilisateur
        
        Args:
            token: Token JWT à vérifier
            
        Returns:
            Informations d'utilisateur contenues dans le token
            
        Raises:
            HTTPException: En cas d'erreur de validation
        """
        try:
            # Vérifier le token
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            
            # Extraire les informations utilisateur
            user_id = payload.get("sub")
            email = payload.get("email")
            
            if user_id is None or email is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token invalide - données manquantes"
                )
            
            # Vérifier si le token n'est pas révoqué (à implémenter avec une liste noire si nécessaire)
            
            return {
                "user_id": user_id,
                "email": email
            }
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token expiré")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expiré"
            )
        except jwt.InvalidTokenError as e:
            logger.error(f"Token invalide: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalide"
            )
    
    async def register_user(self, email: str, password: str, name: str = "") -> Dict[str, Any]:
        """
        Inscrit un nouvel utilisateur
        
        Args:
            email: Email de l'utilisateur
            password: Mot de passe en clair
            name: Nom de l'utilisateur (optionnel)
            
        Returns:
            Informations de l'utilisateur créé
            
        Raises:
            HTTPException: En cas d'erreur d'inscription
        """
        try:
            # Vérifier si l'utilisateur existe déjà
            existing_user = self.db_manager.get_user_by_email(email)
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Un utilisateur avec cet email existe déjà"
                )
            
            # Générer le hash du mot de passe
            password_hash, salt = self._hash_password(password)

            # Créer l'utilisateur avec la signature attendue
            user_id = self.db_manager.create_user(email, password_hash)
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Erreur lors de la création de l'utilisateur"
                )

            # Récupérer l'utilisateur créé
            user = self.db_manager.get_user_by_id(user_id)

            # Ajouter les champs manquants pour correspondre à UserResponse
            if user:
                user["name"] = name
                user["auth_provider"] = "internal"
                user["created_at"] = datetime.utcnow()
                user["last_login"] = None
                user["email_verified"] = False
            
            # Nettoyer les données sensibles avant de les retourner
            if user:
                if "password_hash" in user:
                    del user["password_hash"]
                if "salt" in user:
                    del user["salt"]
            
            return user
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erreur lors de l'inscription: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur lors de l'inscription"
            )
    
    async def login_user(self, email: str, password: str) -> Dict[str, Any]:
        """
        Connecte un utilisateur
        
        Args:
            email: Email de l'utilisateur
            password: Mot de passe en clair
            
        Returns:
            Token JWT et informations de l'utilisateur
            
        Raises:
            HTTPException: En cas d'erreur de connexion
        """
        try:
            # Récupérer l'utilisateur
            user = self.db_manager.get_user_by_email(email)
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Email ou mot de passe incorrect"
                )
            
            # Vérifier le mot de passe
            if "password_hash" not in user or "salt" not in user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Compte non configuré pour l'authentification par mot de passe"
                )
            
            if not self.verify_password(password, user["password_hash"], user["salt"]):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Email ou mot de passe incorrect"
                )
            
            # Mettre à jour la dernière connexion
            self.db_manager.update_user_login(user["user_id"])
            
            # Générer un token JWT
            token_data = self.create_jwt_token(user["user_id"], user["email"])
            
            # Nettoyer les données sensibles avant de les retourner
            if "password_hash" in user:
                del user["password_hash"]
            if "salt" in user:
                del user["salt"]
            
            return {
                "user": user,
                "token": token_data
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erreur lors de la connexion: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur lors de la connexion"
            )
    
    async def get_current_user(self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())) -> Dict[str, Any]:
        """
        Valide le token JWT et récupère l'utilisateur courant
        
        Args:
            credentials: Informations d'authentification
            
        Returns:
            Informations de l'utilisateur
            
        Raises:
            HTTPException: En cas d'erreur d'authentification
        """
        try:
            token = credentials.credentials
            
            # Vérifier le token JWT
            token_data = self.verify_jwt_token(token)
            
            # Récupérer l'utilisateur
            user = self.db_manager.get_user(token_data["user_id"])
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Utilisateur non trouvé"
                )
            
            # Nettoyer les données sensibles
            if "password_hash" in user:
                del user["password_hash"]
            if "salt" in user:
                del user["salt"]
            
            return user
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erreur d'authentification: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token d'authentification invalide"
            )

# Factory pour créer une dépendance FastAPI
def create_auth_dependency(db_manager):
    """
    Crée une fonction de dépendance pour FastAPI qui gère l'authentification

    Args:
        db_manager: Instance du gestionnaire de base de données

    Returns:
        Fonction de dépendance pour FastAPI
    """
    auth_manager = AuthManager(db_manager)

    async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
        return await auth_manager.get_current_user(credentials)

    return get_current_user

def create_optional_auth_dependency(db_manager):
    """
    Crée une fonction de dépendance optionnelle pour FastAPI (n'exige pas d'authentification)

    Args:
        db_manager: Instance du gestionnaire de base de données

    Returns:
        Fonction de dépendance pour FastAPI qui retourne None si pas authentifié
    """
    auth_manager = AuthManager(db_manager)
    security = HTTPBearer(auto_error=False)

    async def get_current_user_optional(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[Dict[str, Any]]:
        if credentials is None:
            return None

        try:
            return await auth_manager.get_current_user(credentials)
        except HTTPException:
            return None

    return get_current_user_optional