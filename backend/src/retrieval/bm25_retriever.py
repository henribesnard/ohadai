"""
Module de recherche BM25 pour le système OHADA Expert-Comptable.
Responsable de l'indexation et de la recherche BM25.
"""

import os
import pickle
import logging
import time
import concurrent.futures
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import nltk
from nltk.tokenize import word_tokenize
from rank_bm25 import BM25Okapi
import numpy as np

# Configurer NLTK
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

# Configuration du logging
logger = logging.getLogger("ohada_bm25_retriever")

class BM25Retriever:
    """Système de recherche BM25 pour les documents OHADA"""
    
    def __init__(self, cache_dir: Path = Path("./data/bm25_cache")):
        """
        Initialise le retrieveur BM25
        
        Args:
            cache_dir: Répertoire pour le cache des index BM25
        """
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.bm25_cache = {}  # Cache des index BM25 en mémoire
        self.document_cache = {}  # Cache des documents
    
    def get_or_create_index(self, collection_name: str, documents_provider) -> Tuple[Optional[BM25Okapi], Dict[int, Dict[str, Any]]]:
        """
        Récupère ou crée un index BM25 pour une collection
        
        Args:
            collection_name: Nom de la collection
            documents_provider: Fonction qui retourne les documents (id, text, metadata)
            
        Returns:
            Tuple (index BM25, mapping des documents)
        """
        # Vérifier si l'index existe déjà en mémoire
        if collection_name in self.bm25_cache:
            return (self.bm25_cache[collection_name]["index"], 
                    self.bm25_cache[collection_name]["mapping"])
        
        # Vérifier s'il existe un index sauvegardé sur disque
        cache_file = self.cache_dir / f"{collection_name}_bm25_index.pkl"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    cached_data = pickle.load(f)
                    self.bm25_cache[collection_name] = cached_data
                    logger.info(f"Index BM25 chargé depuis le cache pour la collection {collection_name}")
                    return cached_data["index"], cached_data["mapping"]
            except Exception as e:
                logger.error(f"Erreur lors du chargement de l'index BM25 depuis le cache: {e}")
        
        # Récupérer tous les documents de la collection via le provider
        try:
            documents = documents_provider(collection_name)
            
            if not documents:
                logger.warning(f"Aucun document fourni pour la collection {collection_name}")
                return None, {}
            
            # Tokeniser les documents pour BM25
            tokenized_docs = []
            doc_mapping = {}
            
            # Utiliser un ThreadPoolExecutor pour paralléliser la tokenisation
            with concurrent.futures.ThreadPoolExecutor() as executor:
                # Tokeniser tous les documents
                tokenize_futures = [
                    executor.submit(word_tokenize, doc["text"].lower())
                    for doc in documents
                ]
                
                # Récupérer les résultats
                for i, future in enumerate(concurrent.futures.as_completed(tokenize_futures)):
                    try:
                        tokens = future.result()
                        tokenized_docs.append(tokens)
                        
                        # Garder la correspondance entre l'index BM25 et le document
                        doc_mapping[i] = documents[i]
                        
                        # Mettre en cache le document pour une récupération rapide
                        self.document_cache[documents[i]["id"]] = {
                            "text": documents[i]["text"],
                            "metadata": documents[i]["metadata"]
                        }
                    except Exception as e:
                        logger.error(f"Erreur lors de la tokenisation du document {i}: {e}")
            
            # Créer l'index BM25
            logger.info(f"Création de l'index BM25 pour la collection {collection_name} avec {len(tokenized_docs)} documents")
            bm25_index = BM25Okapi(tokenized_docs)
            
            # Mettre en cache l'index et le mapping
            self.bm25_cache[collection_name] = {
                "index": bm25_index,
                "mapping": doc_mapping,
                "last_updated": time.time()
            }
            
            # Sauvegarder l'index dans le cache
            try:
                with open(cache_file, 'wb') as f:
                    pickle.dump(self.bm25_cache[collection_name], f)
                logger.info(f"Index BM25 sauvegardé dans le cache pour la collection {collection_name}")
            except Exception as e:
                logger.error(f"Erreur lors de la sauvegarde de l'index BM25 dans le cache: {e}")
            
            return bm25_index, doc_mapping
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de l'index BM25 pour {collection_name}: {e}")
            return None, {}
    
    def search(self, collection_name: str, query: str, filter_dict: Dict, 
              n_results: int, documents_provider=None) -> List[Dict[str, Any]]:
        """
        Effectue une recherche BM25 dans une collection
        
        Args:
            collection_name: Nom de la collection
            query: Texte de la requête
            filter_dict: Filtres à appliquer
            n_results: Nombre de résultats à retourner
            documents_provider: Fonction qui retourne les documents (optionnel)
            
        Returns:
            Liste des candidats BM25
        """
        candidates = []
        
        bm25_index, doc_mapping = self.get_or_create_index(collection_name, documents_provider)
        if bm25_index:
            logger.info(f"Exécution de la recherche BM25 dans {collection_name}")
            # Tokeniser la requête avec NLTK
            tokenized_query = word_tokenize(query.lower())
            
            # Récupérer les scores BM25
            bm25_scores = bm25_index.get_scores(tokenized_query)
            
            # Récupérer les meilleurs résultats BM25
            bm25_top_indices = np.argsort(bm25_scores)[-n_results*2:][::-1]  # Doubler pour avoir plus de candidats
            
            # Ajouter les candidats BM25
            for idx in bm25_top_indices:
                if bm25_scores[idx] > 0:  # Ignorer les documents sans correspondance
                    doc_info = doc_mapping[idx]
                    
                    # Appliquer les filtres
                    if filter_dict:
                        skip = False
                        for key, value in filter_dict.items():
                            if key not in doc_info["metadata"] or doc_info["metadata"][key] != value:
                                skip = True
                                break
                        if skip:
                            continue
                    
                    # Normaliser le score BM25 entre 0 et 1
                    normalized_bm25_score = bm25_scores[idx] / max(bm25_scores) if max(bm25_scores) > 0 else 0
                    
                    # Ajouter à la liste des candidats
                    candidates.append({
                        "document_id": doc_info["id"],
                        "text": doc_info["text"],
                        "metadata": doc_info["metadata"],
                        "bm25_score": normalized_bm25_score,
                        "vector_score": 0.0,
                        "combined_score": normalized_bm25_score * 0.5  # Score initial (sera mis à jour)
                    })
        
        return candidates