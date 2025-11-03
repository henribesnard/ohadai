#!/usr/bin/env python3
"""
Script d'ingestion vectorielle : PostgreSQL → ChromaDB avec BGE-M3

Récupère les documents de PostgreSQL, les découpe en chunks intelligents,
génère les embeddings avec BGE-M3 et les stocke dans ChromaDB.

Usage:
    python scripts/ingest_to_chromadb.py [--batch-size 4] [--chunk-size 3000] [--reset]

Examples:
    # Ingestion complète
    python scripts/ingest_to_chromadb.py

    # Reset ChromaDB et réingérer
    python scripts/ingest_to_chromadb.py --reset

    # Avec batch size personnalisé
    python scripts/ingest_to_chromadb.py --batch-size 8
"""

import sys
import os
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any
import time
from datetime import datetime
import re

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import chromadb
from chromadb.config import Settings

# Import custom modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
from vector_db.ohada_vector_db_structure import OhadaEmbedder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DocumentChunker:
    """Découpe intelligente des documents OHADA"""

    def __init__(self, chunk_size: int = 3000, overlap: int = 200):
        """
        Args:
            chunk_size: Taille cible des chunks en caractères (défaut: 3000)
            overlap: Chevauchement entre chunks en caractères (défaut: 200)
        """
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_document(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Découpe un document en chunks intelligents

        Args:
            text: Texte du document
            metadata: Métadonnées du document

        Returns:
            Liste de chunks avec métadonnées
        """
        chunks = []

        # Pour les petits documents, un seul chunk
        if len(text) <= self.chunk_size:
            chunks.append({
                'text': text,
                'metadata': {
                    **metadata,
                    'chunk_index': 0,
                    'total_chunks': 1,
                    'chunk_size': len(text)
                }
            })
            return chunks

        # Découpe par paragraphes d'abord
        paragraphs = text.split('\n\n')

        current_chunk = ""
        chunk_index = 0

        for para in paragraphs:
            # Si le paragraphe seul est trop grand, le découper par phrases
            if len(para) > self.chunk_size:
                sentences = re.split(r'([.!?])\s+', para)
                for i in range(0, len(sentences), 2):
                    sentence = sentences[i] + (sentences[i+1] if i+1 < len(sentences) else '')

                    if len(current_chunk) + len(sentence) > self.chunk_size:
                        if current_chunk:
                            chunks.append({
                                'text': current_chunk.strip(),
                                'metadata': {
                                    **metadata,
                                    'chunk_index': chunk_index,
                                    'chunk_size': len(current_chunk)
                                }
                            })
                            chunk_index += 1

                            # Overlap : garder les derniers mots
                            words = current_chunk.split()
                            overlap_words = words[-int(self.overlap/5):]  # Approximation
                            current_chunk = ' '.join(overlap_words) + ' '
                        else:
                            current_chunk = ""

                    current_chunk += sentence + ' '
            else:
                # Ajouter le paragraphe entier
                if len(current_chunk) + len(para) > self.chunk_size:
                    if current_chunk:
                        chunks.append({
                            'text': current_chunk.strip(),
                            'metadata': {
                                **metadata,
                                'chunk_index': chunk_index,
                                'chunk_size': len(current_chunk)
                            }
                        })
                        chunk_index += 1

                        # Overlap
                        words = current_chunk.split()
                        overlap_words = words[-int(self.overlap/5):]
                        current_chunk = ' '.join(overlap_words) + '\n\n'
                    else:
                        current_chunk = ""

                current_chunk += para + '\n\n'

        # Dernier chunk
        if current_chunk.strip():
            chunks.append({
                'text': current_chunk.strip(),
                'metadata': {
                    **metadata,
                    'chunk_index': chunk_index,
                    'chunk_size': len(current_chunk)
                }
            })

        # Ajouter total_chunks à tous les chunks
        total = len(chunks)
        for chunk in chunks:
            chunk['metadata']['total_chunks'] = total

        return chunks


def fetch_documents_from_postgres(db_url: str) -> List[Dict[str, Any]]:
    """
    Récupère tous les documents publiés de PostgreSQL

    Returns:
        Liste de documents avec contenu et métadonnées
    """
    engine = create_engine(db_url)

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                id,
                title,
                document_type,
                content_text,
                collection,
                sub_collection,
                acte_uniforme,
                livre,
                titre,
                partie,
                chapitre,
                section,
                sous_section,
                article,
                alinea,
                tags,
                status,
                created_at,
                updated_at
            FROM documents
            WHERE is_latest = true AND status = 'published'
            ORDER BY collection, sub_collection, partie, chapitre
        """))

        documents = []
        for row in result:
            documents.append({
                'id': str(row.id),
                'title': row.title,
                'document_type': row.document_type,
                'content_text': row.content_text,
                'collection': row.collection,
                'sub_collection': row.sub_collection,
                'acte_uniforme': row.acte_uniforme,
                'livre': row.livre,
                'titre': row.titre,
                'partie': row.partie,
                'chapitre': row.chapitre,
                'section': row.section,
                'sous_section': row.sous_section,
                'article': row.article,
                'alinea': row.alinea,
                'tags': list(row.tags) if row.tags else [],
                'status': row.status,
                'created_at': row.created_at.isoformat() if row.created_at else None,
                'updated_at': row.updated_at.isoformat() if row.updated_at else None
            })

    logger.info(f"Récupéré {len(documents)} documents de PostgreSQL")
    return documents


