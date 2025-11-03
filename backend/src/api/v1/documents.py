"""
API endpoints for document management
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import hashlib
import uuid

from src.db.base import get_db
from src.models.document import Document, DocumentVersion, DocumentEmbedding
from src.auth.auth_manager import get_current_user
from pydantic import BaseModel, Field

router = APIRouter(prefix="/documents", tags=["documents"])


# ====================
# Pydantic Models
# ====================

class DocumentBase(BaseModel):
    title: str
    document_type: str
    acte_uniforme: Optional[str] = None
    livre: Optional[int] = None
    titre: Optional[int] = None
    partie: Optional[int] = None
    chapitre: Optional[int] = None
    section: Optional[int] = None
    sous_section: Optional[str] = None
    article: Optional[str] = None
    alinea: Optional[int] = None
    metadata: dict = {}
    tags: List[str] = []
    page_debut: Optional[int] = None
    page_fin: Optional[int] = None
    date_publication: Optional[str] = None


class DocumentCreate(DocumentBase):
    content_text: str


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    content_text: Optional[str] = None
    metadata: Optional[dict] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None


class DocumentResponse(DocumentBase):
    id: str
    status: str
    version: int
    is_latest: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    documents: List[DocumentResponse]


# ====================
# Helper Functions
# ====================

def compute_content_hash(content: str) -> str:
    """Compute SHA-256 hash of content"""
    return hashlib.sha256(content.encode()).hexdigest()


def format_citation(doc: Document) -> str:
    """Format a standard citation for a document"""
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

    return ", ".join(parts)


def format_hierarchy(doc: Document) -> str:
    """Format full hierarchy display"""
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

    return " > ".join(parts)


# ====================
# Endpoints
# ====================

@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    doc_data: DocumentCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new document

    - **title**: Document title
    - **document_type**: Type (chapitre, acte_uniforme, presentation, etc.)
    - **content_text**: Full text content
    - **metadata**: Additional metadata (JSONB)
    - **tags**: List of tags for search
    """
    # Compute content hash
    content_hash = compute_content_hash(doc_data.content_text)

    # Check for duplicates
    existing = db.query(Document).filter(
        Document.content_hash == content_hash,
        Document.is_latest == True
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Document with same content already exists: {existing.id}"
        )

    # Create document
    new_doc = Document(
        id=uuid.uuid4(),
        title=doc_data.title,
        document_type=doc_data.document_type,
        content_text=doc_data.content_text,
        content_hash=content_hash,
        acte_uniforme=doc_data.acte_uniforme,
        livre=doc_data.livre,
        titre=doc_data.titre,
        partie=doc_data.partie,
        chapitre=doc_data.chapitre,
        section=doc_data.section,
        sous_section=doc_data.sous_section,
        article=doc_data.article,
        alinea=doc_data.alinea,
        metadata=doc_data.metadata,
        tags=doc_data.tags,
        page_debut=doc_data.page_debut,
        page_fin=doc_data.page_fin,
        date_publication=datetime.fromisoformat(doc_data.date_publication) if doc_data.date_publication else None,
        version=1,
        is_latest=True,
        status='draft',
        created_by=uuid.UUID(current_user['user_id']),
        updated_by=uuid.UUID(current_user['user_id'])
    )

    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    return new_doc


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    document_type: Optional[str] = None,
    status: Optional[str] = None,
    partie: Optional[int] = None,
    chapitre: Optional[int] = None,
    article: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    List documents with filters and pagination

    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    - **document_type**: Filter by type
    - **status**: Filter by status (draft, published, archived)
    - **partie**: Filter by partie number
    - **chapitre**: Filter by chapitre number
    - **article**: Filter by article number
    - **search**: Full-text search query
    """
    query = db.query(Document).filter(Document.is_latest == True)

    # Apply filters
    if document_type:
        query = query.filter(Document.document_type == document_type)
    if status:
        query = query.filter(Document.status == status)
    if partie is not None:
        query = query.filter(Document.partie == partie)
    if chapitre is not None:
        query = query.filter(Document.chapitre == chapitre)
    if article:
        query = query.filter(Document.article == article)

    # Full-text search
    if search:
        from sqlalchemy import func
        query = query.filter(
            func.to_tsvector('french', Document.content_text).op('@@')(
                func.plainto_tsquery('french', search)
            )
        )

    # Total count
    total = query.count()

    # Pagination
    offset = (page - 1) * page_size
    documents = query.offset(offset).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "documents": documents
    }


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get a single document by ID"""
    doc = db.query(Document).filter(Document.id == uuid.UUID(document_id)).first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found"
        )

    return doc


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: str,
    doc_update: DocumentUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update a document

    Creates a new version if content is changed.
    """
    doc = db.query(Document).filter(Document.id == uuid.UUID(document_id)).first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found"
        )

    # Check if content is being updated
    content_changed = False
    if doc_update.content_text and doc_update.content_text != doc.content_text:
        content_changed = True
        new_hash = compute_content_hash(doc_update.content_text)

        # Increment version
        doc.version += 1
        doc.content_text = doc_update.content_text
        doc.content_hash = new_hash

    # Update other fields
    if doc_update.title:
        doc.title = doc_update.title
    if doc_update.metadata:
        doc.metadata = doc_update.metadata
    if doc_update.tags is not None:
        doc.tags = doc_update.tags
    if doc_update.status:
        doc.status = doc_update.status

    doc.updated_by = uuid.UUID(current_user['user_id'])
    doc.updated_at = datetime.now()

    db.commit()
    db.refresh(doc)

    return doc


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    soft_delete: bool = Query(True, description="Soft delete (archive) or hard delete"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a document

    - **soft_delete**: If True, sets status to 'archived'. If False, permanently deletes.
    """
    doc = db.query(Document).filter(Document.id == uuid.UUID(document_id)).first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found"
        )

    if soft_delete:
        # Soft delete - just archive
        doc.status = 'archived'
        doc.updated_by = uuid.UUID(current_user['user_id'])
        db.commit()
    else:
        # Hard delete
        db.delete(doc)
        db.commit()

    return None


