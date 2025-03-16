"""
Module de gestion de l'authentification pour intégrer Google OAuth.
"""
import os
import json
import logging
import requests
from typing import Dict, Any, Optional
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials

# Configuration du logging
logger = logging.getLogger("ohada_auth")

# Gestionnaire d'authentification
class AuthManager:
    """Gestionnaire d'authentification pour les services OAuth externes"""
    
    def __init__(self, db_manager):
        """
        Initialise le gestionnaire d'authentification
        
        Args:
            db_manager: Instance du gestionnaire de base de données
        """
        self.db_manager = db_manager
        self.google_client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.security = HTTPBearer()
    
    async def verify_google_token(self, token: str) -> Dict[str, Any]:
        """
        Vérifie un token ID Google et retourne les informations d'utilisateur
        
        Args:
            token: Token ID Google
            
        Returns:
            Informations d'utilisateur validées
            
        Raises:
            HTTPException: En cas d'erreur de validation
        """
        try:
            # Vérifier le token avec l'API Google
            if not self.google_client_id:
                logger.error("GOOGLE_CLIENT_ID non défini")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Configuration OAuth manquante"
                )
            
            idinfo = id_token.verify_oauth2_token(
                token, 
                google_requests.Request(), 
                self.google_client_id
            )
            
            # Vérifier que l'émetteur est bien Google
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Émetteur invalide')
            
            # Extraire les informations pertinentes
            user_info = {
                'user_id': idinfo['sub'],  # L'ID Google unique
                'email': idinfo['email'],
                'name': idinfo.get('name', ''),
                'profile_picture': idinfo.get('picture', ''),
                'auth_provider': 'google'
            }
            
            return user_info
            
        except ValueError as e:
            logger.error(f"Erreur de validation du token Google: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token Google invalide"
            )
    
    async def create_or_update_user(self, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crée ou met à jour un utilisateur dans la base de données
        
        Args:
            user_info: Informations de l'utilisateur validées
            
        Returns:
            Informations complètes de l'utilisateur
            
        Raises:
            HTTPException: En cas d'erreur
        """
        try:
            # Vérifier si l'utilisateur existe déjà
            existing_user = self.db_manager.get_user(user_info['user_id'])
            
            if existing_user:
                # Mettre à jour la dernière connexion
                self.db_manager.update_user_login(user_info['user_id'])
                return existing_user
            
            # Créer l'utilisateur s'il n'existe pas
            user_id = self.db_manager.create_user(user_info)
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Erreur lors de la création de l'utilisateur"
                )
            
            return self.db_manager.get_user(user_id)
            
        except Exception as e:
            logger.error(f"Erreur lors de la création/mise à jour de l'utilisateur: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur de base de données"
            )
    
    async def get_current_user(self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())) -> Dict[str, Any]:
        """
        Valide le token et récupère l'utilisateur courant
        
        Args:
            credentials: Informations d'authentification
            
        Returns:
            Informations de l'utilisateur
            
        Raises:
            HTTPException: En cas d'erreur d'authentification
        """
        try:
            token = credentials.credentials
            
            # Déterminer le type de token (actuellement uniquement Google)
            # Pour une implémentation complète, il faudrait vérifier le type de token
            
            # Pour Google
            user_info = await self.verify_google_token(token)
            user = await self.create_or_update_user(user_info)
            
            return user
            
        except HTTPException as e:
            raise e
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