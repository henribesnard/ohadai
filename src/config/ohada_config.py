"""
Module de configuration pour le système OHADA Expert-Comptable.
Gère le chargement et l'accès aux configurations des modèles de langage.
Standardisé pour utiliser OpenAI pour les embeddings.
"""

import os
import yaml
import logging
from typing import List, Dict, Any, Tuple, Optional

# Configuration du logging
logger = logging.getLogger("ohada_config")

class LLMConfig:
    """Gestionnaire de configuration pour les modèles de langage"""
    
    def __init__(self, config_path: str = "./src/config"):
        """
        Initialise la configuration des modèles de langage
        
        Args:
            config_path: Chemin vers le répertoire de configuration
        """
        self.config_path = config_path
        self.config = self._load_config()
        
        # Valider la configuration chargée
        if not self.config:
            logger.warning("Configuration invalide ou manquante. Utilisation des valeurs par défaut.")
            self.config = self._get_default_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Charge la configuration depuis le fichier YAML approprié selon l'environnement
        
        Returns:
            Configuration chargée ou configuration par défaut en cas d'erreur
        """
        try:
            # Vérifier l'environnement d'exécution
            environment = os.getenv("OHADA_ENV", "test")
            
            # Déterminer le chemin du fichier de configuration
            if environment == "production":
                config_file = "llm_config_production.yaml"
            else:
                config_file = "llm_config_test.yaml"
                
            # Construire le chemin complet
            if os.path.isdir(self.config_path):
                # Si c'est un répertoire, construire le chemin complet
                config_path = os.path.join(self.config_path, config_file)
            else:
                # Si c'est déjà un chemin de fichier, utiliser le répertoire parent
                config_path = os.path.join(os.path.dirname(self.config_path), config_file)
                
            logger.info(f"Environnement {environment} détecté, utilisation de la configuration: {config_path}")
            
            if not os.path.exists(config_path):
                logger.warning(f"Fichier de configuration {config_path} non trouvé.")
                return self._get_default_config()
                    
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                    
            # Vérifier la structure minimale requise
            if not config or 'providers' not in config:
                logger.error("Structure de configuration invalide.")
                return self._get_default_config()
                    
            return config
                
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la configuration: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """
        Retourne une configuration par défaut standardisée sur OpenAI pour les embeddings
        
        Returns:
            Configuration par défaut
        """
        return {
            "default_provider": "openai",
            "default_embedding_provider": "openai",
            "provider_priority": ["openai", "deepseek"],
            "embedding_provider_priority": ["openai"],
            "providers": {
                "openai": {
                    "api_key_env": "OPENAI_API_KEY",
                    "models": {
                        "default": "gpt-3.5-turbo-0125",
                        "embedding": "text-embedding-3-small",
                        "response": "gpt-3.5-turbo-0125"
                    },
                    "parameters": {
                        "temperature": 0.3,
                        "top_p": 0.9,
                        "max_tokens": 1000,
                        "dimensions": 1536
                    }
                },
                "deepseek": {
                    "api_key_env": "DEEPSEEK_API_KEY",
                    "base_url": "https://api.deepseek.com/v1",
                    "models": {
                        "default": "deepseek-chat",
                        "analysis": "deepseek-chat",
                        "response": "deepseek-chat"
                    },
                    "parameters": {
                        "temperature": 0.3,
                        "top_p": 0.9,
                        "max_tokens": 1500
                    }
                }
            },
            "assistant_personality": {
                "name": "Expert OHADA",
                "expertise": "comptabilité et normes SYSCOHADA",
                "region": "zone OHADA (Afrique)",
                "language": "fr",
                "tone": "professionnel"
            }
        }
    
    def get_provider_list(self) -> List[str]:
        """
        Retourne la liste des fournisseurs disponibles dans l'ordre de priorité
        
        Returns:
            Liste de fournisseurs prioritaires
        """
        # Si une liste de priorité est définie explicitement
        if "provider_priority" in self.config:
            return self.config["provider_priority"]
        
        # Sinon, utiliser le fournisseur par défaut en premier, puis les autres
        providers = list(self.config["providers"].keys())
        default_provider = self.config.get("default_provider")
        
        if default_provider and default_provider in providers:
            # Placer le fournisseur par défaut en premier
            providers.remove(default_provider)
            return [default_provider] + providers
        
        return providers
    
    def get_embedding_provider_list(self) -> List[str]:
        """
        Retourne la liste des fournisseurs d'embeddings dans l'ordre de priorité
        
        Returns:
            Liste de fournisseurs d'embeddings prioritaires
        """
        # Si une liste de priorité est définie explicitement pour les embeddings
        if "embedding_provider_priority" in self.config:
            return self.config["embedding_provider_priority"]
        
        # Sinon, utiliser le fournisseur d'embedding par défaut en premier, puis la liste normale
        default_embedding_provider = self.config.get("default_embedding_provider")
        providers = self.get_provider_list()
        
        if default_embedding_provider:
            if default_embedding_provider in providers:
                providers.remove(default_embedding_provider)
            return [default_embedding_provider] + providers
        
        return providers
    
    def get_provider_config(self, provider: str) -> Dict[str, Any]:
        """
        Retourne la configuration d'un fournisseur spécifique
        
        Args:
            provider: Nom du fournisseur
            
        Returns:
            Configuration du fournisseur ou dictionnaire vide si non trouvé
        """
        if provider not in self.config["providers"]:
            logger.warning(f"Fournisseur {provider} non trouvé dans la configuration.")
            return {}
        
        # Vérifier si le fournisseur est activé
        provider_config = self.config["providers"][provider]
        if provider_config.get("enabled") is False:
            logger.warning(f"Fournisseur {provider} désactivé dans la configuration.")
            return {}
        
        return provider_config
    
    def get_embedding_model(self, provider: str = None) -> Tuple[str, str, Dict[str, Any]]:
        """
        Retourne le modèle d'embedding à utiliser
        
        Args:
            provider: Nom du fournisseur (ou None pour utiliser l'ordre de priorité)
            
        Returns:
            (provider_name, model_name, params)
        """
        # Utiliser le fournisseur spécifié ou la liste de priorité pour les embeddings
        providers = [provider] if provider else self.get_embedding_provider_list()
        
        for p in providers:
            provider_config = self.get_provider_config(p)
            if not provider_config:
                continue
            
            # Vérifier si le fournisseur a un modèle d'embedding
            models = provider_config.get("models", {})
            embedding_model = models.get("embedding")
            
            # Si pas de modèle d'embedding spécifique, essayer le modèle par défaut
            if not embedding_model:
                embedding_model = models.get("default")
            
            if embedding_model:
                # Récupérer les paramètres du fournisseur
                params = provider_config.get("parameters", {}).copy()
                # Ajouter l'URL de base si spécifiée
                if "base_url" in provider_config:
                    params["base_url"] = provider_config["base_url"]
                # Obtenir la variable d'environnement pour la clé API
                api_key_env = provider_config.get("api_key_env")
                if api_key_env:
                    params["api_key_env"] = api_key_env
                
                return p, embedding_model, params
        
        # Fallback sur OpenAI au lieu du modèle local
        logger.warning("Aucun fournisseur d'embedding valide trouvé, utilisation d'OpenAI par défaut")
        return "openai", "text-embedding-3-small", {"api_key_env": "OPENAI_API_KEY", "dimensions": 1536}
    
    def get_response_model(self, provider: str = None) -> Tuple[str, str, Dict[str, Any]]:
        """
        Retourne le modèle de réponse à utiliser
        
        Args:
            provider: Nom du fournisseur (ou None pour utiliser l'ordre de priorité)
            
        Returns:
            (provider_name, model_name, params)
        """
        providers = [provider] if provider else self.get_provider_list()
        
        for p in providers:
            provider_config = self.get_provider_config(p)
            if not provider_config:
                continue
            
            # Vérifier si le fournisseur a un modèle de réponse
            models = provider_config.get("models", {})
            response_model = models.get("response")
            
            # Si pas de modèle de réponse spécifique, essayer le modèle par défaut
            if not response_model:
                response_model = models.get("default")
            
            if response_model:
                # Récupérer les paramètres du fournisseur
                params = provider_config.get("parameters", {}).copy()
                # Ajouter l'URL de base si spécifiée
                if "base_url" in provider_config:
                    params["base_url"] = provider_config["base_url"]
                # Obtenir la variable d'environnement pour la clé API
                api_key_env = provider_config.get("api_key_env")
                if api_key_env:
                    params["api_key_env"] = api_key_env
                
                return p, response_model, params
        
        # Fallback sur OpenAI
        return "openai", "gpt-3.5-turbo-0125", {"api_key_env": "OPENAI_API_KEY"}
    
    def get_assistant_personality(self) -> Dict[str, Any]:
        """
        Retourne la configuration de personnalité de l'assistant
        
        Returns:
            Configuration de personnalité
        """
        # Récupérer la configuration de personnalité ou utiliser les valeurs par défaut
        default_personality = {
            "name": "Expert OHADA",
            "expertise": "comptabilité et normes SYSCOHADA",
            "region": "zone OHADA (Afrique)",
            "language": "fr",
            "tone": "professionnel"
        }
        
        personality = self.config.get("assistant_personality", default_personality)
        
        # S'assurer que toutes les clés nécessaires sont présentes
        for key, value in default_personality.items():
            if key not in personality:
                personality[key] = value
        
        return personality