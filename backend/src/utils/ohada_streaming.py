"""
Module de streaming pour les réponses des modèles de langage.
Fournit les fonctionnalités de streaming pour différents modèles (OpenAI, etc.)
"""

import os
import asyncio
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
from openai import AsyncOpenAI

# Import des modules internes
from src.config.ohada_config import LLMConfig

# Configuration du logging
logger = logging.getLogger("ohada_streaming")

class StreamingLLMClient:
    """Client pour le streaming des réponses des modèles de langage"""
    
    def __init__(self, config: LLMConfig):
        """
        Initialise le client streaming
        
        Args:
            config: Instance de LLMConfig
        """
        self.config = config
        self.clients = {}  # Cache pour les instances de clients async
    
    async def _get_async_client(self, provider: str, params: Dict[str, Any]) -> Optional[AsyncOpenAI]:
        """
        Obtient ou crée une instance client asynchrone pour un fournisseur
        
        Args:
            provider: Nom du fournisseur
            params: Paramètres du fournisseur
            
        Returns:
            Instance de client asynchrone ou None en cas d'erreur
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
        
        api_key = os.getenv(api_key_env)
        if not api_key:
            logger.warning(f"Variable d'environnement {api_key_env} non définie")
            return None
        
        # Obtenir l'URL de base (si spécifiée)
        base_url = params.pop("base_url", None)
        
        # Créer le client asynchrone
        try:
            client_params = {"api_key": api_key}
            if base_url:
                client_params["base_url"] = base_url
            
            client = AsyncOpenAI(**client_params)
            
            # Mettre en cache le client
            self.clients[provider] = client
            
            return client
            
        except Exception as e:
            logger.error(f"Erreur lors de la création du client asynchrone {provider}: {e}")
            return None
    
    async def generate_streaming_response(self, system_prompt: str, user_prompt: str, 
                                         max_tokens: int = None, temperature: float = None) -> AsyncGenerator[str, None]:
        """
        Génère une réponse en streaming en utilisant le modèle configuré
        
        Args:
            system_prompt: Prompt système
            user_prompt: Prompt utilisateur
            max_tokens: Nombre maximum de tokens (ou None pour utiliser la valeur configurée)
            temperature: Température (ou None pour utiliser la valeur configurée)
            
        Yields:
            Morceaux de la réponse générée
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
                # Préparer les paramètres pour le client
                client_params = {"api_key_env": api_key_env}
                if base_url:
                    client_params["base_url"] = base_url
                
                client = await self._get_async_client(provider, client_params)
                if not client:
                    continue
                
                # Créer un stream
                stream = await client.chat.completions.create(
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
                
                # Traiter le stream
                async for chunk in stream:
                    if chunk.choices and len(chunk.choices) > 0:
                        content = chunk.choices[0].delta.content
                        if content:
                            yield content
                
                # Réussi, sortir de la boucle
                return
                
            except Exception as e:
                logger.error(f"Erreur lors de la génération streaming avec {provider}/{response_model}: {e}")
                # Continue with the next provider
        
        # Si tous les fournisseurs échouent, générer un message d'erreur
        error_msg = "Erreur lors de la génération de réponse: tous les fournisseurs ont échoué"
        logger.error(error_msg)
        yield "Désolé, une erreur est survenue lors de la génération de la réponse. Veuillez vérifier vos clés API et réessayer ultérieurement."


async def generate_streaming_response(client: StreamingLLMClient, system_prompt: str, user_prompt: str, 
                                     max_tokens: int = None, temperature: float = None) -> AsyncGenerator[str, None]:
    """
    Fonction utilitaire pour générer une réponse en streaming
    
    Args:
        client: Instance de StreamingLLMClient
        system_prompt: Prompt système
        user_prompt: Prompt utilisateur
        max_tokens: Nombre maximum de tokens (ou None pour utiliser la valeur configurée)
        temperature: Température (ou None pour utiliser la valeur configurée)
        
    Yields:
        Morceaux de la réponse générée
    """
    async for chunk in client.generate_streaming_response(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_tokens=max_tokens,
        temperature=temperature
    ):
        yield chunk


# Exemple d'utilisation
if __name__ == "__main__":
    import asyncio
    from config.ohada_config import LLMConfig
    
    async def main():
        # Charger la configuration des modèles
        config = LLMConfig()
        
        # Initialiser le client streaming
        client = StreamingLLMClient(config)
        
        # Test de génération en streaming
        system_prompt = "Vous êtes un expert-comptable spécialisé dans le plan comptable OHADA."
        user_prompt = "Expliquez brièvement ce qu'est l'amortissement dégressif dans le SYSCOHADA."
        
        print("Génération de réponse en streaming...")
        async for chunk in client.generate_streaming_response(system_prompt, user_prompt):
            print(chunk, end="", flush=True)
        print("\n\nGénération terminée")
    
    asyncio.run(main())