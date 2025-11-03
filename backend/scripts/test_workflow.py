#!/usr/bin/env python3
"""
Script de test du workflow complet OHADA: BM25 + Semantic + Reranking + LLM
Teste les modes streaming et non-streaming

Usage:
    python backend/scripts/test_workflow.py
"""

import sys
import os
import time
import logging
from pathlib import Path
from typing import Dict, Any
import asyncio

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def print_subsection(title: str):
    """Print a formatted subsection header"""
    print(f"\n--- {title} ---")

def check_chromadb_status():
    """Vérifie l'état de ChromaDB"""
    print_section("1. VERIFICATION CHROMADB")

    try:
        import chromadb
        client = chromadb.PersistentClient(path="backend/chroma_db")
        collection = client.get_collection("ohada_documents")

        count = collection.count()
        metadata = collection.metadata

        print(f"Collection: {collection.name}")
        print(f"Chunks ingérés: {count}")
        print(f"Modèle d'embedding: {metadata.get('embedding_model', 'N/A')}")
        print(f"Dimension: {metadata.get('embedding_dimension', 'N/A')}")

        if count == 0:
            logger.error("ERREUR: Aucun chunk dans ChromaDB! L'ingestion n'est pas terminée.")
            return False

        print(f"\n[OK] ChromaDB prêt avec {count} chunks")
        return True

    except Exception as e:
        logger.error(f"ERREUR ChromaDB: {e}")
        return False

def initialize_hybrid_retriever():
    """Initialise le système de récupération hybride"""
    print_section("2. INITIALISATION DU RETRIEVER HYBRIDE")

    try:
        import chromadb
        from src.vector_db.ohada_vector_db_structure import OhadaVectorDB
        from src.retrieval.ohada_hybrid_retriever import OhadaHybridRetriever
        from src.config.ohada_config import LLMConfig

        # Initialize Vector DB wrapper
        print("Initialisation OhadaVectorDB...")
        vector_db = OhadaVectorDB(
            persist_directory="backend/chroma_db",
            embedding_model="BAAI/bge-m3"
        )

        # Initialize LLM Config
        print("Chargement configuration LLM...")
        llm_config = LLMConfig(config_path="backend/src/config")

        # Initialize Hybrid Retriever
        print("Initialisation OhadaHybridRetriever...")
        print("  - BM25Retriever (recherche lexicale)")
        print("  - VectorRetriever (recherche sémantique BGE-M3)")
        print("  - CrossEncoderReranker (reranking)")
        print("  - ContextProcessor (traitement contexte)")
        print("  - ResponseGenerator (génération réponse)")
        print("  - StreamingGenerator (génération streaming)")

        retriever = OhadaHybridRetriever(
            vector_db=vector_db,
            llm_config=llm_config,
            cross_encoder_model="cross-encoder/ms-marco-MiniLM-L-6-v2",
            enable_postgres_enrichment=True
        )

        print("\n[OK] Hybrid Retriever initialisé avec succès")
        return retriever

    except Exception as e:
        logger.error(f"ERREUR lors de l'initialisation: {e}", exc_info=True)
        return None

def test_hybrid_search(retriever, query: str, n_results: int = 5):
    """Teste la recherche hybride (BM25 + Semantic + Reranking)"""
    print_section(f"3. TEST RECHERCHE HYBRIDE")
    print(f"Requête: \"{query}\"")
    print(f"Nombre de résultats: {n_results}")

    try:
        start_time = time.time()

        # Recherche hybride avec reranking
        results = retriever.search_hybrid(
            query=query,
            collection_name="ohada_documents",
            n_results=n_results,
            rerank=True
        )

        search_time = time.time() - start_time

        print(f"\n[OK] Recherche terminée en {search_time:.2f}s")
        print(f"Résultats trouvés: {len(results)}")

        # Afficher les résultats
        print_subsection("Résultats")
        for i, result in enumerate(results[:3], 1):
            score = result.get('rerank_score', result.get('score', result.get('combined_score', 0)))
            if isinstance(score, str):
                print(f"\n{i}. Score: {score}")
            else:
                print(f"\n{i}. Score: {score:.4f}")
            print(f"   Collection: {result['metadata'].get('collection', 'N/A')}")
            print(f"   Titre: {result['metadata'].get('title', 'N/A')[:80]}")
            print(f"   Extrait: {result['text'][:150]}...")

        return results

    except Exception as e:
        logger.error(f"ERREUR recherche hybride: {e}", exc_info=True)
        return []

