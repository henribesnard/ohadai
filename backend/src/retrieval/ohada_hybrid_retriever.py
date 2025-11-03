"""
Module principal de récupération hybride pour le système OHADA Expert-Comptable.
Coordonne les différents composants de recherche, reranking et génération.
"""

import os
import time
import logging
import concurrent.futures
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union, Callable, AsyncGenerator

# Configuration du logging
logger = logging.getLogger("ohada_hybrid_retriever")

class OhadaHybridRetriever:
   """Système de récupération hybride pour la base de connaissances OHADA"""
   
   def __init__(self, vector_db, llm_config=None, cross_encoder_model="cross-encoder/ms-marco-MiniLM-L-6-v2", enable_postgres_enrichment=True):
       """
       Initialise le système de récupération hybride

       Args:
           vector_db: Instance de la base vectorielle
           llm_config: Configuration des modèles de langage
           cross_encoder_model: Modèle de reranking à utiliser
           enable_postgres_enrichment: Enable PostgreSQL metadata enrichment (default: True)
       """
       # Import à l'intérieur pour éviter les dépendances circulaires
       from src.utils.ohada_clients import LLMClient
       from src.config.ohada_config import LLMConfig
       from src.retrieval.bm25_retriever import BM25Retriever
       from src.retrieval.vector_retriever import VectorRetriever
       from src.retrieval.cross_encoder_reranker import CrossEncoderReranker
       from src.retrieval.context_processor import ContextProcessor
       from src.generation.query_reformulator import QueryReformulator
       from src.generation.response_generator import ResponseGenerator
       from src.generation.streaming_generator import StreamingGenerator
       from src.utils.ohada_cache import EmbeddingCache

       # Configuration
       self.vector_db = vector_db
       self.llm_config = llm_config if llm_config else LLMConfig()
       self.llm_client = LLMClient(self.llm_config)
       self.enable_postgres_enrichment = enable_postgres_enrichment

       # Cache d'embeddings
       self.embedding_cache = EmbeddingCache()

       # Initialiser les sous-systèmes
       self.bm25_retriever = BM25Retriever()
       self.vector_retriever = VectorRetriever(vector_db, self.embedding_cache)
       self.reranker = CrossEncoderReranker(cross_encoder_model)
       self.context_processor = ContextProcessor()
       self.query_reformulator = QueryReformulator(self.llm_client)
       self.response_generator = ResponseGenerator(self.llm_client)
       self.streaming_generator = StreamingGenerator(self.llm_client, self.context_processor)

       # PostgreSQL metadata enricher (if enabled and available)
       self.metadata_enricher = None
       if self.enable_postgres_enrichment:
           try:
               # Check if we're in backend context (PostgreSQL available)
               import sys
               from pathlib import Path
               backend_path = Path(__file__).parent.parent.parent / "backend"
               if backend_path.exists():
                   sys.path.insert(0, str(backend_path))

               from backend.src.retrieval.postgres_metadata_enricher import PostgresMetadataEnricher
               self.metadata_enricher = PostgresMetadataEnricher()
               logger.info("PostgreSQL metadata enrichment enabled")
           except Exception as e:
               logger.warning(f"PostgreSQL metadata enrichment not available: {e}")
               self.enable_postgres_enrichment = False
   
   def _get_document_provider(self, collection_name: str):
       """
       Crée une fonction fournisseur de documents pour BM25

       Args:
           collection_name: Nom de la collection

       Returns:
           Fonction qui fournit les documents
       """
       def provider(coll_name=None):
           # ADAPTATION: Accéder directement au client ChromaDB
           # au lieu de passer par vector_db.collections
           try:
               import chromadb
               # Utiliser le même chemin que l'ingestion
               chroma_client = chromadb.PersistentClient(path="chroma_db")
               collection = chroma_client.get_collection(coll_name or collection_name)

               # Récupérer tous les documents (limité pour performance)
               results = collection.get(
                   include=["documents", "metadatas"],
                   limit=10000  # Limiter pour éviter les problèmes de mémoire
               )

               if not results or "documents" not in results or not results["documents"]:
                   logger.warning(f"Aucun document trouvé dans la collection {coll_name or collection_name}")
                   return []

               # Construire une liste de documents structurés
               documents = []
               for i in range(len(results["ids"])):
                   documents.append({
                       "id": results["ids"][i],
                       "text": results["documents"][i],
                       "metadata": results["metadatas"][i]
                   })

               logger.info(f"Récupéré {len(documents)} documents de {coll_name or collection_name}")
               return documents

           except Exception as e:
               logger.error(f"Erreur lors de la récupération des documents: {e}")
               return []

       return  lambda _=None: provider()
   
   def determine_search_collections(self, query: str, collection_name: str = None,
                                    partie: int = None) -> List[str]:
       """
       Détermine les collections à utiliser pour la recherche en fonction de la requête

       Args:
           query: Texte de la requête
           collection_name: Nom de collection explicite (prioritaire)
           partie: Numéro de partie (optionnel)

       Returns:
           Liste des collections à interroger
       """
       # ADAPTATION: Utiliser la collection unique ohada_documents
       # qui contient tous les chunks ingérés avec BGE-M3
       if collection_name:
           return [collection_name]

       # Toujours utiliser ohada_documents (collection unique avec tous les chunks)
       return ["ohada_documents"]
   
   def search_hybrid(self, query: str, collection_name: str = None, partie: int = None,
                    chapitre: int = None, n_results: int = 10, rerank: bool = True) -> List[Dict[str, Any]]:
       """
       Effectue une recherche hybride (BM25 + vectorielle) avec reranking optionnel
       
       Args:
           query: Texte de la requête
           collection_name: Nom de la collection à interroger
           partie: Numéro de partie (optionnel)
           chapitre: Numéro de chapitre (optionnel)
           n_results: Nombre de résultats à retourner
           rerank: Appliquer le reranking avec cross-encoder
           
       Returns:
           Liste des résultats triés par pertinence
       """
       start_time = time.time()
       
       # Déterminer les collections à utiliser
       collections = self.determine_search_collections(query, collection_name, partie)
       
       # Initialiser les variables
       all_candidates = []
       
       # Exécuter les recherches BM25 et vectorielle en parallèle
       with concurrent.futures.ThreadPoolExecutor() as executor:
           futures = []
           
           # Générer l'embedding de la requête (pour la recherche vectorielle)
           embedding_future = executor.submit(
               self.vector_retriever.get_embedding, 
               query, 
               self.llm_client.generate_embedding
           )
           
           # Construire le filtre
           filter_dict = {}
           if partie:
               filter_dict["partie"] = partie
           if chapitre:
               filter_dict["chapitre"] = chapitre
           
           # Lancer la recherche BM25 pour chaque collection
           for coll in collections:
               doc_provider = self._get_document_provider(coll)
               futures.append(
                   executor.submit(
                       self.bm25_retriever.search, 
                       coll, 
                       query, 
                       filter_dict, 
                       n_results,
                       doc_provider
                   )
               )
           
           # Attendre l'embedding
           query_embedding = embedding_future.result()
           
           # Lancer la recherche vectorielle pour chaque collection
           for coll in collections:
               futures.append(
                   executor.submit(
                       self.vector_retriever.search, 
                       coll, 
                       query_embedding, 
                       filter_dict, 
                       n_results
                   )
               )
           
           # Récupérer tous les résultats
           for future in concurrent.futures.as_completed(futures):
               candidates = future.result()
               if candidates:
                   all_candidates.extend(candidates)
       
       # Déduplication des résultats par ID de document
       unique_candidates = {}
       for candidate in all_candidates:
           doc_id = candidate["document_id"]
           if doc_id in unique_candidates:
               # Prendre le meilleur score pour chaque type
               unique_candidates[doc_id]["bm25_score"] = max(
                   unique_candidates[doc_id]["bm25_score"],
                   candidate["bm25_score"]
               )
               unique_candidates[doc_id]["vector_score"] = max(
                   unique_candidates[doc_id]["vector_score"],
                   candidate["vector_score"]
               )
               # Recalculer le score combiné
               unique_candidates[doc_id]["combined_score"] = (
                   unique_candidates[doc_id]["bm25_score"] * 0.5 + 
                   unique_candidates[doc_id]["vector_score"] * 0.5
               )
           else:
               unique_candidates[doc_id] = candidate
       
       # Convertir en liste et trier par score combiné
       candidates = list(unique_candidates.values())
       
       # Boosting des documents selon le type
       for candidate in candidates:
           metadata = candidate.get("metadata", {})
           document_type = metadata.get("document_type", "")
           
           # Booster les documents pertinents selon le contexte de la requête
           if "traité" in query.lower() and "presentation_ohada" in document_type:
               candidate["combined_score"] *= 1.5
           
           # Booster les chapitres si la requête concerne le plan comptable
           comptable_keywords = ["compte", "comptable", "bilan", "syscohada", "journal"]
           if any(kw in query.lower() for kw in comptable_keywords) and document_type == "chapitre":
               candidate["combined_score"] *= 1.2
       
       # Trier par score
       candidates.sort(key=lambda x: x["combined_score"], reverse=True)
       
       # Appliquer le reranking si demandé
       if rerank and candidates:
           # Limiter aux top_n pour le reranking
           candidates_to_rerank = candidates[:min(n_results * 2, len(candidates))]
           candidates = self.reranker.rerank(query, candidates_to_rerank)
       
       # Prendre les n_results meilleurs résultats
       results = candidates[:min(n_results, len(candidates))]

       # Ajouter une clé de score unique pour la compatibilité avec le code existant
       for result in results:
           result["relevance_score"] = result.get("final_score", result["combined_score"])

       # Enrich results with PostgreSQL metadata if available
       if self.metadata_enricher:
           try:
               results = self.metadata_enricher.enrich_search_results(results)
               logger.info("Search results enriched with PostgreSQL metadata")
           except Exception as e:
               logger.warning(f"Failed to enrich results with PostgreSQL metadata: {e}")

       elapsed = time.time() - start_time
       logger.info(f"Recherche hybride terminée en {elapsed:.2f} secondes, {len(results)} résultats trouvés")

       return results
   
   def search_only(self, query: str, partie: int = None,
                  chapitre: int = None, n_results: int = 5) -> List[Dict[str, Any]]:
       """
       Effectue uniquement la recherche sans générer de réponse
       
       Args:
           query: Requête de l'utilisateur
           partie: Numéro de partie (optionnel)
           chapitre: Numéro de chapitre (optionnel)
           n_results: Nombre de résultats à retourner
           
       Returns:
           Liste des résultats de recherche
       """
       # Reformulation de la requête
       reformulated_query = self.query_reformulator.reformulate(query)
       
       # Recherche hybride
       search_results = self.search_hybrid(
           query=reformulated_query,
           partie=partie,
           chapitre=chapitre,
           n_results=n_results,
           rerank=True
       )
       
       return search_results
   
   def search_ohada_knowledge(self, query: str, partie: int = None,
                             chapitre: int = None, section: int = None,
                             n_results: int = 5, include_sources: bool = False):
       """
       Point d'entrée principal pour rechercher des connaissances OHADA et générer une réponse
       
       Args:
           query: Requête de l'utilisateur
           partie: Numéro de partie (optionnel)
           chapitre: Numéro de chapitre (optionnel)
           section: Numéro de section (optionnel)
           n_results: Nombre de résultats à retourner
           include_sources: Inclure les sources dans la réponse
           
       Returns:
           Dictionnaire contenant la réponse et les métadonnées
       """
       start_time = time.time()
       
       # NOUVELLE PARTIE: Analyse d'intention avec LLM
       # Importer l'analyseur d'intention
       from src.generation.intent_classifier import LLMIntentAnalyzer
       
       # Récupérer la configuration de l'assistant
       assistant_config = self.llm_config.config.get("assistant_personality", {
           "name": "Expert OHADA",
           "expertise": "comptabilité et normes SYSCOHADA",
           "region": "zone OHADA (Afrique)"
       })
       
       # Initialiser l'analyseur d'intention
       intent_analyzer = LLMIntentAnalyzer(
           llm_client=self.llm_client,
           assistant_config=assistant_config
       )
       
       # Analyser l'intention de la requête
       intent, metadata = intent_analyzer.analyze_intent(query)
       logger.info(f"Intention détectée: {intent} (confidence: {metadata.get('confidence', 0)})")
       
       # Si ce n'est pas une demande technique, générer une réponse directe
       direct_response = intent_analyzer.generate_response(intent, metadata)
       if direct_response:
           logger.info(f"Réponse directe générée pour l'intention: {intent}")
           return {
               "answer": direct_response,
               "performance": {
                   "intent_analysis_time_seconds": time.time() - start_time,
                   "total_time_seconds": time.time() - start_time
               }
           }
       
       # PARTIE EXISTANTE: Pour les demandes techniques, continuer avec le processus normal
       # Étape 1: Reformulation de la requête (seulement pour les requêtes complexes)
       reformulation_start = time.time()
       reformulated_query = self.query_reformulator.reformulate(query)
       reformulation_time = time.time() - reformulation_start
       
       # Étape 2: Recherche hybride
       search_start = time.time()
       search_results = self.search_hybrid(
           query=reformulated_query,
           partie=partie,
           chapitre=chapitre,
           n_results=n_results,
           rerank=True
       )
       search_time = time.time() - search_start
       
       # Étape 3: Résumé du contexte
       context_start = time.time()
       context = self.context_processor.summarize_context(
           query=reformulated_query,
           search_results=search_results
       )
       context_time = time.time() - context_start
       
       # Étape 4: Analyse et génération de réponse
       generation_start = time.time()
       answer = self.response_generator.generate_response(query, context)
       generation_time = time.time() - generation_start
       
       # Construire la réponse
       response = {
           "answer": answer,
           "performance": {
               "reformulation_time_seconds": reformulation_time,
               "search_time_seconds": search_time,
               "context_time_seconds": context_time,
               "generation_time_seconds": generation_time,
               "total_time_seconds": time.time() - start_time
           }
       }
       
       # Inclure les sources si demandé
       if include_sources:
           response["sources"] = self.context_processor.prepare_sources(search_results)
       
       return response
   
   async def search_and_stream_response(self, query: str, partie: int = None,
                                      chapitre: int = None, n_results: int = 5,
                                      include_sources: bool = False,
                                      callback: Callable = None) -> Dict[str, Any]:
       """
       Recherche et génère une réponse en streaming
       
       Args:
           query: Requête de l'utilisateur
           partie: Numéro de partie (optionnel)
           chapitre: Numéro de chapitre (optionnel)
           n_results: Nombre de résultats à retourner
           include_sources: Inclure les sources dans la réponse
           callback: Fonction appelée avec chaque morceau de texte généré
           
       Returns:
           Dictionnaire contenant la réponse et les métadonnées
       """
       start_time = time.time()
       
       # NOUVELLE PARTIE: Analyse d'intention
       if callback:
           await callback("progress", {
               "status": "analyzing_intent", 
               "completion": 0.05
           })
           
       # Importer l'analyseur d'intention
       from src.generation.intent_classifier import LLMIntentAnalyzer
       
       # Récupérer la configuration de l'assistant
       assistant_config = self.llm_config.config.get("assistant_personality", {
           "name": "Expert OHADA",
           "expertise": "comptabilité et normes SYSCOHADA",
           "region": "zone OHADA (Afrique)"
       })
       
       # Initialiser l'analyseur d'intention
       intent_analyzer = LLMIntentAnalyzer(
           llm_client=self.llm_client,
           assistant_config=assistant_config
       )
       
       # Analyser l'intention de la requête
       intent, metadata = intent_analyzer.analyze_intent(query)
       logger.info(f"Intention détectée (streaming): {intent}, confidence: {metadata.get('confidence', 0)}")
       
       # Si ce n'est pas une demande technique, générer une réponse directe
       direct_response = intent_analyzer.generate_response(intent, metadata)
       
       if direct_response:
           if callback:
               await callback("progress", {
                   "status": "direct_response",
                   "completion": 0.5,
                   "intent": intent
               })
               
               # Simulation d'un streaming pour la réponse directe
               # Diviser la réponse en morceaux pour un streaming progressif
               import asyncio
               from src.utils.ohada_streaming import StreamingLLMClient
               
               # Envoyer la réponse en morceaux
               chunks = []
               chunk_size = max(10, len(direct_response) // 20)  # Environ 20 chunks
               
               for i in range(0, len(direct_response), chunk_size):
                   chunk = direct_response[i:i+chunk_size]
                   chunks.append(chunk)
                   
                   # Envoyer le chunk au client
                   await callback("chunk", {
                       "text": chunk,
                       "completion": 0.5 + (0.4 * (i / len(direct_response)))
                   })
                   
                   # Petite pause pour simuler une génération naturelle
                   await asyncio.sleep(0.05)
           
           # Réponse complète pour retour
           return {
               "answer": direct_response,
               "sources": None,
               "performance": {
                   "intent_analysis_time_seconds": time.time() - start_time,
                   "total_time_seconds": time.time() - start_time
               }
           }
       
       # Si c'est une demande technique, continuer avec le processus normal
       # Étape 1: Reformulation de la requête
       reformulation_start = time.time()
       reformulated_query = self.query_reformulator.reformulate(query)
       reformulation_time = time.time() - reformulation_start
       
       # Étape 2: Recherche hybride
       search_start = time.time()
       search_results = self.search_hybrid(
           query=reformulated_query,
           partie=partie,
           chapitre=chapitre,
           n_results=n_results,
           rerank=True
       )
       search_time = time.time() - search_start
       
       # Appeler le callback pour signaler la progression
       if callback:
           await callback("search_complete", {
               "search_time": search_time,
               "results_count": len(search_results)
           })
       
       # Étape 3: Résumé du contexte
       context_start = time.time()
       context = self.context_processor.summarize_context(
           query=reformulated_query,
           search_results=search_results
       )
       context_time = time.time() - context_start
       
       # Appeler le callback pour signaler la progression
       if callback:
           await callback("context_ready", {
               "context_time": context_time,
           })
       
       # Étape 4: Générer la réponse avec streaming
       # Utiliser le streaming_generator pour générer la réponse
       response = await self.streaming_generator.search_and_stream_response(
           query=query, 
           search_results=search_results,
           partie=partie,
           chapitre=chapitre,
           n_results=n_results,
           include_sources=include_sources,
           callback=callback
       )
       
       # Mettre à jour les métriques de performance
       response["performance"]["reformulation_time_seconds"] = reformulation_time
       response["performance"]["search_time_seconds"] = search_time
       response["performance"]["total_time_seconds"] = time.time() - start_time
       
       return response


def create_ohada_query_api(config_path: str = "./src/config") -> OhadaHybridRetriever:
   """
   Crée une instance de l'API de requête OHADA hybride
   
   Args:
       config_path: Chemin vers le répertoire de configuration
   
   Returns:
       Instance de OhadaHybridRetriever
   """
   # Import à l'intérieur pour éviter les dépendances circulaires
   from src.config.ohada_config import LLMConfig
   from src.vector_db.ohada_vector_db_structure import OhadaVectorDB
   
   # Charger la configuration des modèles
   llm_config = LLMConfig(config_path)

   # Récupérer le modèle d'embedding depuis la configuration
   embedding_provider, embedding_model, embedding_params = llm_config.get_embedding_model()
   environment = os.getenv("OHADA_ENV", "test")

   logger.info(f"Environnement {environment}: utilisation du modèle d'embedding {embedding_model} (provider: {embedding_provider})")

   # Initialiser la base de données vectorielle
   vector_db = OhadaVectorDB(embedding_model=embedding_model)
   
   # Créer le récupérateur hybride
   retriever = OhadaHybridRetriever(vector_db, llm_config)
   
   return retriever


if __name__ == "__main__":
   import argparse
   
   parser = argparse.ArgumentParser(description="Système de requête OHADA hybride")
   parser.add_argument("query", help="Requête ou question à traiter")
   parser.add_argument("--config", default="./src/config", 
                       help="Chemin vers le répertoire de configuration")
   parser.add_argument("--n_results", type=int, default=5, 
                       help="Nombre de résultats à retourner (par défaut: 5)")
   parser.add_argument("--partie", type=int, choices=[1, 2, 3, 4],
                       help="Filtrer par numéro de partie (1-4)")
   parser.add_argument("--chapitre", type=int,
                       help="Filtrer par numéro de chapitre")
   parser.add_argument("--env", choices=["test", "production"], default=None,
                       help="Définir l'environnement (remplace la variable d'environnement OHADA_ENV)")
   args = parser.parse_args()

   # Définir l'environnement si spécifié
   if args.env:
       os.environ["OHADA_ENV"] = args.env
       print(f"Environnement défini: {args.env}")

   # Créer l'API
   api = create_ohada_query_api(args.config)
   
   # Exécuter la recherche
   print(f"Recherche en cours pour: \"{args.query}\"...")
   result = api.search_ohada_knowledge(
       query=args.query,
       partie=args.partie,
       chapitre=args.chapitre,
       n_results=args.n_results,
       include_sources=True
   )
   
   # Afficher les performances
   print(f"\nRecherche effectuée en {result['performance'].get('search_time_seconds', 0):.2f} secondes")
   print(f"Réponse générée en {result['performance'].get('generation_time_seconds', 0):.2f} secondes")
   print(f"Temps total: {result['performance']['total_time_seconds']:.2f} secondes")
   
   # Afficher la réponse
   print("\n=== RÉPONSE ===\n")
   print(result["answer"])
   
   # Afficher les sources
   if "sources" in result:
       print("\n=== SOURCES ===\n")
       for i, source in enumerate(result["sources"], 1):
           print(f"Source {i} (score: {source['relevance_score']:.2f}):")
           if "title" in source["metadata"]:
               print(f"Titre: {source['metadata']['title']}")
           print(f"Type: {source['metadata'].get('document_type', 'Non spécifié')}")
           if "partie" in source["metadata"]:
               print(f"Partie: {source['metadata']['partie']}")
           if "chapitre" in source["metadata"]:
               print(f"Chapitre: {source['metadata']['chapitre']}")
           print(f"Extrait: {source['preview']}")
           print()