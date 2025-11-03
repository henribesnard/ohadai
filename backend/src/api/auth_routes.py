"""
Routes d'API pour l'authentification interne.
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import uuid
import logging
import json

# Import des modules internes
from src.auth.auth_manager import AuthManager
from src.auth.jwt_manager import JWTManager
from src.auth.auth_models import (
    UserCreate, UserLogin, UserResponse, TokenResponse, UserWithToken,
    PasswordReset, PasswordResetConfirm, ChangePassword, EmailVerification
)
from src.db.db_manager import DatabaseManager
from src.auth.auth_manager import create_auth_dependency

# Configuration du logging
logger = logging.getLogger("ohada_auth_routes")

# Création du routeur
router = APIRouter(prefix="/auth", tags=["authentication"])

# Création des dépendances
db_manager = DatabaseManager()
auth_manager = AuthManager(db_manager)
jwt_manager = JWTManager(db_manager)
get_current_user = create_auth_dependency(db_manager)

# Routes d'authentification

@router.post("/register", response_model=UserWithToken)
async def register(user: UserCreate, background_tasks: BackgroundTasks):
    """
    Inscrit un nouvel utilisateur et retourne un token JWT
    """
    try:
        # Créer l'utilisateur
        new_user = await auth_manager.register_user(
            email=user.email,
            password=user.password,
            name=user.name
        )

        # Créer un token JWT pour l'utilisateur
        token_data = auth_manager.create_jwt_token(
            user_id=new_user["user_id"],
            email=new_user["email"]
        )

        # Ajouter une tâche en arrière-plan pour envoyer l'email de vérification
        # background_tasks.add_task(send_verification_email, new_user["email"], new_user["user_id"])

        # Retourner l'utilisateur et le token
        return UserWithToken(
            user=UserResponse(**new_user),
            token=TokenResponse(**token_data)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de l'inscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de l'inscription"
        )

@router.post("/login", response_model=UserWithToken)
async def login(user_credentials: UserLogin):
    """
    Authentifie un utilisateur et retourne un token JWT
    """
    try:
        # Connecter l'utilisateur
        login_result = await auth_manager.login_user(
            email=user_credentials.email,
            password=user_credentials.password
        )
        
        # Formater la réponse
        return UserWithToken(
            user=UserResponse(**login_result["user"]),
            token=TokenResponse(**login_result["token"])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la connexion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la connexion"
        )

@router.post("/logout")
async def logout(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    """
    Déconnecte un utilisateur (révoque son token)
    """
    try:
        # Révoquer le token
        success = jwt_manager.revoke_token(credentials.credentials)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur lors de la déconnexion"
            )
        
        return {"status": "success", "message": "Déconnexion réussie"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la déconnexion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la déconnexion"
        )

@router.post("/password-reset", response_model=Dict[str, str])
async def request_password_reset(reset_request: PasswordReset, background_tasks: BackgroundTasks):
    """
    Demande une réinitialisation de mot de passe
    """
    try:
        # Vérifier si l'utilisateur existe
        user = db_manager.get_user_by_email(reset_request.email)
        
        if user:
            # Générer un token de réinitialisation
            token, expiry = jwt_manager.create_password_reset_token(user["user_id"], user["email"])
            
            # Enregistrer le token dans la base de données
            db_manager.set_password_reset_token(user["email"], token, expiry)
            
            # Ajouter une tâche en arrière-plan pour envoyer l'email de réinitialisation
            # background_tasks.add_task(send_password_reset_email, user["email"], token)
        
        # Toujours retourner un succès même si l'email n'existe pas (sécurité)
        return {"status": "success", "message": "Si un compte existe avec cet email, un lien de réinitialisation a été envoyé"}
        
    except Exception as e:
        logger.error(f"Erreur lors de la demande de réinitialisation: {e}")
        # Toujours retourner un succès (sécurité)
        return {"status": "success", "message": "Si un compte existe avec cet email, un lien de réinitialisation a été envoyé"}

@router.post("/password-reset-confirm", response_model=Dict[str, str])
async def confirm_password_reset(reset_confirm: PasswordResetConfirm):
    """
    Confirme une réinitialisation de mot de passe avec un token
    """
    try:
        # Vérifier le token
        user_id = db_manager.verify_password_reset_token(reset_confirm.token, reset_confirm.email)
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token invalide ou expiré"
            )
        
        # Récupérer l'utilisateur
        user = db_manager.get_user(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur non trouvé"
            )
        
        # Générer le nouveau hash de mot de passe
        password_hash, salt = auth_manager._hash_password(reset_confirm.new_password)
        
        # Mettre à jour le mot de passe
        success = db_manager.update_user(user_id, {
            "password_hash": password_hash,
            "salt": salt
        })
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur lors de la mise à jour du mot de passe"
            )
        
        # Supprimer le token de réinitialisation
        db_manager.clear_password_reset_token(user_id)
        
        return {"status": "success", "message": "Mot de passe mis à jour avec succès"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la confirmation de réinitialisation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la réinitialisation du mot de passe"
        )

@router.post("/change-password")
async def change_password(
    password_change: ChangePassword,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Change le mot de passe d'un utilisateur connecté
    """
    try:
        user_id = current_user["user_id"]
        
        # Vérifier l'ancien mot de passe
        if not auth_manager.verify_password(
            password_change.current_password,
            current_user["password_hash"],
            current_user["salt"]
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mot de passe actuel incorrect"
            )
        
        # Générer le nouveau hash
        password_hash, salt = auth_manager._hash_password(password_change.new_password)
        
        # Mettre à jour le mot de passe
        success = db_manager.update_user(user_id, {
            "password_hash": password_hash,
            "salt": salt
        })
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur lors de la mise à jour du mot de passe"
            )
        
        return {"status": "success", "message": "Mot de passe mis à jour avec succès"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors du changement de mot de passe: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors du changement de mot de passe"
        )

@router.post("/verify-email")
async def verify_email(verification: EmailVerification):
    """
    Vérifie l'email d'un utilisateur avec un token
    """
    try:
        # Vérifier le token
        try:
            payload = jwt_manager.verify_special_token(verification.token, "email_verification")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token invalide ou expiré"
            )
        
        # Vérifier que l'email correspond
        if payload["email"] != verification.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email ne correspond pas au token"
            )
        
        # Marquer l'email comme vérifié
        success = db_manager.verify_email(payload["sub"])
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur lors de la vérification de l'email"
            )
        
        return {"status": "success", "message": "Email vérifié avec succès"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la vérification de l'email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la vérification de l'email"
        )

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Récupère les informations de l'utilisateur actuellement authentifié
    """
    return UserResponse(**current_user)