def test_non_streaming_response(retriever, query: str, results: list):
    """Teste la génération de réponse non-streaming"""
    print_section("4. TEST GENERATION REPONSE (NON-STREAMING)")

    try:
        start_time = time.time()

        # Générer réponse
        response = retriever.generate_response(
            query=query,
            search_results=results
        )

        generation_time = time.time() - start_time

        print(f"\n[OK] Réponse générée en {generation_time:.2f}s")
        print_subsection("Réponse")
        print(response)

        return response

    except Exception as e:
        logger.error(f"ERREUR génération réponse: {e}", exc_info=True)
        return None

async def test_streaming_response(retriever, query: str, results: list):
    """Teste la génération de réponse en streaming"""
    print_section("5. TEST GENERATION REPONSE (STREAMING)")

    try:
        start_time = time.time()
        full_response = ""

        # Callback pour capturer les chunks
        async def callback(event_type: str, data: Any):
            nonlocal full_response
            if event_type == "text_chunk":
                full_response += data
                print(data, end="", flush=True)

        # Générer réponse en streaming
        result = await retriever.streaming_generator.search_and_stream_response(
            query=query,
            search_results=results,
            n_results=len(results),
            include_sources=True,
            callback=callback
        )

        generation_time = time.time() - start_time

        print(f"\n\n[OK] Réponse streaming générée en {generation_time:.2f}s")
        print(f"Tokens générés: ~{len(full_response.split())}")

        return result

    except Exception as e:
        logger.error(f"ERREUR génération streaming: {e}", exc_info=True)
        return None

def run_complete_workflow_test():
    """Execute le test complet du workflow"""
    print_section("TEST WORKFLOW COMPLET OHADA")
    print("Architecture: backend/")
    print("Workflow: Query -> BM25 + Semantic -> Reranking -> Context -> LLM")
    print("Modes: Streaming & Non-Streaming")

    overall_start = time.time()

    # 1. Vérifier ChromaDB
    if not check_chromadb_status():
        print("\n[ERREUR] ChromaDB non prêt. Attendez la fin de l'ingestion.")
        return False

    # 2. Initialiser le retriever
    retriever = initialize_hybrid_retriever()
    if not retriever:
        print("\n[ERREUR] Impossible d'initialiser le retriever")
        return False

    # 3. Définir une requête de test
    test_query = "Comment comptabiliser les immobilisations corporelles?"

    # 4. Test recherche hybride
    results = test_hybrid_search(retriever, test_query, n_results=5)
    if not results:
        print("\n[ERREUR] Aucun résultat trouvé")
        return False

    # 5. Test génération non-streaming
    response = test_non_streaming_response(retriever, test_query, results)
    if not response:
        print("\n[ATTENTION] Génération non-streaming échouée")

    # 6. Test génération streaming
    print("\nTest streaming...")
    try:
        streaming_result = asyncio.run(
            test_streaming_response(retriever, test_query, results)
        )
    except Exception as e:
        logger.error(f"Erreur streaming: {e}")
        streaming_result = None

    # 7. Résumé
    overall_time = time.time() - overall_start

    print_section("RESUME DU TEST")
    print(f"Durée totale: {overall_time:.2f}s")
    print(f"ChromaDB: OK (chunks disponibles)")
    print(f"Recherche hybride: {'OK' if results else 'ERREUR'}")
    print(f"Génération non-streaming: {'OK' if response else 'ERREUR'}")
    print(f"Génération streaming: {'OK' if streaming_result else 'ERREUR'}")

    success = results and (response or streaming_result)

    if success:
        print("\n[SUCCESS] Workflow complet fonctionnel!")
    else:
        print("\n[ERREUR] Workflow incomplet, voir erreurs ci-dessus")

    return success

def main():
    """Point d'entrée principal"""
    try:
        success = run_complete_workflow_test()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrompu par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Erreur fatale: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
