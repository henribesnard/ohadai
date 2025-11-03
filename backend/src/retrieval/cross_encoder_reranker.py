"""
Module de reranking pour le système OHADA Expert-Comptable.
Responsable du reranking des résultats de recherche.
"""

import logging
from typing import List, Dict, Any
from sentence_transformers import CrossEncoder

# Configuration du logging
logger = logging.getLogger("ohada_cross_encoder_reranker")

class CrossEncoderReranker:
    """Système de reranking avec cross-encoder pour les résultats de recherche OHADA"""
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """
        Initialise le reranker cross-encoder
        
        Args:
            model_name: Nom du modèle cross-encoder à utiliser
        """
        self.model_name = model_name
        self.model = None
    
    def load_model(self):
        """Charge le modèle cross-encoder à la demande"""
        if self.model is not None:
            return self.model
            
        try:
            logger.info(f"Chargement du cross-encoder: {self.model_name}")
            self.model = CrossEncoder(self.model_name)
            logger.info(f"Cross-encoder {self.model_name} chargé avec succès")
            return self.model
        except Exception as e:
            logger.error(f"Erreur lors du chargement du cross-encoder: {e}")
            return None
    
    def rerank(self, query: str, candidates: List[Dict[str, Any]], top_k: int = None) -> List[Dict[str, Any]]:
        """
        Réordonne les candidats en utilisant le cross-encoder
        
        Args:
            query: Texte de la requête originale
            candidates: Liste des candidats à réordonner
            top_k: Nombre de candidats à considérer (ou None pour tous)
            
        Returns:
            Liste des candidats réordonnés avec scores mis à jour
        """
        if not candidates:
            return candidates
            
        # Limiter aux top_k candidats si demandé
        if top_k is not None and top_k < len(candidates):
            candidates_to_rerank = candidates[:top_k]
        else:
            candidates_to_rerank = candidates
        
        # Charger le cross-encoder à la demande
        cross_encoder = self.load_model()
        if not cross_encoder:
            logger.warning("Cross-encoder non disponible, pas de reranking")
            return candidates
        
        logger.info(f"Application du reranking avec cross-encoder sur {len(candidates_to_rerank)} candidats")
        
        # Préparer les paires (requête, passage) pour le cross-encoder
        pairs = [(query, doc["text"]) for doc in candidates_to_rerank]
        
        # Obtenir les scores du cross-encoder
        cross_scores = cross_encoder.predict(pairs)
        
        # Mettre à jour les scores
        for i, score in enumerate(cross_scores):
            if i < len(candidates_to_rerank):
                candidates_to_rerank[i]["cross_score"] = float(score)
                # Combinaison finale: 30% BM25, 30% vectoriel, 40% cross-encoder
                candidates_to_rerank[i]["final_score"] = (
                    candidates_to_rerank[i]["bm25_score"] * 0.3 +
                    candidates_to_rerank[i]["vector_score"] * 0.3 +
                    candidates_to_rerank[i]["cross_score"] * 0.4
                )
                # Mettre à jour le score combiné pour la compatibilité
                candidates_to_rerank[i]["combined_score"] = candidates_to_rerank[i]["final_score"]
                candidates_to_rerank[i]["relevance_score"] = candidates_to_rerank[i]["final_score"]
        
        # Réordonner les candidats traités
        candidates_to_rerank.sort(key=lambda x: x.get("final_score", x["combined_score"]), reverse=True)
        
        # Si on a traité tous les candidats, retourner la liste
        if top_k is None or top_k >= len(candidates):
            return candidates_to_rerank
        
        # Sinon, combiner les candidats réordonnés avec le reste non traité
        return candidates_to_rerank + candidates[top_k:]