@router.get("/{document_id}/versions")
async def get_document_versions(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all versions of a document"""
    versions = db.query(DocumentVersion).filter(
        DocumentVersion.document_id == uuid.UUID(document_id)
    ).order_by(DocumentVersion.version.desc()).all()

    return {
        "document_id": document_id,
        "total_versions": len(versions),
        "versions": [
            {
                "version": v.version,
                "changed_at": v.changed_at,
                "changed_by": str(v.changed_by) if v.changed_by else None,
                "change_description": v.change_description
            }
            for v in versions
        ]
    }


@router.post("/{document_id}/publish")
async def publish_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Publish a document (change status from draft to published)

    Requires validation by an admin user.
    """
    # Check if user is admin
    if not current_user.get('is_admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can publish documents"
        )

    doc = db.query(Document).filter(Document.id == uuid.UUID(document_id)).first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found"
        )

    if doc.status == 'published':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document is already published"
        )

    doc.status = 'published'
    doc.validated_by = uuid.UUID(current_user['user_id'])
    doc.validated_at = datetime.now()
    doc.date_revision = datetime.now()
    doc.updated_by = uuid.UUID(current_user['user_id'])

    db.commit()
    db.refresh(doc)

    return {
        "message": "Document published successfully",
        "document": doc.to_dict()
    }


@router.post("/{document_id}/reindex")
async def reindex_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Trigger re-indexing of a document (regenerate embeddings)

    This creates a Celery task to regenerate embeddings for this document.
    """
    doc = db.query(Document).filter(Document.id == uuid.UUID(document_id)).first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found"
        )

    # Trigger Celery task (to be implemented)
    from src.tasks.celery_app import reindex_document_task

    task = reindex_document_task.delay(str(doc.id))

    return {
        "message": "Re-indexing task queued",
        "task_id": task.id,
        "document_id": str(doc.id)
    }


@router.get("/search/hierarchy")
async def search_by_hierarchy(
    acte_uniforme: Optional[str] = None,
    partie: Optional[int] = None,
    chapitre: Optional[int] = None,
    section: Optional[int] = None,
    article: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Search documents by OHADA hierarchy

    Example: Find all documents in Partie 2, Chapitre 5, Section 2
    """
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
    ).all()

    return {
        "total": len(documents),
        "filters": {
            "acte_uniforme": acte_uniforme,
            "partie": partie,
            "chapitre": chapitre,
            "section": section,
            "article": article
        },
        "documents": [
            {
                **doc.to_dict(),
                "hierarchy_display": format_hierarchy(doc),
                "citation": format_citation(doc)
            }
            for doc in documents
        ]
    }


@router.get("/stats/overview")
async def get_documents_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get overview statistics about documents"""
    from sqlalchemy import func

    total = db.query(func.count(Document.id)).filter(Document.is_latest == True).scalar()
    published = db.query(func.count(Document.id)).filter(
        Document.is_latest == True,
        Document.status == 'published'
    ).scalar()
    draft = db.query(func.count(Document.id)).filter(
        Document.is_latest == True,
        Document.status == 'draft'
    ).scalar()

    by_type = db.query(
        Document.document_type,
        func.count(Document.id).label('count')
    ).filter(
        Document.is_latest == True
    ).group_by(Document.document_type).all()

    return {
        "total_documents": total,
        "published": published,
        "draft": draft,
        "archived": total - published - draft,
        "by_type": {doc_type: count for doc_type, count in by_type}
    }
