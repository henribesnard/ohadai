"""
Modèles Pydantic pour l'authentification interne.
"""
from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, Dict, Any
from datetime import datetime

class UserBase(BaseModel):
    """Modèle de base pour les utilisateurs"""
    email: EmailStr
    name: Optional[str] = None

class UserCreate(UserBase):
    """Modèle pour la création d'un utilisateur"""
    password: str = Field(..., min_length=8)
    
    @validator('password')
    def password_complexity(cls, v):
        """Valide la complexité du mot de passe"""
        if len(v) < 8:
            raise ValueError("Le mot de passe doit contenir au moins 8 caractères")
        
        # Au moins une lettre majuscule, une lettre minuscule et un chiffre
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        
        if not (has_upper and has_lower and has_digit):
            raise ValueError("Le mot de passe doit contenir au moins une lettre majuscule, une lettre minuscule et un chiffre")
            
        return v

class UserLogin(BaseModel):
    """Modèle pour la connexion d'un utilisateur"""
    email: EmailStr
    password: str

class UserResponse(UserBase):
    """Modèle pour la réponse utilisateur (sans données sensibles)"""
    user_id: str
    created_at: datetime
    last_login: Optional[datetime] = None
    auth_provider: str = "internal"
    email_verified: bool = False

class TokenResponse(BaseModel):
    """Modèle pour la réponse de token"""
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime

class UserWithToken(BaseModel):
    """Modèle combinant utilisateur et token"""
    user: UserResponse
    token: TokenResponse

class PasswordReset(BaseModel):
    """Modèle pour la demande de réinitialisation de mot de passe"""
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    """Modèle pour la confirmation de réinitialisation de mot de passe"""
    token: str
    email: EmailStr
    new_password: str = Field(..., min_length=8)
    
    @validator('new_password')
    def password_complexity(cls, v):
        """Valide la complexité du mot de passe"""
        if len(v) < 8:
            raise ValueError("Le mot de passe doit contenir au moins 8 caractères")
        
        # Au moins une lettre majuscule, une lettre minuscule et un chiffre
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        
        if not (has_upper and has_lower and has_digit):
            raise ValueError("Le mot de passe doit contenir au moins une lettre majuscule, une lettre minuscule et un chiffre")
            
        return v

class ChangePassword(BaseModel):
    """Modèle pour le changement de mot de passe"""
    current_password: str
    new_password: str = Field(..., min_length=8)
    
    @validator('new_password')
    def password_complexity(cls, v):
        """Valide la complexité du mot de passe"""
        if len(v) < 8:
            raise ValueError("Le mot de passe doit contenir au moins 8 caractères")
        
        # Au moins une lettre majuscule, une lettre minuscule et un chiffre
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        
        if not (has_upper and has_lower and has_digit):
            raise ValueError("Le mot de passe doit contenir au moins une lettre majuscule, une lettre minuscule et un chiffre")
            
        return v

class EmailVerification(BaseModel):
    """Modèle pour la vérification d'email"""
    token: str
    email: EmailStr