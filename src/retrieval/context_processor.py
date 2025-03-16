"""
Module de traitement du contexte pour le système OHADA Expert-Comptable.
Responsable de la préparation et du résumé du contexte pour les LLMs.
"""

import logging
from typing import List, Dict, Any

# Configuration du logging
logger = logging.getLogger("ohada_context_processor")

class ContextProcessor:
    """Traitement du contexte pour les réponses OHADA"""
    
    def __init__(self):
        """Initialise le processeur de contexte"""
        pass
    
    def summarize_context(self, query: str, search_results: List[Dict[str, Any]], 
                         max_tokens: int = 1800) -> str:
        """
        Crée un contexte résumé à partir des résultats de recherche
        
        Args:
            query: Requête de l'utilisateur
            search_results: Résultats de la recherche
            max_tokens: Nombre maximum de tokens approximatif
            
        Returns:
            Contexte résumé
        """
        if not search_results:
            return ""
        
        # Construire un contexte contenant les extraits les plus pertinents
        context_parts = []
        
        # Estimation grossière des tokens (environ 4 caractères par token)
        current_length = 0
        max_chars = max_tokens * 4
        
        for i, result in enumerate(search_results):
            # Extraire les métadonnées essentielles
            metadata_str = ""
            if result["metadata"].get('title'):
                metadata_str += f"Titre: {result['metadata'].get('title')}\n"
            
            if result["metadata"].get('document_type'):
                metadata_str += f"Type: {result['metadata'].get('document_type')}"
                
                if result["metadata"].get('partie'):
                    metadata_str += f", Partie: {result['metadata'].get('partie')}"
                
                if result["metadata"].get('chapitre'):
                    metadata_str += f", Chapitre: {result['metadata'].get('chapitre')}"
                
                metadata_str += "\n"
            
            # Calcul approximatif des caractères
            entry_text = f"Document {i+1} (score: {result['relevance_score']:.2f}):\n{metadata_str}\n{result['text']}\n\n"
            entry_length = len(entry_text)
            
            # Vérifier si on dépasse la limite
            if current_length + entry_length > max_chars:
                # Si on ne peut pas ajouter le document complet, on extrait un passage pertinent
                if i < 2:  # Toujours inclure au moins les 2 premiers documents
                    # Extraire un passage pertinent du texte
                    sentences = result['text'].split('.')
                    passage = ""
                    passage_length = 0
                    remaining_chars = max_chars - current_length - len(metadata_str) - 50
                    
                    for sentence in sentences:
                        if passage_length + len(sentence) < remaining_chars:
                            passage += sentence + ". "
                            passage_length += len(sentence) + 2
                        else:
                            break
                    
                    # Ajouter le passage pertinent
                    context_parts.append(f"Document {i+1} (score: {result['relevance_score']:.2f}):\n{metadata_str}\n{passage}\n\n")
                    current_length += len(metadata_str) + passage_length + 50
                    
                # Si ce n'est pas un des premiers documents, on s'arrête
                break
            else:
                # Ajouter le document complet
                context_parts.append(entry_text)
                current_length += entry_length
        
        # Joindre les parties du contexte
        context = "".join(context_parts)
        
        logger.info(f"Contexte résumé généré: {len(context)} caractères")
        return context
    
    def prepare_sources(self, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Prépare les sources pour l'inclusion dans la réponse
        
        Args:
            search_results: Résultats de la recherche
            
        Returns:
            Liste des sources formatées
        """
        sources = []
        for result in search_results:
            # Extraire un aperçu du texte (premiers 150 caractères)
            preview = result["text"][:150] + "..." if len(result["text"]) > 150 else result["text"]
            
            sources.append({
                "document_id": result["document_id"],
                "metadata": result["metadata"],
                "relevance_score": result["relevance_score"],
                "preview": preview
            })
        
        return sources