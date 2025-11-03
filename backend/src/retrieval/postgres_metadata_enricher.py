"""
PostgreSQL Metadata Enricher

Enriches search results from ChromaDB with detailed metadata from PostgreSQL
"""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid
import os

try:
    from src.db.base import DATABASE_URL
    from src.models.document import Document
except ModuleNotFoundError:
    # When imported from outside backend directory
    from backend.src.db.base import DATABASE_URL
    from backend.src.models.document import Document

logger = logging.getLogger(__name__)


class PostgresMetadataEnricher:
    """
    Enriches search results with PostgreSQL metadata

    This class bridges the gap between ChromaDB (vector search) and PostgreSQL (rich metadata).
    It takes search results from ChromaDB and enriches them with full OHADA hierarchy and metadata
    from PostgreSQL.
    """

    def __init__(self, db_url: str = None):
        """
        Initialize the metadata enricher

        Args:
            db_url: Database URL (optional, uses DATABASE_URL env var if not provided)
        """
        if db_url is None:
            db_url = DATABASE_URL

        self.engine = create_engine(db_url)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def get_db(self) -> Session:
        """Get a database session"""
        return self.SessionLocal()

    def enrich_search_results(self, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enrich search results with PostgreSQL metadata

        Args:
            search_results: List of search results from ChromaDB
                Each result should have:
                - document_id: UUID as string
                - text: Document text chunk
                - metadata: Basic metadata from ChromaDB
                - relevance_score: Search relevance score

        Returns:
            Enriched search results with full OHADA hierarchy
        """
        if not search_results:
            return []

        db = self.get_db()

        try:
            # Extract document IDs from results
            document_ids = []
            for result in search_results:
                doc_id = result.get('document_id') or result.get('metadata', {}).get('document_id')
                if doc_id:
                    try:
                        document_ids.append(uuid.UUID(doc_id))
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid document_id format: {doc_id}")
                        continue

            if not document_ids:
                logger.warning("No valid document IDs found in search results")
                return search_results

            # Query PostgreSQL for document metadata
            documents = db.query(Document).filter(
                Document.id.in_(document_ids),
                Document.is_latest == True
            ).all()

            # Create a lookup dictionary
            doc_lookup = {str(doc.id): doc for doc in documents}

            # Enrich results
            enriched_results = []
            for result in search_results:
                doc_id = result.get('document_id') or result.get('metadata', {}).get('document_id')

                if not doc_id or doc_id not in doc_lookup:
                    # If no enrichment available, keep original result
                    enriched_results.append(result)
                    continue

                doc = doc_lookup[doc_id]

                # Create enriched result
                enriched_result = {
                    **result,  # Keep original fields
                    'metadata': {
                        **result.get('metadata', {}),  # Keep original metadata
                        # Add enriched metadata
                        'document_id': str(doc.id),
                        'title': doc.title,
                        'document_type': doc.document_type,
                        'collection': doc.collection,
                        'sub_collection': doc.sub_collection,
                        'acte_uniforme': doc.acte_uniforme,
                        'livre': doc.livre,
                        'titre': doc.titre,
                        'partie': doc.partie,
                        'chapitre': doc.chapitre,
                        'section': doc.section,
                        'sous_section': doc.sous_section,
                        'article': doc.article,
                        'alinea': doc.alinea,
                        'tags': doc.tags,
                        'status': doc.status,
                        'version': doc.version,
                        'date_publication': doc.date_publication.isoformat() if doc.date_publication else None,
                        'date_revision': doc.date_revision.isoformat() if doc.date_revision else None,
                        # Computed fields
                        'collection_display': self._format_collection(doc),
                        'hierarchy_display': self._format_hierarchy(doc),
                        'full_hierarchy_display': self._format_full_hierarchy(doc),
                        'citation': self._format_citation(doc)
                    }
                }

                enriched_results.append(enriched_result)

            logger.info(f"Enriched {len(enriched_results)} search results with PostgreSQL metadata")

            return enriched_results

        except Exception as e:
            logger.error(f"Failed to enrich search results: {e}", exc_info=True)
            # Return original results if enrichment fails
            return search_results

        finally:
            db.close()

    def _format_collection(self, doc: Document) -> str:
        """
        Format collection display

        Args:
            doc: Document object

        Returns:
            Formatted collection string (e.g., "Actes Uniformes > Droit Commercial Général")
        """
        parts = []

        if doc.collection:
            parts.append(doc.collection)
        if doc.sub_collection:
            parts.append(doc.sub_collection)

        return " > ".join(parts) if parts else ""

    def _format_hierarchy(self, doc: Document) -> str:
        """
        Format OHADA hierarchy display (internal document structure)

        Args:
            doc: Document object

        Returns:
            Formatted hierarchy string (e.g., "Partie 2 > Chapitre 5 > Section 1 > Article 25")
        """
        parts = []

        if doc.acte_uniforme:
            parts.append(doc.acte_uniforme)
        if doc.livre:
            parts.append(f"Livre {doc.livre}")
        if doc.titre:
            parts.append(f"Titre {doc.titre}")
        if doc.partie:
            parts.append(f"Partie {doc.partie}")
        if doc.chapitre:
            parts.append(f"Chapitre {doc.chapitre}")
        if doc.section:
            parts.append(f"Section {doc.section}")
        if doc.sous_section:
            parts.append(f"Sous-section {doc.sous_section}")
        if doc.article:
            parts.append(f"Article {doc.article}")

        return " > ".join(parts) if parts else ""

    def _format_full_hierarchy(self, doc: Document) -> str:
        """
        Format complete hierarchy (collection + OHADA structure)

        Args:
            doc: Document object

        Returns:
            Formatted full hierarchy string (e.g., "Actes Uniformes > Droit Commercial Général > Partie 2 > Chapitre 5")
        """
        parts = []

        # Add collection
        if doc.collection:
            parts.append(doc.collection)
        if doc.sub_collection:
            parts.append(doc.sub_collection)

        # Add OHADA hierarchy
        if doc.partie:
            parts.append(f"Partie {doc.partie}")
        if doc.chapitre:
            parts.append(f"Chapitre {doc.chapitre}")
        if doc.section:
            parts.append(f"Section {doc.section}")
        if doc.article:
            parts.append(f"Article {doc.article}")

        return " > ".join(parts) if parts else "Document OHADA"

    def _format_citation(self, doc: Document) -> str:
        """
        Format a standard citation for a document

        Args:
            doc: Document object

        Returns:
            Formatted citation string (e.g., "Article 25, Section 2, Chapitre 5, Partie 2, SYSCOHADA Révisé, 2017")
        """
        parts = []

        if doc.article:
            parts.append(f"Article {doc.article}")
        if doc.section:
            section_str = f"Section {doc.section}"
            if doc.sous_section:
                section_str += doc.sous_section
            parts.append(section_str)
        if doc.chapitre:
            parts.append(f"Chapitre {doc.chapitre}")
        if doc.partie:
            parts.append(f"Partie {doc.partie}")
        if doc.acte_uniforme:
            parts.append(doc.acte_uniforme)
        if doc.date_revision:
            year = doc.date_revision.year
            parts.append(f"SYSCOHADA Révisé, {year}")

        return ", ".join(parts) if parts else doc.title

    def get_document_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a single document by ID with full metadata

        Args:
            document_id: Document UUID as string

        Returns:
            Document dictionary or None if not found
        """
        db = self.get_db()

        try:
            doc = db.query(Document).filter(
                Document.id == uuid.UUID(document_id)
            ).first()

            if not doc:
                return None

            return {
                'id': str(doc.id),
                'title': doc.title,
                'document_type': doc.document_type,
                'content_text': doc.content_text,
                'acte_uniforme': doc.acte_uniforme,
                'livre': doc.livre,
                'titre': doc.titre,
                'partie': doc.partie,
                'chapitre': doc.chapitre,
                'section': doc.section,
                'sous_section': doc.sous_section,
                'article': doc.article,
                'alinea': doc.alinea,
                'tags': doc.tags,
                'metadata': doc.metadata,
                'status': doc.status,
                'version': doc.version,
                'date_publication': doc.date_publication.isoformat() if doc.date_publication else None,
                'date_revision': doc.date_revision.isoformat() if doc.date_revision else None,
                'hierarchy_display': self._format_hierarchy(doc),
                'citation': self._format_citation(doc)
            }

        except Exception as e:
            logger.error(f"Failed to get document {document_id}: {e}")
            return None

        finally:
            db.close()

    def search_by_hierarchy(
        self,
        acte_uniforme: Optional[str] = None,
        partie: Optional[int] = None,
        chapitre: Optional[int] = None,
        section: Optional[int] = None,
        article: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search documents by OHADA hierarchy

        Args:
            acte_uniforme: Acte uniforme name filter
            partie: Partie number filter
            chapitre: Chapitre number filter
            section: Section number filter
            article: Article number filter
            limit: Maximum number of results

        Returns:
            List of matching documents
        """
        db = self.get_db()

        try:
            query = db.query(Document).filter(
                Document.is_latest == True,
                Document.status == 'published'
            )

            if acte_uniforme:
                query = query.filter(Document.acte_uniforme.ilike(f"%{acte_uniforme}%"))
            if partie is not None:
                query = query.filter(Document.partie == partie)
            if chapitre is not None:
                query = query.filter(Document.chapitre == chapitre)
            if section is not None:
                query = query.filter(Document.section == section)
            if article:
                query = query.filter(Document.article == article)

            documents = query.order_by(
                Document.partie,
                Document.chapitre,
                Document.section,
                Document.article
            ).limit(limit).all()

            results = []
            for doc in documents:
                results.append({
                    'id': str(doc.id),
                    'title': doc.title,
                    'document_type': doc.document_type,
                    'acte_uniforme': doc.acte_uniforme,
                    'partie': doc.partie,
                    'chapitre': doc.chapitre,
                    'section': doc.section,
                    'article': doc.article,
                    'hierarchy_display': self._format_hierarchy(doc),
                    'citation': self._format_citation(doc)
                })

            return results

        except Exception as e:
            logger.error(f"Failed to search by hierarchy: {e}", exc_info=True)
            return []

        finally:
            db.close()