def ingest_to_chromadb(
    db_url: str,
    chroma_path: str = "backend/chroma_db",
    chunk_size: int = 3000,
    overlap: int = 200,
    batch_size: int = 4,
    reset: bool = False
):
    """
    Ingère tous les documents dans ChromaDB

    Args:
        db_url: URL PostgreSQL
        chroma_path: Chemin vers ChromaDB
        chunk_size: Taille des chunks
        overlap: Chevauchement entre chunks
        batch_size: Taille des batchs pour embedding
        reset: Reset ChromaDB avant ingestion
    """
    logger.info("="*60)
    logger.info("INGESTION VECTORIELLE : PostgreSQL → ChromaDB")
    logger.info("="*60)

    # Initialize embedder (BGE-M3 par défaut)
    logger.info("\n1. Chargement du modèle d'embedding...")
    embedder = OhadaEmbedder()  # Utilise BGE-M3 par défaut

    # Initialize ChromaDB
    logger.info(f"\n2. Connexion à ChromaDB ({chroma_path})...")
    chroma_client = chromadb.PersistentClient(path=chroma_path)

    # Reset si demandé
    if reset:
        logger.warning("  → Reset de ChromaDB demandé...")
        try:
            chroma_client.delete_collection("ohada_documents")
            logger.info("  → Collection supprimée")
        except:
            logger.info("  → Aucune collection à supprimer")

    # Créer ou récupérer la collection
    collection = chroma_client.get_or_create_collection(
        name="ohada_documents",
        metadata={
            "description": "Documents OHADA avec embeddings BGE-M3",
            "embedding_model": embedder.model_name,
            "embedding_dimension": embedder.embedding_dimension,
            "max_tokens": embedder.max_tokens
        }
    )
    logger.info(f"  → Collection: {collection.name}")
    logger.info(f"  → Modèle: {embedder.model_name}")
    logger.info(f"  → Dimension: {embedder.embedding_dimension}")
    logger.info(f"  → Documents existants: {collection.count()}")

    # Fetch documents from PostgreSQL
    logger.info("\n3. Récupération des documents PostgreSQL...")
    documents = fetch_documents_from_postgres(db_url)

    # Chunk documents
    logger.info(f"\n4. Découpage en chunks (taille: {chunk_size}, overlap: {overlap})...")
    chunker = DocumentChunker(chunk_size=chunk_size, overlap=overlap)

    all_chunks = []
    for doc in documents:
        chunks = chunker.chunk_document(doc['content_text'], {
            'document_id': doc['id'],
            'title': doc['title'],
            'document_type': doc['document_type'],
            'collection': doc['collection'],
            'sub_collection': doc['sub_collection'],
            'partie': doc['partie'],
            'chapitre': doc['chapitre'],
            'section': doc['section'],
            'article': doc['article'],
            'tags': ','.join(doc['tags']) if doc['tags'] else ''
        })
        all_chunks.extend(chunks)

    logger.info(f"  → Total chunks: {len(all_chunks)}")
    logger.info(f"  → Moyenne chunks/document: {len(all_chunks)/len(documents):.1f}")

    # Generate embeddings and store
    logger.info(f"\n5. Génération des embeddings et stockage (batch: {batch_size})...")

    start_time = time.time()
    batch_count = 0

    for i in range(0, len(all_chunks), batch_size):
        batch_chunks = all_chunks[i:i+batch_size]
        batch_count += 1

        # Extract texts
        texts = [chunk['text'] for chunk in batch_chunks]

        # Generate embeddings
        embeddings = embedder.generate_embeddings(texts, batch_size=batch_size)

        # Prepare data for ChromaDB
        ids = [f"{chunk['metadata']['document_id']}_chunk_{chunk['metadata']['chunk_index']}" for chunk in batch_chunks]

        # Clean metadatas: ChromaDB n'accepte que str, int, float, bool (pas None)
        clean_metadatas = []
        for metadata in [chunk['metadata'] for chunk in batch_chunks]:
            clean_metadata = {}
            for key, value in metadata.items():
                if value is not None:
                    # Convertir en string si ce n'est pas un type de base accepté
                    if isinstance(value, (str, int, float, bool)):
                        clean_metadata[key] = value
                    else:
                        clean_metadata[key] = str(value)
            clean_metadatas.append(clean_metadata)

        # Add to ChromaDB
        collection.add(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=clean_metadatas
        )

        # Progress
        if batch_count % 10 == 0:
            elapsed = time.time() - start_time
            progress = (i + batch_size) / len(all_chunks) * 100
            rate = (i + batch_size) / elapsed
            eta = (len(all_chunks) - i - batch_size) / rate if rate > 0 else 0

            logger.info(f"  → Progression: {progress:.1f}% | {i+batch_size}/{len(all_chunks)} chunks | {rate:.1f} chunks/s | ETA: {eta/60:.1f} min")

    # Final stats
    elapsed_time = time.time() - start_time
    logger.info("\n" + "="*60)
    logger.info("INGESTION TERMINÉE!")
    logger.info("="*60)
    logger.info(f"Documents: {len(documents)}")
    logger.info(f"Chunks: {len(all_chunks)}")
    logger.info(f"Temps: {elapsed_time/60:.1f} minutes")
    logger.info(f"Vitesse moyenne: {len(all_chunks)/elapsed_time:.1f} chunks/s")
    logger.info(f"ChromaDB count: {collection.count()}")
    logger.info("="*60)


