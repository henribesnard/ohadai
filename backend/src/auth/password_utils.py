"""
Utilitaires pour la gestion des mots de passe avec hashage sécurisé.
"""
import secrets
import hashlib
import re
from typing import Tuple, Optional

def generate_salt(size: int = 16) -> str:
    """
    Génère un sel cryptographique aléatoire
    
    Args:
        size: Taille du sel en octets
        
    Returns:
        Sel en format hexadécimal
    """
    return secrets.token_hex(size)

def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """
    Génère un hash sécurisé d'un mot de passe
    
    Args:
        password: Mot de passe en clair
        salt: Sel optionnel (généré si non fourni)
        
    Returns:
        Tuple (hash du mot de passe, sel utilisé)
    """
    if salt is None:
        salt = generate_salt()
    
    # Combiner le mot de passe et le sel
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000  # Nombre d'itérations
    ).hex()
    
    return key, salt

def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """
    Vérifie si un mot de passe correspond au hash stocké
    
    Args:
        password: Mot de passe à vérifier
        stored_hash: Hash stocké dans la base de données
        salt: Sel utilisé pour le hash
        
    Returns:
        True si le mot de passe est correct, False sinon
    """
    new_hash, _ = hash_password(password, salt)
    return new_hash == stored_hash

def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Valide la force d'un mot de passe
    
    Args:
        password: Mot de passe à valider
        
    Returns:
        Tuple (est_valide, message_erreur)
    """
    if len(password) < 8:
        return False, "Le mot de passe doit contenir au moins 8 caractères"
    
    # Vérifier la présence d'au moins une lettre majuscule, une lettre minuscule et un chiffre
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(not c.isalnum() for c in password)
    
    if not has_upper:
        return False, "Le mot de passe doit contenir au moins une lettre majuscule"
    
    if not has_lower:
        return False, "Le mot de passe doit contenir au moins une lettre minuscule"
    
    if not has_digit:
        return False, "Le mot de passe doit contenir au moins un chiffre"
    
    # Vérifier les caractères spéciaux (optionnel mais recommandé)
    if not has_special:
        return False, "Le mot de passe devrait contenir au moins un caractère spécial"
    
    # Vérifier la présence de mots de passe courants (optionnel)
    common_passwords = ["password", "123456", "qwerty", "admin", "welcome", "letmein"]
    password_lower = password.lower()
    
    for common in common_passwords:
        if common in password_lower:
            return False, "Le mot de passe contient une séquence trop commune"
    
    return True, ""

def generate_secure_password() -> str:
    """
    Génère un mot de passe aléatoire sécurisé
    
    Returns:
        Mot de passe généré
    """
    # Paramètres
    length = 12
    num_uppercase = 2
    num_digits = 2
    num_special = 2
    
    # Ensemble de caractères
    lowercase = 'abcdefghijklmnopqrstuvwxyz'
    uppercase = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    digits = '0123456789'
    special = '!@#$%^&*()-_=+[]{}|;:,.<>?'
    
    # Sélectionner des caractères aléatoires pour chaque groupe
    password_chars = []
    
    # Ajouter des majuscules
    for _ in range(num_uppercase):
        password_chars.append(secrets.choice(uppercase))
    
    # Ajouter des chiffres
    for _ in range(num_digits):
        password_chars.append(secrets.choice(digits))
    
    # Ajouter des caractères spéciaux
    for _ in range(num_special):
        password_chars.append(secrets.choice(special))
    
    # Remplir le reste avec des minuscules
    for _ in range(length - num_uppercase - num_digits - num_special):
        password_chars.append(secrets.choice(lowercase))
    
    # Mélanger les caractères
    secrets.SystemRandom().shuffle(password_chars)
    
    # Joindre les caractères
    password = ''.join(password_chars)
    
    return password