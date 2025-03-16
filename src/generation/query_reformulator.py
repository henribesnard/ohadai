"""
Module de reformulation de requêtes pour le système OHADA Expert-Comptable.
Responsable de l'optimisation des requêtes pour la recherche.
"""

import logging
from typing import Optional

# Configuration du logging
logger = logging.getLogger("ohada_query_reformulator")

class QueryReformulator:
    """Reformulation des requêtes pour optimiser la recherche OHADA"""
    
    def __init__(self, llm_client):
        """
        Initialise le reformulateur de requêtes
        
        Args:
            llm_client: Client LLM pour la génération de texte
        """
        self.llm_client = llm_client
    
    def reformulate(self, query: str) -> str:
        """
        Reformule la requête pour améliorer la recherche
        
        Args:
            query: Requête originale
            
        Returns:
            Requête reformulée
        """
        # Pour les requêtes courtes (moins de 100 caractères), pas besoin de reformulation
        if len(query) < 100:
            return query
            
        # Utiliser le LLM pour reformuler la requête
        prompt = f"""
        Vous êtes un assistant spécialisé dans la recherche d'informations sur le plan comptable OHADA.
        Votre tâche est de reformuler la question suivante pour maximiser les chances de trouver 
        des informations pertinentes dans une base de données. Ajoutez des mots-clés pertinents,
        mais gardez la requête concise.
        
        Question originale: {query}
        
        Reformulation optimisée:
        """
        
        try:
            logger.info(f"Reformulation de la requête: {query}")
            reformulated = self.llm_client.generate_response(
                system_prompt="Reformulez la question pour optimiser la recherche dans le plan comptable OHADA.",
                user_prompt=prompt,
                max_tokens=100,
                temperature=0.3
            )
            
            # Nettoyer la reformulation
            reformulated = reformulated.strip()
            
            logger.info(f"Requête reformulée: {reformulated}")
            
            return reformulated if reformulated else query
        except Exception as e:
            logger.error(f"Erreur lors de la reformulation: {e}")
            return query