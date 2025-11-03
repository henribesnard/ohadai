#!/usr/bin/env python3
"""
Test simplifié du workflow avec ChromaDB "ohada_documents"
Teste la recherche sémantique directe avec BGE-M3

Usage:
    python backend/scripts/test_simple_workflow.py
"""

import sys
import os
import time
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import chromadb
from src.vector_db.ohada_vector_db_structure import OhadaEmbedder

def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def test_chromadb_search():
    """Teste la recherche sémantique directe dans ChromaDB"""
    print_section("TEST WORKFLOW SIMPLIFIE - ChromaDB + BGE-M3")

    # 1. Vérifier ChromaDB
    print_section("1. VERIFICATION CHROMADB")
    try:
        client = chromadb.PersistentClient(path="backend/chroma_db")
        collection = client.get_collection("ohada_documents")

        count = collection.count()
        metadata = collection.metadata

        print(f"Collection: {collection.name}")
        print(f"Chunks: {count}")
        print(f"Modele: {metadata.get('embedding_model', 'N/A')}")
        print(f"Dimension: {metadata.get('embedding_dimension', 'N/A')}")

        if count == 0:
            print("\n[ERREUR] Aucun chunk dans ChromaDB!")
            return False

        print(f"\n[OK] ChromaDB pret avec {count} chunks")

    except Exception as e:
        print(f"[ERREUR] ChromaDB: {e}")
        return False

    # 2. Initialiser BGE-M3
    print_section("2. INITIALISATION BGE-M3")
    try:
        print("Chargement modele BGE-M3...")
        embedder = OhadaEmbedder(model_name="BAAI/bge-m3")
        print(f"[OK] BGE-M3 charge (dimension: {embedder.embedding_dimension})")

    except Exception as e:
        print(f"[ERREUR] Chargement modele: {e}")
        return False

    # 3. Test recherche sémantique
    print_section("3. TEST RECHERCHE SEMANTIQUE")

    query = "Comment comptabiliser les immobilisations corporelles?"
    print(f"Requete: \"{query}\"")

    try:
        # Générer embedding pour la requête
        print("\nGeneration embedding requete...")
        start_time = time.time()
        query_embedding = embedder.generate_embedding(query)
        embedding_time = time.time() - start_time
        print(f"[OK] Embedding genere en {embedding_time:.2f}s")

        # Recherche dans ChromaDB
        print("\nRecherche semantique dans ChromaDB...")
        search_start = time.time()
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=5
        )
        search_time = time.time() - search_start

        print(f"[OK] Recherche terminee en {search_time:.2f}s")
        print(f"Resultats trouves: {len(results['ids'][0]) if results['ids'] else 0}")

        # Afficher les résultats
        if results['documents'] and len(results['documents'][0]) > 0:
            print("\n--- RESULTATS ---")
            for i, (doc, metadata, distance) in enumerate(zip(
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            ), 1):
                print(f"\n{i}. Score: {1 - distance:.4f}")  # Convert distance to similarity
                print(f"   Collection: {metadata.get('collection', 'N/A')}")
                print(f"   Titre: {metadata.get('title', 'N/A')[:80]}")
                print(f"   Extrait: {doc[:150]}...")

            print_section("RESULTAT")
            print(f"Total time: {embedding_time + search_time:.2f}s")
            print(f"- Embedding: {embedding_time:.2f}s")
            print(f"- Search: {search_time:.2f}s")
            print(f"- Results: {len(results['ids'][0])}")
            print("\n[SUCCESS] Workflow semantique fonctionnel!")
            return True
        else:
            print("\n[ERREUR] Aucun resultat trouve")
            return False

    except Exception as e:
        print(f"\n[ERREUR] Recherche: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Point d'entree principal"""
    try:
        success = test_chromadb_search()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrompu")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERREUR FATALE] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
