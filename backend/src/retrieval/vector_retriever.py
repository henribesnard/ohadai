"""
Module de recherche vectorielle pour le système OHADA Expert-Comptable.
Responsable de la recherche basée sur les embeddings.
"""

import logging
from typing import List, Dict, Any, Optional

# Configuration du logging
logger = logging.getLogger("ohada_vector_retriever")

class VectorRetriever:
    """Système de recherche vectorielle pour les documents OHADA"""
    
    def __init__(self, vector_db, embedding_cache=None, redis_cache=None):
        """
        Initialise le retrieveur vectoriel

        Args:
            vector_db: Instance de la base vectorielle
            embedding_cache: Cache d'embeddings local (optionnel)
            redis_cache: Cache Redis distribué (optionnel, OPTIMISATION PHASE 2)
        """
        self.vector_db = vector_db
        self.embedding_cache = embedding_cache or {}
        self.redis_cache = redis_cache  # Cache distribué pour embeddings

    def get_embedding(self, text: str, embedder) -> List[float]:
        """
        Récupère ou génère un embedding pour un texte.

        OPTIMISATION PHASE 2: Utilise Redis comme cache distribué en priorité,
        puis le cache local, puis génère un nouvel embedding si nécessaire.

        Cascade de cache:
        1. Cache Redis (partagé, ~1-2ms) ✓
        2. Cache local (mémoire, ~0.1ms) ✓
        3. Génération API OpenAI (réseau, ~50-150ms)

        Args:
            text: Texte à transformer en embedding
            embedder: Fonction ou objet qui génère des embeddings

        Returns:
            Vecteur d'embedding
        """
        # 1. Vérifier le cache Redis distribué en premier (OPTIMISATION)
        if self.redis_cache and self.redis_cache.enabled:
            cached_embedding = self.redis_cache.get_embedding(text)
            if cached_embedding:
                logger.debug(f"✓ Redis cache HIT pour embedding: {text[:50]}")
                # Mettre aussi en cache local pour accès ultra-rapide
                text_hash = hash(text)
                self.embedding_cache[text_hash] = cached_embedding
                return cached_embedding

        # 2. Vérifier le cache local
        text_hash = hash(text)

        if text_hash in self.embedding_cache:
            logger.debug(f"✓ Local cache HIT pour embedding: {text[:50]}")
            return self.embedding_cache[text_hash]

        # 3. Générer un nouvel embedding (LENT: ~50-150ms)
        logger.debug(f"Génération nouvel embedding pour: {text[:50]}")
        embedding = embedder(text)

        # 4. Mettre en cache (Redis + local)
        if self.redis_cache and self.redis_cache.enabled:
            self.redis_cache.set_embedding(text, embedding, ttl=86400)  # 24h

        self.embedding_cache[text_hash] = embedding

        # Limiter la taille du cache local (garder les 100 derniers embeddings)
        if len(self.embedding_cache) > 100:
            # Supprimer l'entrée la plus ancienne (FIFO)
            self.embedding_cache.pop(next(iter(self.embedding_cache)))

        return embedding
    
    def search(self, collection_name: str, query_embedding: List[float],
              filter_dict: Dict, n_results: int) -> List[Dict[str, Any]]:
        """
        Effectue une recherche vectorielle dans une collection

        Args:
            collection_name: Nom de la collection
            query_embedding: Embedding de la requête
            filter_dict: Filtres à appliquer
            n_results: Nombre de résultats à retourner

        Returns:
            Liste des candidats vectoriels
        """
        candidates = []

        try:
            logger.info(f"Exécution de la recherche vectorielle dans {collection_name}")

            # ADAPTATION: Accéder directement à ChromaDB au lieu de vector_db.collections
            import chromadb
            chroma_client = chromadb.PersistentClient(path="backend/chroma_db")
            collection = chroma_client.get_collection(collection_name)

            # Query directement sur la collection ChromaDB
            vector_results = collection.query(
                query_embeddings=[query_embedding],
                where=filter_dict if filter_dict else None,
                n_results=n_results*2  # Doubler pour avoir plus de candidats
            )
            
            if vector_results and 'ids' in vector_results:
                for i in range(len(vector_results['ids'][0])):
                    doc_id = vector_results['ids'][0][i]
                    text = vector_results['documents'][0][i]
                    metadata = vector_results['metadatas'][0][i]
                    distance = vector_results.get('distances', [[]])[0][i] if 'distances' in vector_results else 0.0
                    
                    # Convertir distance en score (1 - distance normalisée)
                    # Pour les mesures de cosinus, la distance est déjà entre 0 et 2
                    vector_score = 1.0 - (distance / 2.0) if distance else 1.0
                    
                    # Ajouter un nouveau candidat
                    candidates.append({
                        "document_id": doc_id,
                        "text": text,
                        "metadata": metadata,
                        "bm25_score": 0.0,
                        "vector_score": vector_score,
                        "combined_score": vector_score * 0.5  # Score initial
                    })
        except Exception as e:
            logger.error(f"Erreur lors de la recherche vectorielle dans {collection_name}: {e}")
        
        return candidates