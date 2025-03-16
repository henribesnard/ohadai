"""
Module d'utilitaires pour le système OHADA Expert-Comptable.
Fournit des fonctions communes utilisées par différents composants.
"""

import os
import yaml
import logging
import math
from typing import Dict, Any, Optional, List, Union
import json
import time

# Configuration du logging
logger = logging.getLogger("ohada_utils")

def load_llm_config(config_path: str = "./src/config/llm_config.yaml") -> Dict[str, Any]:
    """
    Charge la configuration des modèles de langage depuis un fichier YAML
    
    Args:
        config_path: Chemin vers le fichier de configuration
        
    Returns:
        Dictionnaire de configuration ou None en cas d'erreur
    """
    try:
        if not os.path.exists(config_path):
            logger.warning(f"Fichier de configuration {config_path} non trouvé.")
            return None
                
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        return config
    except Exception as e:
        logger.error(f"Erreur lors du chargement de la configuration: {e}")
        return None

def format_time(seconds: float) -> str:
    """
    Formate un temps en secondes en une chaîne lisible
    
    Args:
        seconds: Temps en secondes
        
    Returns:
        Chaîne formatée (ex: "2.5s" ou "1m 30s")
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    else:
        minutes = math.floor(seconds / 60)
        remaining_seconds = seconds - (minutes * 60)
        return f"{minutes}m {remaining_seconds:.0f}s"

def check_keys(required_providers: List[str] = None) -> Dict[str, bool]:
    """
    Vérifie si les clés API nécessaires sont définies
    
    Args:
        required_providers: Liste des fournisseurs à vérifier (ou None pour tous)
        
    Returns:
        Dictionnaire indiquant quels fournisseurs sont disponibles
    """
    # Charger la configuration
    config = load_llm_config()
    if not config:
        return {"error": "Configuration non disponible"}
    
    result = {}
    
    # Si aucun fournisseur spécifique n'est demandé, vérifier tous les fournisseurs
    if not required_providers:
        required_providers = list(config.get("providers", {}).keys())
    
    # Vérifier chaque fournisseur
    for provider in required_providers:
        if provider not in config.get("providers", {}):
            result[provider] = False
            continue
        
        provider_config = config["providers"][provider]
        
        # Vérifier si le fournisseur est désactivé
        if provider_config.get("enabled") is False:
            result[provider] = False
            continue
        
        # Vérifier si une clé API est nécessaire
        api_key_env = provider_config.get("api_key_env")
        if not api_key_env:
            # Pour les fournisseurs sans clé API (comme les modèles locaux)
            result[provider] = True
            continue
        
        # Vérifier si la clé API est définie
        api_key = os.getenv(api_key_env)
        result[provider] = bool(api_key)
    
    return result

def extract_relevant_text(document: str, query: str, max_chars: int = 500) -> str:
    """
    Extrait le passage le plus pertinent d'un document pour une requête donnée
    
    Args:
        document: Texte complet du document
        query: Requête de l'utilisateur
        max_chars: Longueur maximale de l'extrait
        
    Returns:
        Extrait pertinent du document
    """
    # Découper le document en paragraphes
    paragraphs = [p for p in document.split('\n') if p.strip()]
    
    if not paragraphs:
        return ""
    
    # Préparer les mots-clés à rechercher (mots de la requête)
    keywords = {word.lower() for word in query.split() if len(word) > 3}
    
    # Évaluer chaque paragraphe
    scored_paragraphs = []
    for para in paragraphs:
        score = 0
        para_lower = para.lower()
        
        # Compter le nombre de mots-clés trouvés
        for keyword in keywords:
            if keyword in para_lower:
                score += 1
        
        scored_paragraphs.append((para, score))
    
    # Trier les paragraphes par score
    scored_paragraphs.sort(key=lambda x: x[1], reverse=True)
    
    # Prendre les meilleurs paragraphes jusqu'à atteindre max_chars
    result = []
    current_length = 0
    
    for para, score in scored_paragraphs:
        if score == 0:  # Ignorer les paragraphes sans correspondance
            continue
            
        if current_length + len(para) <= max_chars:
            result.append(para)
            current_length += len(para)
        else:
            # Si le paragraphe est trop long, couper à max_chars
            remaining = max_chars - current_length
            if remaining > 50:  # Au moins 50 caractères pour que ce soit utile
                result.append(para[:remaining] + "...")
            break
    
    # Si aucun paragraphe pertinent n'a été trouvé, prendre le début du document
    if not result:
        return document[:max_chars] + "..."
    
    return "\n\n".join(result)

def clean_text_for_display(text: str, max_length: int = 500) -> str:
    """
    Nettoie et tronque un texte pour l'affichage
    
    Args:
        text: Texte à nettoyer
        max_length: Longueur maximale
        
    Returns:
        Texte nettoyé et tronqué
    """
    # Retirer les espaces multiples
    text = ' '.join(text.split())
    
    # Tronquer le texte si nécessaire
    if len(text) > max_length:
        text = text[:max_length] + "..."
    
    return text

def save_query_history(query: str, answer: str, metadata: Dict[str, Any] = None) -> None:
    """
    Sauvegarde une question et sa réponse dans l'historique
    
    Args:
        query: Question posée
        answer: Réponse générée
        metadata: Métadonnées supplémentaires (perf, etc.)
    """
    try:
        history_dir = "./data/history"
        os.makedirs(history_dir, exist_ok=True)
        
        # Préparer l'entrée d'historique
        entry = {
            "query": query,
            "answer": answer,
            "timestamp": time.time(),
            "metadata": metadata or {}
        }
        
        # Générer un nom de fichier
        timestamp = int(entry["timestamp"])
        filename = f"{history_dir}/query_{timestamp}.json"
        
        # Sauvegarder l'entrée
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(entry, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde de l'historique: {e}")

def get_query_history(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Récupère l'historique des questions et réponses
    
    Args:
        limit: Nombre maximum d'entrées à récupérer
        
    Returns:
        Liste des entrées d'historique
    """
    try:
        history_dir = "./data/history"
        
        if not os.path.exists(history_dir):
            return []
        
        # Lister les fichiers d'historique
        history_files = [os.path.join(history_dir, f) for f in os.listdir(history_dir) 
                        if f.startswith("query_") and f.endswith(".json")]
        
        # Trier par date (plus récent en premier)
        history_files.sort(reverse=True)
        
        # Limiter le nombre de fichiers
        history_files = history_files[:limit]
        
        # Charger les entrées
        entries = []
        for file in history_files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    entry = json.load(f)
                    entries.append(entry)
            except Exception as e:
                logger.error(f"Erreur lors de la lecture du fichier {file}: {e}")
        
        return entries
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de l'historique: {e}")
        return []