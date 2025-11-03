"""
Module clients pour le système OHADA Expert-Comptable.
Fournit une interface unifiée pour interagir avec différents fournisseurs de modèles de langage.
Optimisé pour la performance avec les modèles d'embedding légers.
"""

import os
import time
import logging
from typing import List, Dict, Any, Optional, Union
from openai import OpenAI, AsyncOpenAI

# Import des modules internes
from src.config.ohada_config import LLMConfig
from src.vector_db.ohada_vector_db_structure import OhadaEmbedder

# Configuration du logging
logger = logging.getLogger("ohada_clients")

class LLMClient:
    """Client pour interagir avec différents modèles de langage"""
    
    def __init__(self, config: LLMConfig):
        """
        Initialise le client LLM
        
        Args:
            config: Instance de LLMConfig
        """
        self.config = config
        self.clients = {}  # Cache pour les instances de clients
        
        # Initialiser l'embedder dès maintenant pour gagner du temps lors des requêtes
        # (utilisation du pattern Singleton dans OhadaEmbedder)
        try:
            # Détecter l'environnement
            environment = os.getenv("OHADA_ENV", "test")

            # Récupérer le modèle d'embedding configuré
            embedding_provider, model_name, params = self.config.get_embedding_model()
            dimensions = params.get("dimensions", 1024)  # 1024 pour BGE-M3

            if embedding_provider == "local_embedding":
                logger.info(f"Préchargement de l'embedder local {model_name} (env: {environment})...")
                self.local_embedder = OhadaEmbedder(model_name=model_name)
                logger.info(f"Embedder local {model_name} préchargé avec succès (dim: {dimensions})")
        except Exception as e:
            logger.error(f"Erreur lors du préchargement de l'embedder local: {e}")
            logger.info("L'embedder sera chargé à la demande")
    
    def _get_api_key(self, env_var: str) -> str:
        """
        Récupère une clé API depuis une variable d'environnement
        
        Args:
            env_var: Nom de la variable d'environnement
            
        Returns:
            La clé API ou None si non trouvée
        """
        api_key = os.getenv(env_var)
        if not api_key:
            logger.warning(f"Variable d'environnement {env_var} non définie")
        return api_key
    
    def _get_client(self, provider: str, params: Dict[str, Any]) -> Optional[OpenAI]:
        """
        Obtient ou crée une instance client pour un fournisseur
        
        Args:
            provider: Nom du fournisseur
            params: Paramètres du fournisseur
            
        Returns:
            Instance de client ou None en cas d'erreur
        """
        # Vérifier si le client existe déjà en cache
        if provider in self.clients:
            return self.clients[provider]
        
        # Vérifier les modèles locaux (n'ont pas besoin de client API)
        if params.get("local", False):
            return None
        
        # Obtenir la clé API
        api_key_env = params.pop("api_key_env", None)
        if not api_key_env:
            logger.error(f"Variable d'environnement pour la clé API non spécifiée pour {provider}")
            return None
        
        api_key = self._get_api_key(api_key_env)
        if not api_key:
            return None
        
        # Obtenir l'URL de base (si spécifiée)
        base_url = params.pop("base_url", None)
        
        # Créer le client
        try:
            client_params = {"api_key": api_key}
            if base_url:
                client_params["base_url"] = base_url
            
            client = OpenAI(**client_params)
            
            # Mettre en cache le client
            self.clients[provider] = client
            
            return client
            
        except Exception as e:
            logger.error(f"Erreur lors de la création du client {provider}: {e}")
            return None
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Génère un embedding pour un texte en utilisant le modèle configuré
        
        Args:
            text: Texte à transformer en embedding
            
        Returns:
            Vecteur d'embedding ou liste vide en cas d'erreur
        """
        start_time = time.time()
        
        # Déterminer l'environnement actuel
        environment = os.getenv("OHADA_ENV", "test")
        
        # Utiliser la liste de priorité pour les embeddings
        provider_list = self.config.get_embedding_provider_list()
        
        # Essayer chaque fournisseur dans l'ordre
        for provider in provider_list:
            provider_config = self.config.get_provider_config(provider)
            if not provider_config:
                continue
            
            models = provider_config.get("models", {})
            embedding_model = models.get("embedding")
            
            if not embedding_model:
                embedding_model = models.get("default")
                if not embedding_model:
                    continue
            
            params = provider_config.get("parameters", {}).copy()

            # Vérifier si c'est un modèle local (le flag "local" est au niveau provider, pas dans parameters)
            if provider_config.get("local", False):
                try:
                    # Utiliser le modèle configuré (pas hardcodé)
                    logger.info(f"Génération d'embedding avec modèle local: {embedding_model} (env: {environment})")

                    # Utiliser le pattern Singleton dans OhadaEmbedder
                    embedder = OhadaEmbedder(model_name=embedding_model)
                    embedding = embedder.generate_embedding(text)
                    
                    elapsed = time.time() - start_time
                    logger.info(f"Embedding généré avec modèle local en {elapsed:.2f} secondes")
                    
                    return embedding
                    
                except Exception as e:
                    logger.error(f"Erreur lors de la génération d'embedding avec modèle local {embedding_model}: {e}")
                    continue
            
            # Pour les modèles d'API comme OpenAI
            api_key_env = provider_config.get("api_key_env")
            dimensions = params.pop("dimensions", 1536)
            base_url = provider_config.get("base_url")
            
            try:
                # Préparer les paramètres pour le client
                client_params = {"api_key_env": api_key_env}
                if base_url:
                    client_params["base_url"] = base_url
                
                client = self._get_client(provider, client_params)
                if not client:
                    continue
                
                logger.info(f"Génération d'embedding avec API {provider}/{embedding_model}")
                
                response = client.embeddings.create(
                    model=embedding_model,
                    input=[text],
                    dimensions=dimensions
                )
                
                elapsed = time.time() - start_time
                logger.info(f"Embedding généré en {elapsed:.2f} secondes")
                
                return response.data[0].embedding
                
            except Exception as e:
                logger.error(f"Erreur lors de la génération d'embedding avec {provider}/{embedding_model}: {e}")
                continue
        
        # Si tous les fournisseurs échouent, retourner un vecteur vide
        logger.error("Tous les fournisseurs d'embedding ont échoué. Retour d'un vecteur vide.")

        # Récupérer la dimension configurée (BGE-M3 = 1024, text-embedding-3-small = 1536)
        _, _, embedding_params = self.config.get_embedding_model()
        default_dimension = embedding_params.get("dimensions", 1024)

        return [0.0] * default_dimension
    
    async def generate_response_streaming(self, system_prompt: str, user_prompt: str, 
                                       max_tokens: int = None, temperature: float = None):
        """
        Génère une réponse en streaming en utilisant le modèle configuré
        
        Args:
            system_prompt: Prompt système
            user_prompt: Prompt utilisateur
            max_tokens: Nombre maximum de tokens (ou None pour utiliser la valeur configurée)
            temperature: Température (ou None pour utiliser la valeur configurée)
            
        Returns:
            Un objet StreamResponse pour itérer sur les chunks de réponse
        """
        # Utiliser la liste de priorité pour les réponses
        provider_list = self.config.get_provider_list()
        
        # Essayer chaque fournisseur dans l'ordre
        for provider in provider_list:
            provider_config = self.config.get_provider_config(provider)
            if not provider_config:
                continue
            
            models = provider_config.get("models", {})
            response_model = models.get("response")
            
            if not response_model:
                response_model = models.get("default")
                if not response_model:
                    continue
            
            params = provider_config.get("parameters", {}).copy()
            
            # Extraire et supprimer api_key_env des params pour ne pas le passer à l'API
            api_key_env = provider_config.get("api_key_env")
            base_url = provider_config.get("base_url")
            
            # Extraire les paramètres ou utiliser ceux fournis
            if max_tokens is None:
                max_tokens = params.pop("max_tokens", 1000)
            else:
                params.pop("max_tokens", None)
                
            if temperature is None:
                temperature = params.pop("temperature", 0.3)
            else:
                params.pop("temperature", None)
            
            logger.info(f"Génération de réponse streaming avec {provider}/{response_model}")
            
            try:
                # Créer un client asynchrone
                api_key = self._get_api_key(api_key_env)
                if not api_key:
                    continue
                    
                client_params = {"api_key": api_key}
                if base_url:
                    client_params["base_url"] = base_url
                    
                async_client = AsyncOpenAI(**client_params)
                
                # Créer le stream
                stream = await async_client.chat.completions.create(
                    model=response_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True,
                    **params  # Autres paramètres spécifiques au fournisseur
                )
                
                return stream
                    
            except Exception as e:
                logger.error(f"Erreur lors de la génération de réponse streaming avec {provider}/{response_model}: {e}")
                continue
        
        # Si tous les fournisseurs échouent, lever une exception
        error_msg = "Erreur lors de la génération de réponse streaming: tous les fournisseurs ont échoué"
        logger.error(error_msg)
        raise Exception(error_msg)

    def generate_response(self, system_prompt: str, user_prompt: str, 
                         max_tokens: int = None, temperature: float = None) -> str:
        """
        Génère une réponse en utilisant le modèle configuré
        
        Args:
            system_prompt: Prompt système
            user_prompt: Prompt utilisateur
            max_tokens: Nombre maximum de tokens (ou None pour utiliser la valeur configurée)
            temperature: Température (ou None pour utiliser la valeur configurée)
            
        Returns:
            Réponse générée ou message d'erreur
        """
        start_time = time.time()
        
        # Utiliser la liste de priorité pour les réponses
        provider_list = self.config.get_provider_list()
        
        # Essayer chaque fournisseur dans l'ordre
        for provider in provider_list:
            provider_config = self.config.get_provider_config(provider)
            if not provider_config:
                continue
            
            models = provider_config.get("models", {})
            response_model = models.get("response")
            
            if not response_model:
                response_model = models.get("default")
                if not response_model:
                    continue
            
            params = provider_config.get("parameters", {}).copy()
            
            # Extraire et supprimer api_key_env des params pour ne pas le passer à l'API
            api_key_env = provider_config.get("api_key_env")
            base_url = provider_config.get("base_url")
            
            # Extraire les paramètres ou utiliser ceux fournis
            if max_tokens is None:
                max_tokens = params.pop("max_tokens", 1000)
            else:
                params.pop("max_tokens", None)
                
            if temperature is None:
                temperature = params.pop("temperature", 0.3)
            else:
                params.pop("temperature", None)
            
            logger.info(f"Génération de réponse avec {provider}/{response_model}")
            
            try:
                # Préparer les paramètres pour le client
                client_params = {"api_key_env": api_key_env}
                if base_url:
                    client_params["base_url"] = base_url
                
                client = self._get_client(provider, client_params)
                if not client:
                    continue
                
                response = client.chat.completions.create(
                    model=response_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **params  # Autres paramètres spécifiques au fournisseur
                )
                
                elapsed = time.time() - start_time
                logger.info(f"Réponse générée en {elapsed:.2f} secondes")
                
                return response.choices[0].message.content
                
            except Exception as e:
                logger.error(f"Erreur lors de la génération de réponse avec {provider}/{response_model}: {e}")
                continue
        
        # Si tous les fournisseurs échouent, retourner un message d'erreur
        error_msg = "Erreur lors de la génération de réponse: tous les fournisseurs ont échoué"
        logger.error(error_msg)
        return f"Désolé, une erreur est survenue lors de la génération de la réponse. Veuillez vérifier vos clés API et réessayer ultérieurement."