def main():
    parser = argparse.ArgumentParser(
        description='Ingestion vectorielle PostgreSQL → ChromaDB',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--db-url',
        default='postgresql://ohada_user:changeme_in_production@localhost:5434/ohada',
        help='PostgreSQL URL'
    )

    parser.add_argument(
        '--chroma-path',
        default='backend/chroma_db',
        help='Chemin vers ChromaDB'
    )

    parser.add_argument(
        '--chunk-size',
        type=int,
        default=3000,
        help='Taille des chunks en caractères (défaut: 3000)'
    )

    parser.add_argument(
        '--overlap',
        type=int,
        default=200,
        help='Chevauchement entre chunks (défaut: 200)'
    )

    parser.add_argument(
        '--batch-size',
        type=int,
        default=4,
        help='Taille des batchs pour embedding (défaut: 4)'
    )

    parser.add_argument(
        '--reset',
        action='store_true',
        help='Reset ChromaDB avant ingestion'
    )

    args = parser.parse_args()

    try:
        ingest_to_chromadb(
            db_url=args.db_url,
            chroma_path=args.chroma_path,
            chunk_size=args.chunk_size,
            overlap=args.overlap,
            batch_size=args.batch_size,
            reset=args.reset
        )

        logger.info("\n[OK] Ingestion réussie!")

    except Exception as e:
        logger.error(f"\n[ERROR] Ingestion échouée: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
