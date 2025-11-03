"""
Module de génération de réponses en streaming pour le système OHADA Expert-Comptable.
Responsable de la génération des réponses en mode streaming.
"""

import logging
import asyncio
from typing import Dict, Any, AsyncGenerator, Callable

# Configuration du logging
logger = logging.getLogger("ohada_streaming_generator")

class StreamingGenerator:
    """Générateur de réponses en streaming pour les requêtes OHADA"""
    
    def __init__(self, llm_client, context_processor):
        """
        Initialise le générateur de réponses en streaming
        
        Args:
            llm_client: Client LLM avec support du streaming
            context_processor: Processeur de contexte pour résumer les résultats
        """
        self.llm_client = llm_client
        self.context_processor = context_processor
    
    async def search_and_stream_response(self, query: str, search_results: list, 
                                       partie: int = None, chapitre: int = None, 
                                       n_results: int = 5, include_sources: bool = False,
                                       callback: Callable = None) -> Dict[str, Any]:
        """
        Recherche et génère une réponse en streaming
        
        Args:
            query: Requête de l'utilisateur
            search_results: Résultats de la recherche préalable
            partie: Numéro de partie (optionnel)
            chapitre: Numéro de chapitre (optionnel)
            n_results: Nombre de résultats à retourner
            include_sources: Inclure les sources dans la réponse
            callback: Fonction appelée avec chaque morceau de texte généré
            
        Returns:
            Dictionnaire contenant la réponse et les métadonnées
        """
        import time
        start_time = time.time()
        
        # Appeler le callback pour signaler la progression initiale
        if callback:
            await callback("search_complete", {
                "results_count": len(search_results)
            })
        
        # Étape 1: Résumé du contexte
        context_start = time.time()
        context = self.context_processor.summarize_context(
            query=query,
            search_results=search_results,
            max_tokens=1800
        )
        context_time = time.time() - context_start
        
        # Appeler le callback pour signaler la progression
        if callback:
            await callback("context_ready", {
                "context_time": context_time,
            })
        
        # Étape 2: Générer la réponse avec streaming
        generation_start = time.time()
        
        answer_parts = []
        
        # Système de prompt et prompt utilisateur
        system_prompt = "Vous êtes un expert-comptable spécialisé dans le plan comptable OHADA. N'utilisez jamais de notation mathématique LaTeX ou de formules entre crochets."
        user_prompt = f"""
        Question: {query}
        
        Contexte:
        {context}
        
        Répondez à la question de manière claire, précise et structurée en vous basant sur le contexte fourni.
        """
        
        # Générer la réponse avec streaming
        from src.utils.ohada_streaming import generate_streaming_response
        
        async for chunk in generate_streaming_response(self.llm_client, system_prompt, user_prompt):
            answer_parts.append(chunk)
            
            # Appeler le callback avec le morceau de texte généré
            if callback:
                await callback("text_chunk", {"text": chunk})
        
        # Construire la réponse complète
        answer = "".join(answer_parts)
        generation_time = time.time() - generation_start
        
        # Préparer les sources si demandé
        sources = None
        if include_sources:
            sources = self.context_processor.prepare_sources(search_results)
        
        # Construire la réponse complète
        response = {
            "answer": answer,
            "sources": sources,
            "performance": {
                "context_time_seconds": context_time,
                "generation_time_seconds": generation_time,
                "total_time_seconds": time.time() - start_time
            }
        }
        
        # Appeler le callback pour signaler la fin
        if callback:
            await callback("complete", {
                "total_time": time.time() - start_time,
                "answer_length": len(answer)
            })
        
        return response

    async def stream_prompt_response(self, system_prompt: str, user_prompt: str):
        """
        Génère une réponse en streaming pour un prompt donné
        
        Args:
            system_prompt: Message système pour le LLM
            user_prompt: Message utilisateur pour le LLM
            
        Yields:
            Morceaux de texte de la réponse au fur et à mesure de la génération
        """
        from src.utils.ohada_streaming import generate_streaming_response
        
        async for chunk in generate_streaming_response(self.llm_client, system_prompt, user_prompt):
            yield chunk