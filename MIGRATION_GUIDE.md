# Migration Guide: Complete Document Management System

This guide explains how to migrate from the old file-based document management system to the new PostgreSQL-based system with enhanced OHADA hierarchy support.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Step-by-Step Migration](#step-by-step-migration)
4. [Document Parser](#document-parser)
5. [Import Methods](#import-methods)
6. [PostgreSQL Metadata Enrichment](#postgresql-metadata-enrichment)
7. [Celery Tasks](#celery-tasks)
8. [Troubleshooting](#troubleshooting)

## Overview

### What's New

The new architecture provides:

- **PostgreSQL-based document management** with full OHADA hierarchy (acte_uniforme, livre, titre, partie, chapitre, section, sous-section, article, alinéa)
- **Automatic metadata extraction** from Word documents using advanced parser
- **Version control** for all document changes
- **Enriched citations** with complete hierarchy information
- **Async processing** with Celery for document ingestion and embedding generation
- **Hybrid metadata system** combining PostgreSQL (structured metadata) with ChromaDB (vector embeddings)

### Architecture Comparison

**Before:**
```
base_connaissances/
├── chapitre_1.docx
├── chapitre_2.docx
└── presentation.docx

ChromaDB (metadata + embeddings)
```

**After:**
```
PostgreSQL (structured metadata, versioning, hierarchy)
    ↓ (linked via document_id)
ChromaDB (vector embeddings)

Documents ingested via:
- REST API
- Python scripts
- Bulk migration
```

## Prerequisites

### 1. Environment Setup

Ensure you have the following environment variables configured in `.env`:

```bash
# Database
DATABASE_URL=postgresql://ohada_user:your_password@localhost:5432/ohada

# Redis (for Celery)
REDIS_URL=redis://localhost:6379/0

# OpenAI
OPENAI_API_KEY=your_openai_api_key

# ChromaDB
CHROMA_PERSIST_DIRECTORY=./chroma_db

# Environment
OHADA_ENV=production  # or test
```

### 2. Install Dependencies

Add to `backend/requirements.txt`:

```txt
# Document Processing
python-docx==1.1.0
python-magic==0.4.27  # For file type detection (optional)

# Celery
celery==5.3.4
redis==5.0.1

# Existing dependencies
fastapi>=0.115.0
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
chromadb>=0.5.0
# ... other existing deps
```

Install:

```bash
cd backend
pip install -r requirements.txt
```

### 3. Start Docker Services

```bash
docker-compose -f docker-compose.prod.yml up -d postgres redis
```

Wait for PostgreSQL to be healthy:

```bash
docker-compose -f docker-compose.prod.yml ps postgres
```

### 4. Initialize Database Schema

The schema will be automatically created when PostgreSQL starts (via `db/init/01_schema.sql`).

Verify:

```bash
docker-compose -f docker-compose.prod.yml exec postgres psql -U ohada_user -d ohada -c "\dt"
```

You should see tables: `documents`, `document_versions`, `document_embeddings`, `users`, etc.

## Step-by-Step Migration

### Phase 1: Test with Single Document

Start by testing the import of a single document to verify everything works.

#### 1.1. Import One Document

```bash
cd backend

# Import a single document as draft
python scripts/import_document.py ../base_connaissances/chapitre_1.docx

# Or import and publish immediately
python scripts/import_document.py ../base_connaissances/chapitre_1.docx --publish
```

#### 1.2. Verify in Database

```bash
docker-compose -f docker-compose.prod.yml exec postgres psql -U ohada_user -d ohada

-- Check document was created
SELECT id, title, document_type, partie, chapitre, status FROM documents LIMIT 5;

-- Check metadata extraction
SELECT acte_uniforme, partie, chapitre, section, article FROM documents WHERE id = 'your-document-id';

-- Check embeddings
SELECT COUNT(*) FROM document_embeddings WHERE document_id = 'your-document-id';
```

#### 1.3. Test Search with Enrichment

```python
from src.retrieval.ohada_hybrid_retriever import create_ohada_query_api

# Create retriever with PostgreSQL enrichment
api = create_ohada_query_api()

# Search
result = api.search_ohada_knowledge(
    query="Qu'est-ce que le plan comptable?",
    n_results=5,
    include_sources=True
)

# Check enriched metadata in sources
for source in result['sources']:
    print(source['metadata']['hierarchy_display'])  # Should show full hierarchy
    print(source['metadata']['citation'])  # Should show complete citation
```

### Phase 2: Bulk Migration

Once single document import is working, migrate all documents.

#### 2.1. Dry Run First

Always do a dry run to preview what will be migrated:

```bash
cd backend

python scripts/migrate_all_documents.py \
  --source-dir ../base_connaissances \
  --dry-run
```

Review the output:

```
Found 50 .docx files in ../base_connaissances
DRY RUN MODE - No changes will be made
Would import: SYSCOHADA - Chapitre 1 (Type: chapitre, Partie 2, Chapitre 1)
Would import: Présentation OHADA (Type: presentation, Partie None, Chapitre None)
...
```

#### 2.2. Migrate All Documents

```bash
python scripts/migrate_all_documents.py \
  --source-dir ../base_connaissances \
  --user-email admin@ohada.com \
  --skip-duplicates \
  --progress
```

Options:
- `--publish`: Publish all documents immediately (default: draft)
- `--skip-duplicates`: Skip duplicate documents instead of failing
- `--progress`: Show progress bar (requires `pip install tqdm`)
- `--report migration_report.json`: Export detailed report

#### 2.3. Review Migration Report

```bash
# If you used --report flag
cat migration_report.json | jq '.'

# Check summary
cat migration_report.json | jq '.successful'
cat migration_report.json | jq '.errors'
```

#### 2.4. Verify Migration

```bash
docker-compose -f docker-compose.prod.yml exec postgres psql -U ohada_user -d ohada

-- Count imported documents
SELECT COUNT(*) FROM documents WHERE is_latest = TRUE;

-- Check document types
SELECT document_type, COUNT(*) FROM documents WHERE is_latest = TRUE GROUP BY document_type;

-- Check hierarchy coverage
SELECT
  COUNT(*) as total,
  COUNT(partie) as with_partie,
  COUNT(chapitre) as with_chapitre,
  COUNT(section) as with_section,
  COUNT(article) as with_article
FROM documents WHERE is_latest = TRUE;

-- Check embeddings
SELECT
  d.title,
  COUNT(e.id) as embedding_count
FROM documents d
LEFT JOIN document_embeddings e ON d.id = e.document_id
WHERE d.is_latest = TRUE
GROUP BY d.id, d.title
LIMIT 10;
```

### Phase 3: Async Processing with Celery

For production, use Celery for async document processing.

#### 3.1. Start Celery Worker

```bash
docker-compose -f docker-compose.prod.yml up -d celery-worker celery-beat
```

#### 3.2. Monitor Celery Tasks

```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs -f celery-worker

# Or use Flower (Celery monitoring tool)
pip install flower
celery -A src.tasks.celery_app flower --port=5555
# Open http://localhost:5555
```

#### 3.3. Submit Async Import Tasks

```python
from src.tasks.document_tasks import process_document_task, generate_embeddings_task

# Queue document processing
task = process_document_task.delay(
    file_path='../base_connaissances/chapitre_1.docx',
    user_id='your-user-id-uuid',
    publish=False
)

# Check task status
print(task.status)  # PENDING, STARTED, SUCCESS, FAILURE

# Get result
result = task.get(timeout=300)  # Wait up to 5 minutes
print(result)
# {'status': 'success', 'document_id': '...', 'title': '...'}
```

#### 3.4. Trigger Re-indexing

```python
from src.tasks.document_tasks import reindex_document_task, reindex_all_documents_task

# Re-index single document
task = reindex_document_task.delay('document-id-uuid')

# Re-index all published documents
task = reindex_all_documents_task.delay()
```

## Document Parser

### How the Parser Works

The `OhadaDocumentParser` automatically extracts:

1. **Title**: From first paragraph or filename
2. **Hierarchy**: Using regex patterns for OHADA structure
3. **Document Type**: Based on content analysis
4. **Tags**: Legal terms and keywords
5. **References**: Cross-references to other articles/sections
6. **Publication Date**: From document text

### Parser Configuration

The parser uses these regex patterns (from `extractor.py`):

```python
PATTERNS = {
    'acte_uniforme': r'Acte [Uu]niforme\s+(?:portant|relatif|sur)\s+(.+?)(?:\n|$|\.)',
    'livre': r'LIVRE\s+([IVXLCDM]+|[0-9]+)[:\s\-]',
    'titre': r'TITRE\s+([IVXLCDM]+|[0-9]+)[:\s\-]',
    'partie': r'(?:PARTIE|Partie)\s+([IVXLCDM]+|[0-9]+)[:\s\-]',
    'chapitre': r'(?:CHAPITRE|Chapitre)\s+([IVXLCDM]+|[0-9]+)[:\s\-]',
    'section': r'Section\s+([IVXLCDM]+|[0-9]+)[:\s\-]',
    'article': r'Article\s+([0-9]+(?:-[0-9]+)?(?:\s+[a-z]+)?)',
}
```

### Customizing the Parser

To customize extraction logic, edit `backend/src/document_parser/extractor.py`:

```python
class HierarchyExtractor:
    # Add new pattern
    PATTERNS = {
        **PATTERNS,
        'annexe': r'Annexe\s+([IVXLCDM]+|[0-9]+)',
    }

    @classmethod
    def extract_hierarchy_from_text(cls, text: str, title: str = "") -> HierarchyInfo:
        # Add custom logic
        hierarchy = HierarchyInfo()

        # Extract annexe
        match = re.search(cls.PATTERNS['annexe'], text, re.IGNORECASE)
        if match:
            hierarchy.annexe = match.group(1)

        return hierarchy
```

### Parser Validation

The parser includes validation to catch issues:

```python
from src.document_parser.parser import OhadaDocumentParser

parser = OhadaDocumentParser()
doc_data = parser.parse_docx('path/to/document.docx')

# Check for warnings
warnings = parser.validate_document_data(doc_data)
if warnings:
    print("Warnings:", warnings)
    # ['Missing title', 'Section without chapitre', ...]
```

Common warnings:
- `Missing title`: No title extracted
- `Content too short`: Less than 100 characters
- `Section without chapitre`: Inconsistent hierarchy
- `Could not determine specific document type`: Type is 'other'

## Import Methods

### Method 1: CLI Script (Recommended for Migration)

**Use case**: Migrating existing documents

```bash
# Single document
python scripts/import_document.py path/to/document.docx --publish

# Bulk import
python scripts/migrate_all_documents.py --source-dir base_connaissances --publish --progress
```

**Pros:**
- Simple, straightforward
- Good for one-time migrations
- Progress reporting
- Dry run option

**Cons:**
- No async processing
- Manual execution

### Method 2: REST API (Recommended for Production)

**Use case**: Adding new documents through application

```bash
# Create document via API
curl -X POST http://localhost:8000/api/v1/documents/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "SYSCOHADA - Chapitre 1",
    "document_type": "chapitre",
    "content_text": "...",
    "partie": 2,
    "chapitre": 1,
    "tags": ["comptabilité", "syscohada"]
  }'
```

**Pros:**
- Integrated with application
- Authentication/authorization
- Validation
- API-first workflow

**Cons:**
- Requires manual metadata entry
- No automatic parsing

### Method 3: Celery Task (Recommended for Large Batches)

**Use case**: Processing large batches asynchronously

```python
from src.tasks.document_tasks import process_document_task

# Queue multiple documents
documents = [
    'base_connaissances/chapitre_1.docx',
    'base_connaissances/chapitre_2.docx',
    # ... 100 more
]

task_ids = []
for doc_path in documents:
    task = process_document_task.delay(
        file_path=doc_path,
        user_id='user-id',
        publish=False
    )
    task_ids.append(task.id)

# Monitor progress
from celery.result import ResultSet
results = ResultSet(task_ids)
print(f"Completed: {results.completed_count()}/{len(task_ids)}")
```

**Pros:**
- Async processing
- Scalable
- Retry on failure
- Progress monitoring

**Cons:**
- Requires Celery setup
- More complex

### Comparison Matrix

| Feature | CLI Script | REST API | Celery Task |
|---------|------------|----------|-------------|
| Automatic parsing | ✅ | ❌ | ✅ |
| Async processing | ❌ | ❌ | ✅ |
| Authentication | ❌ | ✅ | ⚠️ (requires user_id) |
| Bulk import | ✅ | ⚠️ (manual loop) | ✅ |
| Progress reporting | ✅ | ❌ | ✅ |
| Dry run | ✅ | ❌ | ❌ |
| Retry on failure | ❌ | ❌ | ✅ |
| Best for | Migration | App integration | Production batch |

## PostgreSQL Metadata Enrichment

### How It Works

The `PostgresMetadataEnricher` bridges ChromaDB and PostgreSQL:

1. **Search**: Query ChromaDB for vector similarity → returns document_ids
2. **Enrich**: Query PostgreSQL with document_ids → returns full metadata
3. **Merge**: Combine vector results with PostgreSQL metadata

**Flow:**

```
User Query
    ↓
ChromaDB Search (vector similarity)
    ↓
Results with basic metadata
    ↓
PostgresMetadataEnricher.enrich_search_results()
    ↓
Results with full OHADA hierarchy + citations
```

### Integration with Hybrid Retriever

The enrichment is automatically applied in `OhadaHybridRetriever.search_hybrid()`:

```python
# In ohada_hybrid_retriever.py
def search_hybrid(self, query, ...):
    # ... BM25 + Vector search ...
    results = candidates[:n_results]

    # Automatic enrichment
    if self.metadata_enricher:
        results = self.metadata_enricher.enrich_search_results(results)

    return results
```

### Enriched Metadata Fields

**Before enrichment** (from ChromaDB):
```json
{
  "document_id": "uuid",
  "text": "chunk text",
  "metadata": {
    "partie": 2,
    "chapitre": 5
  },
  "relevance_score": 0.85
}
```

**After enrichment** (from PostgreSQL):
```json
{
  "document_id": "uuid",
  "text": "chunk text",
  "metadata": {
    "document_id": "uuid",
    "title": "SYSCOHADA - Chapitre 5",
    "document_type": "chapitre",
    "acte_uniforme": "Acte uniforme relatif au droit comptable",
    "livre": null,
    "titre": null,
    "partie": 2,
    "chapitre": 5,
    "section": 1,
    "sous_section": "A",
    "article": "25",
    "alinea": 1,
    "tags": ["comptabilité", "syscohada", "bilan"],
    "status": "published",
    "version": 1,
    "date_publication": "2017-01-24",
    "date_revision": "2017-01-24T00:00:00",
    "hierarchy_display": "Acte uniforme relatif au droit comptable > Partie 2 > Chapitre 5 > Section 1 > Sous-section A > Article 25",
    "citation": "Article 25, Section 1A, Chapitre 5, Partie 2, Acte uniforme relatif au droit comptable, SYSCOHADA Révisé, 2017"
  },
  "relevance_score": 0.85
}
```

### Using Enriched Metadata in Frontend

```javascript
// React component displaying search result
function SearchResult({ result }) {
  const { metadata } = result;

  return (
    <div className="search-result">
      <h3>{metadata.title}</h3>

      {/* Hierarchy breadcrumb */}
      <div className="hierarchy">
        {metadata.hierarchy_display}
      </div>

      {/* Citation */}
      <div className="citation">
        <strong>Citation:</strong> {metadata.citation}
      </div>

      {/* Tags */}
      <div className="tags">
        {metadata.tags?.map(tag => (
          <span key={tag} className="tag">{tag}</span>
        ))}
      </div>

      {/* Preview */}
      <p>{result.text}</p>

      {/* Relevance score */}
      <div className="score">
        Pertinence: {(result.relevance_score * 100).toFixed(0)}%
      </div>
    </div>
  );
}
```

### Disabling Enrichment

If you need to disable PostgreSQL enrichment (e.g., for testing):

```python
from src.retrieval.ohada_hybrid_retriever import OhadaHybridRetriever

retriever = OhadaHybridRetriever(
    vector_db=vector_db,
    enable_postgres_enrichment=False  # Disable enrichment
)
```

## Celery Tasks

### Available Tasks

#### 1. `process_document_task`

Process a Word document: parse, validate, store in PostgreSQL, generate embeddings.

```python
from src.tasks.document_tasks import process_document_task

task = process_document_task.delay(
    file_path='path/to/document.docx',
    user_id='user-uuid',
    publish=False
)

result = task.get()
# {'status': 'success', 'document_id': '...', 'title': '...', 'warnings': []}
```

#### 2. `generate_embeddings_task`

Generate embeddings for a document and store in ChromaDB.

```python
from src.tasks.document_tasks import generate_embeddings_task

task = generate_embeddings_task.delay(document_id='doc-uuid')

result = task.get()
# {'status': 'success', 'document_id': '...', 'embedding_count': 25}
```

#### 3. `reindex_document_task`

Delete old embeddings and regenerate for a document.

```python
from src.tasks.document_tasks import reindex_document_task

task = reindex_document_task.delay(document_id='doc-uuid')

result = task.get()
# {'status': 'success', 'document_id': '...', 'task_id': 'embedding-task-uuid'}
```

#### 4. `cleanup_old_versions_task`

Clean up old document versions (retention policy).

```python
from src.tasks.document_tasks import cleanup_old_versions_task

# Delete versions older than 30 days
task = cleanup_old_versions_task.delay(retention_days=30)

result = task.get()
# {'status': 'success', 'deleted_count': 45, 'cutoff_date': '2024-01-01T00:00:00'}
```

#### 5. `reindex_all_documents_task`

Re-index all published documents.

```python
from src.tasks.document_tasks import reindex_all_documents_task

task = reindex_all_documents_task.delay()

result = task.get()
# {'status': 'success', 'document_count': 150, 'task_ids': ['...', '...']}
```

### Scheduled Tasks (Celery Beat)

Configured in `src/tasks/celery_app.py`:

| Task | Schedule | Description |
|------|----------|-------------|
| `cleanup-old-versions` | Daily at 2 AM | Delete versions older than 30 days |
| `weekly-reindex` | Sunday at 3 AM | Re-index all published documents |

### Monitoring Celery

#### Using Flower

```bash
pip install flower
celery -A src.tasks.celery_app flower --port=5555
```

Open http://localhost:5555

#### Using Redis CLI

```bash
docker-compose -f docker-compose.prod.yml exec redis redis-cli

# Check queue length
LLEN celery

# Check task status
KEYS celery-task-meta-*
```

#### Using Prometheus + Grafana

Metrics are automatically exported to Prometheus (configured in `docker-compose.prod.yml`).

Access Grafana: http://localhost:3000 (admin/admin)

## Troubleshooting

### Issue: "Document already exists"

**Problem**: Attempting to import a duplicate document

**Solution**:

```bash
# Option 1: Skip duplicates
python scripts/migrate_all_documents.py --source-dir base_connaissances --skip-duplicates

# Option 2: Update existing document
python scripts/import_document.py file.docx
# When prompted, type 'y' to update
```

### Issue: "User not found"

**Problem**: User email doesn't exist in database

**Solution**:

```bash
# Create user first
docker-compose -f docker-compose.prod.yml exec postgres psql -U ohada_user -d ohada

INSERT INTO users (email, password_hash, full_name, is_admin)
VALUES ('admin@ohada.com', '$2b$12$...', 'Admin', TRUE);

# Or use default admin created by schema
# Email: admin@ohada.com
# Password: admin123
```

### Issue: Parser extracts wrong hierarchy

**Problem**: Document structure doesn't match regex patterns

**Solution**:

```python
# Method 1: Manual metadata entry
from src.api.v1.documents import create_document

# Use REST API with manual metadata
create_document({
    'title': 'Document title',
    'content_text': '...',
    'partie': 2,
    'chapitre': 5,
    # ... manual hierarchy
})

# Method 2: Customize parser patterns
# Edit backend/src/document_parser/extractor.py
PATTERNS = {
    'chapitre': r'(?:CHAPITRE|Chap\.)\s+([0-9]+)',  # Add abbreviation
}
```

### Issue: PostgreSQL enrichment not working

**Problem**: `metadata_enricher` is None

**Symptoms**:

```
WARNING - PostgreSQL metadata enrichment not available: ...
```

**Solution**:

```bash
# Check DATABASE_URL environment variable
echo $DATABASE_URL

# Verify PostgreSQL is running
docker-compose -f docker-compose.prod.yml ps postgres

# Check database connection
docker-compose -f docker-compose.prod.yml exec postgres psql -U ohada_user -d ohada -c "SELECT 1"

# If using backend from different location, check path
# Edit ohada_hybrid_retriever.py line 66:
backend_path = Path(__file__).parent.parent.parent / "backend"
print(f"Backend path: {backend_path}")
```

### Issue: Celery tasks stuck in PENDING

**Problem**: Celery worker not running or not connected to Redis

**Solution**:

```bash
# Check worker status
docker-compose -f docker-compose.prod.yml ps celery-worker

# Check worker logs
docker-compose -f docker-compose.prod.yml logs celery-worker

# Restart worker
docker-compose -f docker-compose.prod.yml restart celery-worker

# Check Redis connection
docker-compose -f docker-compose.prod.yml exec redis redis-cli ping
# Should return: PONG
```

### Issue: Embeddings not generated

**Problem**: ChromaDB collection not created or OpenAI API key missing

**Solution**:

```bash
# Check OPENAI_API_KEY
echo $OPENAI_API_KEY

# Check ChromaDB directory
ls -la ./chroma_db

# Manually trigger embedding generation
python -c "
from src.tasks.document_tasks import generate_embeddings_task
task = generate_embeddings_task.delay('document-uuid')
print(task.get())
"

# Check Celery worker logs for errors
docker-compose -f docker-compose.prod.yml logs celery-worker | grep ERROR
```

### Issue: Migration report shows many failures

**Problem**: Documents have invalid format or content

**Solution**:

```bash
# Export detailed error report
python scripts/migrate_all_documents.py \
  --source-dir base_connaissances \
  --report migration_report.json

# Analyze errors
cat migration_report.json | jq '.errors[]'

# Common fixes:
# 1. Remove temporary Word files (~$*.docx)
find base_connaissances -name "~$*.docx" -delete

# 2. Check file permissions
find base_connaissances -name "*.docx" -exec chmod 644 {} \;

# 3. Validate Word files
python -c "
from docx import Document
import sys
try:
    Document('path/to/problem.docx')
    print('Valid')
except Exception as e:
    print(f'Invalid: {e}')
"
```

## Next Steps

After successful migration:

1. **Test Search**: Verify enriched metadata appears in search results
2. **Update Frontend**: Use new metadata fields for enhanced UI
3. **Monitor Performance**: Check Prometheus dashboards for metrics
4. **Backup Database**: Setup PostgreSQL backups
5. **Document Workflow**: Train users on new document management process

## Support

For issues or questions:

1. Check logs: `docker-compose -f docker-compose.prod.yml logs`
2. Review database: `psql -U ohada_user -d ohada`
3. Test components individually: Run parser, import script, API separately
4. Consult documentation: See DOCKER_SETUP_GUIDE.md, BACKEND_IMPROVEMENTS.md

---

**Migration Checklist:**

- [ ] Environment variables configured
- [ ] Docker services running (postgres, redis)
- [ ] Database schema initialized
- [ ] Single document import tested
- [ ] Dry run completed
- [ ] Bulk migration executed
- [ ] Migration report reviewed
- [ ] Embeddings generated
- [ ] Search with enrichment tested
- [ ] Celery workers running
- [ ] Monitoring configured
- [ ] Backup strategy implemented
