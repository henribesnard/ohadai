"""
SQLAlchemy models for documents
"""

from sqlalchemy import (
    Column, String, Integer, Boolean, Text, TIMESTAMP,
    ForeignKey, ARRAY, Date, Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, BYTEA, TSVECTOR
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from src.db.base import Base


class Document(Base):
    """Main document model"""
    __tablename__ = "documents"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Basic info
    title = Column(String(500), nullable=False)
    document_type = Column(String(50), nullable=False)

    # Content
    content_text = Column(Text, nullable=False)
    content_binary = Column(BYTEA)
    content_hash = Column(String(64), nullable=False)

    # Organizational hierarchy (directory structure)
    collection = Column(String(100))  # actes_uniformes, plan_comptable, presentation_ohada
    sub_collection = Column(String(200))  # Specific acte uniforme name, partie number, etc.

    # OHADA hierarchy (document internal structure)
    acte_uniforme = Column(String(200))
    livre = Column(Integer)
    titre = Column(Integer)
    partie = Column(Integer)
    chapitre = Column(Integer)
    section = Column(Integer)
    sous_section = Column(String(10))
    article = Column(String(50))
    alinea = Column(Integer)

    # Parent relationship
    parent_id = Column(UUID(as_uuid=True), ForeignKey('documents.id', ondelete='SET NULL'))

    # Flexible metadata - using 'doc_metadata' to avoid SQLAlchemy reserved name conflict
    doc_metadata = Column('metadata', JSONB, default={})

    # Tags
    tags = Column(ARRAY(Text), default=[])

    # Pagination
    page_debut = Column(Integer)
    page_fin = Column(Integer)

    # Versioning
    version = Column(Integer, nullable=False, default=1)
    is_latest = Column(Boolean, default=True)

    # Dates
    date_publication = Column(Date)
    date_revision = Column(TIMESTAMP)

    # Status & workflow
    status = Column(String(20), default='draft')
    validated_by = Column(UUID(as_uuid=True), ForeignKey('users.user_id'))
    validated_at = Column(TIMESTAMP)

    # Audit
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.user_id'))
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_by = Column(UUID(as_uuid=True), ForeignKey('users.user_id'))
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Full-text search
    search_vector = Column(TSVECTOR)

    # Relationships
    parent = relationship("Document", remote_side=[id], backref="children")
    versions = relationship("DocumentVersion", back_populates="document", cascade="all, delete-orphan")
    embeddings = relationship("DocumentEmbedding", back_populates="document", cascade="all, delete-orphan")
    relations_from = relationship("DocumentRelation", foreign_keys="[DocumentRelation.from_document_id]", back_populates="from_document")
    relations_to = relationship("DocumentRelation", foreign_keys="[DocumentRelation.to_document_id]", back_populates="to_document")

    # Indexes
    __table_args__ = (
        Index('idx_documents_type', 'document_type'),
        Index('idx_documents_partie_chapitre', 'partie', 'chapitre'),
        Index('idx_documents_status', 'status'),
        Index('idx_documents_latest', 'is_latest'),
        Index('idx_documents_hierarchy', 'acte_uniforme', 'partie', 'chapitre', 'section'),
        Index('idx_documents_search', 'search_vector', postgresql_using='gin'),
        Index('idx_documents_metadata', 'metadata', postgresql_using='gin'),
        Index('idx_documents_tags', 'tags', postgresql_using='gin'),
    )

    def __repr__(self):
        return f"<Document(id={self.id}, title='{self.title}', type='{self.document_type}')>"

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "title": self.title,
            "document_type": self.document_type,
            "collection": self.collection,
            "sub_collection": self.sub_collection,
            "acte_uniforme": self.acte_uniforme,
            "livre": self.livre,
            "titre": self.titre,
            "partie": self.partie,
            "chapitre": self.chapitre,
            "section": self.section,
            "sous_section": self.sous_section,
            "article": self.article,
            "alinea": self.alinea,
            "metadata": self.doc_metadata,
            "tags": self.tags,
            "page_debut": self.page_debut,
            "page_fin": self.page_fin,
            "version": self.version,
            "is_latest": self.is_latest,
            "date_publication": self.date_publication.isoformat() if self.date_publication else None,
            "date_revision": self.date_revision.isoformat() if self.date_revision else None,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class DocumentVersion(Base):
    """Document version history"""
    __tablename__ = "document_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey('documents.id', ondelete='CASCADE'), nullable=False)
    version = Column(Integer, nullable=False)

    # Content snapshot
    content_text = Column(Text, nullable=False)
    content_binary = Column(BYTEA)
    doc_metadata = Column('metadata', JSONB, default={})

    # Change tracking
    change_description = Column(Text)
    changed_by = Column(UUID(as_uuid=True), ForeignKey('users.user_id'))
    changed_at = Column(TIMESTAMP, server_default=func.now())

    # Diff (optional)
    diff_from_previous = Column(JSONB)

    # Relationships
    document = relationship("Document", back_populates="versions")

    __table_args__ = (
        Index('idx_document_versions_document', 'document_id'),
        Index('idx_document_versions_changed_at', 'changed_at'),
    )

    def __repr__(self):
        return f"<DocumentVersion(document_id={self.document_id}, version={self.version})>"


class DocumentRelation(Base):
    """Relations between documents"""
    __tablename__ = "document_relations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_document_id = Column(UUID(as_uuid=True), ForeignKey('documents.id', ondelete='CASCADE'), nullable=False)
    to_document_id = Column(UUID(as_uuid=True), ForeignKey('documents.id', ondelete='CASCADE'), nullable=False)
    relation_type = Column(String(50), nullable=False)  # 'reference', 'replaces', 'complements', 'voir_aussi'
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Relationships
    from_document = relationship("Document", foreign_keys=[from_document_id], back_populates="relations_from")
    to_document = relationship("Document", foreign_keys=[to_document_id], back_populates="relations_to")

    __table_args__ = (
        Index('idx_document_relations_from', 'from_document_id'),
        Index('idx_document_relations_to', 'to_document_id'),
        Index('idx_document_relations_type', 'relation_type'),
    )

    def __repr__(self):
        return f"<DocumentRelation(from={self.from_document_id}, to={self.to_document_id}, type='{self.relation_type}')>"


class DocumentEmbedding(Base):
    """Document embeddings mapping to ChromaDB"""
    __tablename__ = "document_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey('documents.id', ondelete='CASCADE'), nullable=False)

    # Chunking info
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    chunk_title = Column(String(255))
    chunk_start_page = Column(Integer)
    chunk_end_page = Column(Integer)

    # Embedding info
    embedding_model = Column(String(100), nullable=False)
    chromadb_id = Column(String(255), nullable=False)
    chromadb_collection = Column(String(100), nullable=False)

    created_at = Column(TIMESTAMP, server_default=func.now())

    # Relationships
    document = relationship("Document", back_populates="embeddings")

    __table_args__ = (
        Index('idx_document_embeddings_document', 'document_id'),
        Index('idx_document_embeddings_chromadb', 'chromadb_id'),
        Index('idx_document_embeddings_collection', 'chromadb_collection'),
    )

    def __repr__(self):
        return f"<DocumentEmbedding(document_id={self.document_id}, chunk={self.chunk_index}, chromadb_id='{self.chromadb_id}')>"
