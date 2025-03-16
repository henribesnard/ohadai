"""
Gestionnaire de tokens JWT pour l'authentification.
"""
import os
import jwt
import secrets
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
import uuid

# Configuration du logging
logger = logging.getLogger("ohada_jwt")

class JWTManager:
    """Gestionnaire de tokens JWT"""
    
    def __init__(self, db_manager, secret_key: Optional[str] = None):
        """
        Initialise le gestionnaire JWT
        
        Args:
            db_manager: Instance du gestionnaire de base de données
            secret_key: Clé secrète pour signer les tokens (générée si non fournie)
        """
        self.db_manager = db_manager
        self.secret_key = secret_key or os.getenv("JWT_SECRET_KEY", secrets.token_hex(32))
        self.algorithm = "HS256"
        self.access_token_expire_minutes = int(os.getenv("JWT_EXPIRATION_MINUTES", "1440"))  # 24 heures par défaut
    
    def create_access_token(self, data: Dict[str, Any]) -> Tuple[str, datetime]:
        """
        Crée un token JWT d'accès
        
        Args:
            data: Données à inclure dans le token
            
        Returns:
            Tuple (token, date d'expiration)
        """
        to_encode = data.copy()
        
        # Définir la date d'expiration
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        # Ajouter les informations standard
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": str(uuid.uuid4())  # Identifiant unique du token
        })
        
        # Encoder le token
        token = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        
        return token, expire
    
    def decode_token(self, token: str) -> Dict[str, Any]:
        """
        Décode un token JWT
        
        Args:
            token: Token à décoder
            
        Returns:
            Payload du token décodé
            
        Raises:
            jwt.PyJWTError: Si le token est invalide ou expiré
        """
        # Décoder le token
        payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        
        # Vérifier si le token est révoqué
        jti = payload.get("jti")
        if jti and self.db_manager.is_token_revoked(jti):
            raise jwt.InvalidTokenError("Token révoqué")
        
        return payload
    
    def revoke_token(self, token: str) -> bool:
        """
        Révoque un token JWT
        
        Args:
            token: Token à révoquer
            
        Returns:
            True si le token a été révoqué, False sinon
        """
        try:
            # Décoder le token sans vérifier l'expiration
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm],
                options={"verify_exp": False}
            )
            
            # Récupérer les informations nécessaires
            jti = payload.get("jti")
            user_id = payload.get("sub")
            exp = payload.get("exp")
            
            if not jti or not user_id or not exp:
                logger.error("Token incomplet - impossible de le révoquer")
                return False
            
            # Convertir exp en datetime
            expiry = datetime.fromtimestamp(exp)
            
            # Ajouter à la liste de révocation
            return self.db_manager.revoke_token(jti, user_id, expiry)
            
        except Exception as e:
            logger.error(f"Erreur lors de la révocation du token: {e}")
            return False
    
    def create_email_verification_token(self, user_id: str, email: str) -> str:
        """
        Crée un token pour la vérification d'email
        
        Args:
            user_id: ID de l'utilisateur
            email: Email à vérifier
            
        Returns:
            Token de vérification
        """
        # Définir la date d'expiration (48 heures)
        expire = datetime.utcnow() + timedelta(hours=48)
        
        # Créer le payload
        payload = {
            "sub": user_id,
            "email": email,
            "type": "email_verification",
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": str(uuid.uuid4())
        }
        
        # Encoder le token
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        return token
    
    def create_password_reset_token(self, user_id: str, email: str) -> Tuple[str, datetime]:
        """
        Crée un token pour la réinitialisation de mot de passe
        
        Args:
            user_id: ID de l'utilisateur
            email: Email pour la réinitialisation
            
        Returns:
            Tuple (token, date d'expiration)
        """
        # Définir la date d'expiration (1 heure)
        expire = datetime.utcnow() + timedelta(hours=1)
        
        # Créer le payload
        payload = {
            "sub": user_id,
            "email": email,
            "type": "password_reset",
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": str(uuid.uuid4())
        }
        
        # Encoder le token
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        return token, expire
    
    def verify_special_token(self, token: str, expected_type: str) -> Dict[str, Any]:
        """
        Vérifie un token spécial (email ou réinitialisation)
        
        Args:
            token: Token à vérifier
            expected_type: Type attendu du token
            
        Returns:
            Payload du token décodé
            
        Raises:
            jwt.PyJWTError: Si le token est invalide ou expiré
        """
        # Décoder le token
        payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        
        # Vérifier le type du token
        token_type = payload.get("type")
        if token_type != expected_type:
            raise jwt.InvalidTokenError(f"Type de token invalide: {token_type}, attendu: {expected_type}")
        
        return payload