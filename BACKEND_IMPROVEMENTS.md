# 🚀 AMÉLIORATIONS BACKEND - OHAD'AI Expert-Comptable

## 📋 Table des Matières

1. [Analyse de l'Architecture Actuelle](#analyse-architecture-actuelle)
2. [Points d'Amélioration Identifiés](#points-amélioration)
3. [Proposition d'Architecture Optimisée](#architecture-optimisée)
4. [Gestion des Documents](#gestion-documents)
5. [Optimisations Performance & Latence](#optimisations-performance)
6. [Nouvelles Fonctionnalités](#nouvelles-fonctionnalités)
7. [Plan de Migration](#plan-migration)

---

## 📊 1. ANALYSE DE L'ARCHITECTURE ACTUELLE {#analyse-architecture-actuelle}

### ✅ Points Forts

```
✓ API FastAPI bien structurée avec versioning
✓ Système RAG hybride performant (BM25 + Vector + Cross-Encoder)
✓ Authentification JWT complète
✓ Streaming SSE pour les réponses
✓ Multi-environnements (test/production)
✓ Docker ready
✓ Base vectorielle ChromaDB optimisée
```

### ❌ Problèmes Identifiés

#### **1. Gestion des Documents**
```yaml
Problème:
  - Documents stockés comme fichiers Word dans base_connaissances/
  - Pas de versioning
  - Pas de métadonnées riches (auteur, date modification, validation)
  - Difficile à maintenir et mettre à jour
  - Pas de traçabilité des modifications
  - Ingestion manuelle (script Python à lancer)

Impact:
  - Latence: Lecture fichiers à chaque ingestion
  - Maintenance: Difficile de savoir quel document a changé
  - Scalabilité: Pas adapté pour des milliers de documents
```

#### **2. Performance & Caching**
```yaml
Problème:
  - Pas de cache Redis
  - Embeddings recalculés à chaque requête similaire
  - Pas de cache pour les réponses LLM
  - SQLite pour les métadonnées (limite concurrence)

Impact:
  - Latence: 2-5s par requête (could be < 500ms)
  - Coût: Appels OpenAI répétés pour mêmes questions
  - Scalabilité: SQLite ne scale pas au-delà de ~100 req/s
```

#### **3. Architecture & Modularité**
```yaml
Problème:
  - Monolithique (tout dans un process FastAPI)
  - Pas de séparation retrieval/generation
  - Pas de queue pour traitement asynchrone
  - Pas de rate limiting
  - Pas de circuit breakers (si OpenAI down, tout crash)

Impact:
  - Scalabilité: Impossible de scaler retrieval vs generation
  - Résilience: Un service down = tout down
  - Performance: Pas de traitement parallèle optimal
```

#### **4. Monitoring & Observabilité**
```yaml
Problème:
  - Logging basique (fichiers texte)
  - Pas de métriques (latence, coûts, erreurs)
  - Pas d'alertes
  - Pas de tracing distribué

Impact:
  - Debug: Difficile de diagnostiquer les problèmes
  - Optimisation: Impossible d'identifier les bottlenecks
  - Business: Pas de visibilité sur les coûts API
```

#### **5. Base de Données**
```yaml
Problème:
  - SQLite (limite: ~100 req/s, pas distribué)
  - Pas de migrations automatiques (Alembic partiellement configuré)
  - Pas de backup automatisé
  - Pas de réplication

Impact:
  - Scalabilité: Ne peut pas servir > 100 utilisateurs concurrents
  - Résilience: Perte de données si crash
  - Performance: Locks sur écritures
```

---

## 🎯 2. POINTS D'AMÉLIORATION IDENTIFIÉS {#points-amélioration}

### Priorité 1 (Critique pour Performance)

```
1. ⚡ Ajouter Redis pour caching
2. 📦 Migrer documents vers base de données
3. 🔄 Implémenter rate limiting
4. 📊 Ajouter monitoring (Prometheus)
5. 🗄️ Migrer SQLite → PostgreSQL
```

### Priorité 2 (Importantes pour Scalabilité)

```
6. 🔀 Queue de traitement asynchrone (Celery/Redis)
7. 🛡️ Circuit breakers & fallbacks
8. 📈 Métriques coûts API
9. 🔍 Logging structuré (JSON)
10. 🔐 Rate limiting par utilisateur
```

### Priorité 3 (Nice to have)

```
11. 🌐 API GraphQL (en plus de REST)
12. 🔄 WebSocket pour chat temps réel
13. 📦 Compression des réponses (gzip)
14. 🎨 Admin panel (interface de gestion)
15. 📧 Notifications (email/webhook)
```

---

## 🏗️ 3. ARCHITECTURE OPTIMISÉE PROPOSÉE {#architecture-optimisée}

### Vue d'Ensemble

```
┌─────────────────────────────────────────────────────────────────┐
│                   ARCHITECTURE BACKEND v2.0                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────── API GATEWAY (NGINX/TRAEFIK) ────────────────┐
│  ✓ Rate Limiting Global                                          │
│  ✓ Load Balancing                                               │
│  ✓ SSL Termination                                              │
│  ✓ Request Routing                                              │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────── FASTAPI SERVICE ────────────────────────┐
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              API ROUTES (REST + SSE)                     │  │
│  │  ├─ /api/v1/auth/*         - Authentication             │  │
│  │  ├─ /api/v1/query/*        - Query endpoints            │  │
│  │  ├─ /api/v1/documents/*    - Document management (NEW)  │  │
│  │  ├─ /api/v1/conversations  - Conversations              │  │
│  │  ├─ /api/v1/admin/*        - Admin endpoints            │  │
│  │  └─ /api/v1/metrics        - Prometheus metrics (NEW)   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  MIDDLEWARE STACK                        │  │
│  │  ├─ Rate Limiter (per user)                             │  │
│  │  ├─ Request Logger (JSON structured)                    │  │
│  │  ├─ Circuit Breaker (external APIs)                     │  │
│  │  ├─ Compression (gzip)                                  │  │
│  │  └─ Prometheus Metrics Collector                        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
         │              │               │              │
         │              │               │              │
    ┌────▼────┐   ┌────▼────┐    ┌────▼────┐   ┌────▼─────┐
    │         │   │         │    │         │   │          │
    │  REDIS  │   │PostgreSQL│   │ ChromaDB│   │ Celery   │
    │  CACHE  │   │   DB     │   │ Vector  │   │ Workers  │
    │         │   │          │    │   DB    │   │          │
    └─────────┘   └──────────┘    └─────────┘   └──────────┘
         │              │               │              │
    ┌────▼──────────────▼───────────────▼──────────────▼─────┐
    │                                                          │
    │  Cache:               Database:        Vector:  Tasks:  │
    │  - Query results      - Users          - Embeddings     │
    │  - Embeddings         - Conversations  - Documents      │
    │  - LLM responses      - Messages       - Collections    │
    │  - Rate limits        - Documents Meta                  │
    │                       - Audit logs                       │
    └──────────────────────────────────────────────────────────┘
```

### Stack Technique Détaillée

```yaml
API Layer:
  Framework: FastAPI 0.115+
  ASGI Server: Uvicorn (with Gunicorn for production)
  Validation: Pydantic v2
  OpenAPI: Auto-generated Swagger docs

Caching Layer:
  Primary: Redis 7.x (Cluster mode for production)
  Use Cases:
    - Query result caching (TTL: 1 hour)
    - Embedding caching (TTL: 24 hours)
    - LLM response caching (TTL: 7 days)
    - Rate limiting counters
    - Session storage
    - Pub/Sub for real-time features

Database Layer:
  Primary: PostgreSQL 15+ (was SQLite)
  Why:
    - Better concurrency (1000+ connections)
    - JSONB support for flexible metadata
    - Full-text search (bonus)
    - Replication & backups
    - ACID compliance

  Schema:
    - users (auth, profiles)
    - conversations (threads)
    - messages (content)
    - documents (metadata, versions)  # NEW
    - document_versions (history)     # NEW
    - audit_logs (tracking)           # NEW
    - api_usage (metrics)             # NEW

Vector Database:
  Keep: ChromaDB 0.5+ (proven performant)
  Optimizations:
    - Connection pooling
    - Batch operations
    - Index optimization

Task Queue:
  Framework: Celery 5.x
  Broker: Redis
  Workers: Separate processes

  Tasks:
    - Document ingestion (async)
    - Embedding generation (batch)
    - Email notifications
    - Report generation
    - Database cleanup

Search & Retrieval:
  Hybrid: BM25 + Vector + Cross-Encoder (keep)
  Optimizations:
    - Pre-computed embeddings cache
    - Query result cache (Redis)
    - Parallel search execution

LLM Integration:
  Providers: OpenAI, DeepSeek (keep)
  Optimizations:
    - Response caching (semantic similarity)
    - Circuit breaker (fallback to cached)
    - Streaming optimized
    - Token usage tracking

Monitoring & Logging:
  Metrics: Prometheus + Grafana
  Logging: Structured JSON logs
  Tracing: OpenTelemetry (optional)
  Alerting: Prometheus Alertmanager

  Metrics Tracked:
    - Request latency (p50, p95, p99)
    - Error rates
    - API costs (per endpoint, per user)
    - Cache hit rates
    - Database query times
    - Queue lengths

Security:
  Auth: JWT (keep)
  Rate Limiting:
    - Global: 1000 req/min
    - Per user: 60 req/min
    - Per IP: 100 req/min
  Encryption:
    - TLS 1.3
    - Database encryption at rest
    - Secrets in environment variables
```

---

## 📦 4. GESTION DES DOCUMENTS {#gestion-documents}

### Problème Actuel

```
base_connaissances/
├── plan_comptable/
│   └── chapitres_word/
│       ├── partie_1/
│       │   ├── chapitre_1.docx
│       │   ├── chapitre_2.docx
│       │   └── ...
│       └── partie_2/...
├── presentation_ohada/
│   ├── Présentation de l'OHADA.docx
│   └── Traité relatif à L'ohada.docx
└── actes_uniformes/...

Issues:
❌ Fichiers éparpillés
❌ Pas de versioning
❌ Pas de métadonnées (auteur, date, statut)
❌ Pas de validation
❌ Ingestion manuelle
```

### Solution Proposée: Document Management System (DMS)

#### **Option A: Base de Données PostgreSQL (Recommandé)**

```sql
-- Schema proposé

-- Table principale des documents
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    document_type VARCHAR(50) NOT NULL,  -- 'chapitre', 'acte_uniforme', 'presentation'
    content_text TEXT NOT NULL,          -- Texte extrait
    content_binary BYTEA,                -- Document original (Word/PDF)
    content_hash VARCHAR(64) NOT NULL,   -- SHA-256 pour déduplication

    -- Métadonnées OHADA
    partie INT,
    chapitre INT,
    section INT,
    parent_id UUID REFERENCES documents(id),

    -- Métadonnées générales
    metadata JSONB DEFAULT '{}',         -- Métadonnées flexibles
    tags TEXT[],                         -- Tags pour recherche

    -- Versioning
    version INT NOT NULL DEFAULT 1,
    is_latest BOOLEAN DEFAULT TRUE,

    -- Status & workflow
    status VARCHAR(20) DEFAULT 'draft',  -- draft, review, published, archived
    validated_by UUID REFERENCES users(id),
    validated_at TIMESTAMP,

    -- Audit
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_by UUID REFERENCES users(id),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Indexation
    search_vector tsvector,              -- Full-text search PostgreSQL

    UNIQUE(content_hash, version)
);

-- Index pour performance
CREATE INDEX idx_documents_type ON documents(document_type);
CREATE INDEX idx_documents_partie_chapitre ON documents(partie, chapitre);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_metadata ON documents USING GIN(metadata);
CREATE INDEX idx_documents_search ON documents USING GIN(search_vector);
CREATE INDEX idx_documents_latest ON documents(is_latest) WHERE is_latest = TRUE;

-- Table historique des versions
CREATE TABLE document_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    version INT NOT NULL,
    content_text TEXT NOT NULL,
    content_binary BYTEA,
    metadata JSONB DEFAULT '{}',

    -- Changements
    change_description TEXT,
    changed_by UUID REFERENCES users(id),
    changed_at TIMESTAMP DEFAULT NOW(),

    -- Diff (optionnel)
    diff_from_previous JSONB,

    UNIQUE(document_id, version)
);

-- Table de relations entre documents
CREATE TABLE document_relations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    to_document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    relation_type VARCHAR(50) NOT NULL,  -- 'reference', 'replaces', 'complements'
    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(from_document_id, to_document_id, relation_type)
);

-- Table pour tracking des embeddings
CREATE TABLE document_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,           -- Pour documents chunked
    chunk_text TEXT NOT NULL,
    embedding_model VARCHAR(100) NOT NULL,
    chromadb_id VARCHAR(255) NOT NULL,  -- ID dans ChromaDB
    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(document_id, chunk_index, embedding_model)
);

-- Table de logs d'audit
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR(50) NOT NULL,   -- 'document', 'user', 'conversation'
    entity_id UUID NOT NULL,
    action VARCHAR(50) NOT NULL,        -- 'created', 'updated', 'deleted', 'viewed'
    user_id UUID REFERENCES users(id),
    metadata JSONB DEFAULT '{}',
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at DESC);
```

#### **Avantages PostgreSQL pour Documents**

```yaml
Avantages:
  ✓ Versioning natif (table versions)
  ✓ Full-text search intégré (tsvector)
  ✓ JSONB pour métadonnées flexibles
  ✓ Transactions ACID
  ✓ Backup/Restore facile (pg_dump)
  ✓ Réplication pour HA
  ✓ Performances excellentes (indexation)
  ✓ Relations entre documents (FK)

Inconvénients:
  ✗ Storage binaire limité (max 1GB/document)
  ✗ Plus complexe que système de fichiers
  ✗ Migration initiale nécessaire

Verdict: ✅ RECOMMANDÉ
  - Pour OHADA: documents < 50MB → OK
  - Relations entre documents importantes
  - Versioning critique
```

#### **Option B: Système de Fichiers + Métadonnées DB (Hybride)**

```yaml
Architecture:
  Files:
    - Storage: Filesystem (ou S3)
    - Path: /data/documents/{type}/{id}/{version}/
    - Format: Original (docx/pdf) + extracted (txt/json)

  Database:
    - Table: documents (métadonnées only)
    - Field: file_path (référence au fichier)
    - Indexation via PostgreSQL

Avantages:
  ✓ Pas de limite taille documents
  ✓ Plus simple pour très gros fichiers
  ✓ Backup séparé (files vs DB)

Inconvénients:
  ✗ Synchronisation files/DB complexe
  ✗ Risque d'orphelins (DB sans file ou vice-versa)
  ✗ Transactions compliquées

Verdict: ⚠️ ACCEPTABLE si documents > 100MB
```

#### **Option C: Object Storage (S3/MinIO)**

```yaml
Architecture:
  Storage: MinIO (S3-compatible, self-hosted)
  Structure:
    Bucket: ohada-documents
    Path: /{type}/{id}/{version}/document.{ext}

  Database:
    - Table: documents (métadonnées)
    - Field: s3_key (référence S3)

Avantages:
  ✓ Scalable infiniment
  ✓ Versioning natif S3
  ✓ CDN-ready
  ✓ Backup automatisé

Inconvénients:
  ✗ Complexité infrastructure
  ✗ Coût si cloud (AWS S3)
  ✗ Latence accès distant

Verdict: 🚀 OPTIMAL pour production scale
  - Recommandé si > 10K documents
  - Recommandé si déploiement cloud
```

### Décision: Architecture Hybride Recommandée

```yaml
Phase 1 (MVP): PostgreSQL uniquement
  - Documents < 50MB dans BYTEA
  - Simple à implémenter
  - Bon pour démarrer

Phase 2 (Scale): PostgreSQL + MinIO
  - Métadonnées dans PostgreSQL
  - Binaires dans MinIO (S3-compatible)
  - Best of both worlds

Migration:
  Étape 1: Créer tables PostgreSQL
  Étape 2: Script ingestion base_connaissances/ → DB
  Étape 3: Adapter code retrieval
  Étape 4: (Plus tard) Migrer binaires vers MinIO
```

### Nouvelle API Documents

```python
# Endpoints proposés

POST   /api/v1/documents               # Upload nouveau document
GET    /api/v1/documents               # Liste documents (filtres, pagination)
GET    /api/v1/documents/{id}          # Détails document
PUT    /api/v1/documents/{id}          # Mettre à jour document
DELETE /api/v1/documents/{id}          # Supprimer document (soft delete)

GET    /api/v1/documents/{id}/versions # Historique versions
GET    /api/v1/documents/{id}/versions/{version}  # Version spécifique
POST   /api/v1/documents/{id}/validate # Valider document (admin)

POST   /api/v1/documents/{id}/reindex  # Régénérer embeddings
GET    /api/v1/documents/stats         # Statistiques documents

# Exemple requête
POST /api/v1/documents
Content-Type: multipart/form-data

{
    "file": <binary>,
    "title": "Chapitre 5 - Amortissements",
    "document_type": "chapitre",
    "partie": 2,
    "chapitre": 5,
    "tags": ["amortissement", "immobilisation"],
    "metadata": {
        "author": "Expert OHADA",
        "source": "SYSCOHADA Révisé"
    }
}

Response 201:
{
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "title": "Chapitre 5 - Amortissements",
    "version": 1,
    "status": "draft",
    "created_at": "2025-01-15T10:30:00Z",
    "embedding_status": "pending"  # Généré en background
}
```

---

## ⚡ 5. OPTIMISATIONS PERFORMANCE & LATENCE {#optimisations-performance}

### Objectifs de Performance

```yaml
Current:
  - Query latency: 2-5 seconds
  - Embedding generation: 1-2 seconds
  - LLM generation: 3-8 seconds
  - Total: 6-15 seconds per query

Target:
  - Query latency: < 500ms (cache hit: < 100ms)
  - Embedding generation: < 200ms (cached)
  - LLM generation: 2-5 seconds (cached: < 100ms)
  - Total: < 3 seconds per query (cache: < 500ms)
```

### Stratégie de Caching Multi-Niveaux

```python
# Architecture de cache proposée

┌─────────────────────────────────────────────────────────┐
│                    CACHE HIERARCHY                       │
└─────────────────────────────────────────────────────────┘

Level 1: Memory Cache (In-Process)
├─ LRU Cache (functools.lru_cache)
├─ Size: 100MB
├─ TTL: 5 minutes
├─ Use: Configuration, user sessions
└─ Hit rate target: 95%

Level 2: Redis Cache (Distributed)
├─ Query Results
│  ├─ Key: query_hash:{semantic_hash}
│  ├─ TTL: 1 hour
│  └─ Stores: {answer, sources, metadata}
│
├─ Embeddings Cache
│  ├─ Key: embedding:{model}:{text_hash}
│  ├─ TTL: 24 hours
│  └─ Stores: [float] vector
│
├─ LLM Response Cache
│  ├─ Key: llm_response:{model}:{prompt_hash}
│  ├─ TTL: 7 days
│  └─ Stores: {response, tokens, cost}
│
└─ User Rate Limits
   ├─ Key: rate_limit:{user_id}:{endpoint}
   ├─ TTL: 60 seconds
   └─ Stores: request_count

Level 3: Database Cache
├─ PostgreSQL query cache (built-in)
├─ Materialized views for analytics
└─ Prepared statements

Level 4: CDN Cache (Optional, for frontend)
├─ Static assets
├─ Public API responses
└─ TTL: 1 day
```

### Implémentation Redis Cache

```python
# src/cache/redis_cache.py

import redis
import hashlib
import json
from typing import Any, Optional, Callable
from functools import wraps
import pickle

class RedisCache:
    """Cache Redis pour OHADA"""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.client = redis.from_url(redis_url, decode_responses=False)

    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        """Génère une clé de cache unique"""
        key_data = f"{prefix}:{args}:{sorted(kwargs.items())}"
        hash_key = hashlib.sha256(key_data.encode()).hexdigest()[:16]
        return f"ohada:{prefix}:{hash_key}"

    def get(self, key: str) -> Optional[Any]:
        """Récupère une valeur du cache"""
        value = self.client.get(key)
        if value:
            return pickle.loads(value)
        return None

    def set(self, key: str, value: Any, ttl: int = 3600):
        """Stocke une valeur dans le cache"""
        self.client.setex(key, ttl, pickle.dumps(value))

    def delete(self, key: str):
        """Supprime une clé du cache"""
        self.client.delete(key)

    def cache_query_result(self, ttl: int = 3600):
        """Décorateur pour cacher les résultats de requêtes"""
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Générer clé de cache
                cache_key = self._make_key(f"query:{func.__name__}", *args, **kwargs)

                # Essayer de récupérer du cache
                cached = self.get(cache_key)
                if cached is not None:
                    return cached

                # Sinon, exécuter la fonction
                result = func(*args, **kwargs)

                # Sauvegarder dans le cache
                self.set(cache_key, result, ttl)

                return result
            return wrapper
        return decorator

# Utilisation
cache = RedisCache()

@cache.cache_query_result(ttl=3600)
def search_documents(query: str, n_results: int = 5):
    # Recherche coûteuse...
    return results
```

### Optimisations Base de Données

```python
# Connexion pooling optimisé

from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    "postgresql://user:pass@localhost/ohada",
    poolclass=QueuePool,
    pool_size=20,           # Connexions permanentes
    max_overflow=40,        # Connexions temporaires max
    pool_pre_ping=True,     # Vérifier connexion avant utilisation
    pool_recycle=3600,      # Recycler connexions après 1h
    echo=False              # Pas de logging SQL (performance)
)

# Index optimisés (déjà dans schema proposé)
# Queries préparées (prepared statements)

# Exemple: Query optimization
# AVANT (slow)
SELECT * FROM messages WHERE conversation_id = '123' ORDER BY created_at DESC

# APRÈS (fast avec index)
CREATE INDEX idx_messages_conversation_created ON messages(conversation_id, created_at DESC);
```

### Optimisations ChromaDB

```python
# Configuration optimisée ChromaDB

import chromadb
from chromadb.config import Settings

# Client optimisé
client = chromadb.PersistentClient(
    path="./data/vector_db",
    settings=Settings(
        chroma_db_impl="duckdb+parquet",  # Plus rapide que SQLite
        anonymized_telemetry=False,
        allow_reset=False
    )
)

# Batch operations
def batch_add_documents(collection, documents, embeddings, metadatas, batch_size=100):
    """Ajout par lots pour meilleure performance"""
    for i in range(0, len(documents), batch_size):
        batch_docs = documents[i:i+batch_size]
        batch_embeddings = embeddings[i:i+batch_size]
        batch_metadatas = metadatas[i:i+batch_size]
        batch_ids = [f"doc_{i+j}" for j in range(len(batch_docs))]

        collection.add(
            documents=batch_docs,
            embeddings=batch_embeddings,
            metadatas=batch_metadatas,
            ids=batch_ids
        )

# Recherche parallèle dans plusieurs collections
import asyncio

async def parallel_search(collections, query_embedding, n_results=5):
    """Recherche en parallèle dans plusieurs collections"""
    tasks = [
        asyncio.to_thread(
            collection.query,
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        for collection in collections
    ]
    results = await asyncio.gather(*tasks)
    return results
```

### Rate Limiting & Throttling

```python
# src/middleware/rate_limiter.py

from fastapi import Request, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address
import redis

limiter = Limiter(key_func=get_remote_address)
redis_client = redis.from_url("redis://localhost:6379")

class RateLimiter:
    """Rate limiter avec Redis"""

    def __init__(self, redis_client):
        self.redis = redis_client

    async def check_rate_limit(
        self,
        key: str,
        max_requests: int,
        window: int
    ) -> bool:
        """
        Vérifie si la limite de requêtes est atteinte

        Args:
            key: Identifiant unique (user_id, ip, etc.)
            max_requests: Nombre max de requêtes
            window: Fenêtre de temps en secondes
        """
        current = self.redis.get(key)

        if current is None:
            # Première requête
            self.redis.setex(key, window, 1)
            return True

        if int(current) >= max_requests:
            return False

        self.redis.incr(key)
        return True

# Middleware FastAPI
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Extraire user_id ou IP
        user_id = request.state.user.get("user_id") if hasattr(request.state, "user") else None
        identifier = user_id or request.client.host

        # Vérifier rate limit
        limiter = RateLimiter(redis_client)
        allowed = await limiter.check_rate_limit(
            f"rate_limit:{identifier}",
            max_requests=60,  # 60 requêtes
            window=60         # par minute
        )

        if not allowed:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please try again later."
            )

        response = await call_next(request)
        return response
```

### Async Processing avec Celery

```python
# src/tasks/celery_app.py

from celery import Celery
from src.config.ohada_config import LLMConfig
from src.vector_db.ohada_vector_db_structure import OhadaVectorDB
from src.vector_db.ohada_document_ingestor import OhadaWordProcessor

# Configuration Celery
celery_app = Celery(
    'ohada_tasks',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/1'
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes max
)

# Tâches asynchrones

@celery_app.task(name="ingest_document")
def ingest_document_task(document_id: str, content: str, metadata: dict):
    """Ingestion asynchrone d'un document"""
    vector_db = OhadaVectorDB()
    processor = OhadaWordProcessor(vector_db)

    # Traiter le document
    # Générer embeddings
    # Ajouter à ChromaDB

    return {"document_id": document_id, "status": "completed"}

@celery_app.task(name="generate_report")
def generate_report_task(user_id: str, report_type: str, params: dict):
    """Génération asynchrone de rapport"""
    # Logique de génération
    return {"report_url": "/reports/123.pdf"}

@celery_app.task(name="cleanup_old_data")
def cleanup_old_data_task():
    """Nettoyage périodique des données"""
    # Nettoyer cache expiré
    # Archiver anciennes conversations
    # Nettoyer logs
    pass

# Scheduling (dans config)
celery_app.conf.beat_schedule = {
    'cleanup-every-night': {
        'task': 'cleanup_old_data',
        'schedule': crontab(hour=2, minute=0),  # 2am every day
    },
}
```

### Monitoring avec Prometheus

```python
# src/monitoring/prometheus.py

from prometheus_client import Counter, Histogram, Gauge
import time

# Métriques définies

# Compteurs
request_count = Counter(
    'ohada_requests_total',
    'Total requests',
    ['method', 'endpoint', 'status']
)

error_count = Counter(
    'ohada_errors_total',
    'Total errors',
    ['endpoint', 'error_type']
)

# Histogrammes (latence)
request_latency = Histogram(
    'ohada_request_duration_seconds',
    'Request latency',
    ['method', 'endpoint']
)

llm_latency = Histogram(
    'ohada_llm_duration_seconds',
    'LLM call latency',
    ['provider', 'model']
)

# Gauges (valeurs instantanées)
active_users = Gauge(
    'ohada_active_users',
    'Number of active users'
)

cache_hit_rate = Gauge(
    'ohada_cache_hit_rate',
    'Cache hit rate',
    ['cache_type']
)

# Middleware pour tracking

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Traiter la requête
        response = await call_next(request)

        # Enregistrer métriques
        duration = time.time() - start_time
        request_latency.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)

        request_count.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()

        return response

# Endpoint métriques
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

---

## 🆕 6. NOUVELLES FONCTIONNALITÉS {#nouvelles-fonctionnalités}

### 1. Recherche Avancée

```python
# Recherche multi-critères

POST /api/v1/search/advanced
{
    "query": "amortissement dégressif",
    "filters": {
        "document_type": ["chapitre", "acte_uniforme"],
        "partie": [1, 2],
        "date_range": {
            "from": "2020-01-01",
            "to": "2025-01-01"
        },
        "tags": ["amortissement", "immobilisation"]
    },
    "options": {
        "search_mode": "hybrid",  # "bm25", "vector", "hybrid"
        "min_relevance": 0.7,
        "group_by": "document_type",
        "highlight": true
    }
}
```

### 2. Suggestions Automatiques

```python
# Auto-complete pour requêtes

GET /api/v1/suggestions?q=amor&limit=10

Response:
{
    "suggestions": [
        {
            "text": "amortissement dégressif",
            "score": 0.95,
            "count": 42  # Nombre de fois recherché
        },
        {
            "text": "amortissement linéaire",
            "score": 0.88,
            "count": 35
        }
    ]
}
```

### 3. Analytics & Insights

```python
# Dashboard analytics

GET /api/v1/analytics/dashboard

Response:
{
    "period": "last_30_days",
    "metrics": {
        "total_queries": 1542,
        "unique_users": 89,
        "avg_response_time": 2.3,
        "cache_hit_rate": 0.67,
        "api_cost": 45.32,
        "top_queries": [
            {"query": "amortissement", "count": 123},
            {"query": "provisions", "count": 98}
        ],
        "top_documents": [
            {"title": "Chapitre 5", "views": 234}
        ]
    }
}
```

### 4. Export & Reporting

```python
# Export conversations/réponses

POST /api/v1/conversations/{id}/export
{
    "format": "pdf",  # pdf, docx, html, markdown
    "options": {
        "include_sources": true,
        "include_metadata": true,
        "language": "fr"
    }
}

Response:
{
    "export_id": "exp_123",
    "status": "processing",
    "estimated_time": 30
}

GET /api/v1/exports/{export_id}
Response: <file download>
```

### 5. Notifications & Webhooks

```python
# Configuration webhooks

POST /api/v1/webhooks
{
    "url": "https://myapp.com/webhook",
    "events": ["document.created", "query.completed"],
    "secret": "wh_secret_123"
}

# Événements envoyés
POST https://myapp.com/webhook
{
    "event": "document.created",
    "timestamp": "2025-01-15T10:30:00Z",
    "data": {
        "document_id": "doc_123",
        "title": "Nouveau chapitre"
    }
}
```

---

## 🗺️ 7. PLAN DE MIGRATION {#plan-migration}

### Phase 1: Infrastructure (Semaine 1-2)

```bash
✓ Tâche 1.1: Setup Redis
  - Installer Redis 7
  - Configurer persistence (AOF + RDB)
  - Tester connexion

✓ Tâche 1.2: Setup PostgreSQL
  - Installer PostgreSQL 15
  - Créer base de données
  - Créer schéma (tables proposées)
  - Configurer backup automatique

✓ Tâche 1.3: Migrations données
  - Script migration SQLite → PostgreSQL
  - Migration users, conversations, messages
  - Validation données

✓ Tâche 1.4: Setup monitoring
  - Installer Prometheus
  - Installer Grafana
  - Créer dashboards basiques
```

### Phase 2: Optimisations Performance (Semaine 3-4)

```bash
✓ Tâche 2.1: Implémenter Redis caching
  - RedisCache class
  - Cache embeddings
  - Cache query results
  - Cache LLM responses

✓ Tâche 2.2: Rate limiting
  - Middleware rate limit
  - Configuration par endpoint
  - Gestion quotas utilisateurs

✓ Tâche 2.3: Connection pooling
  - Pool PostgreSQL
  - Pool Redis
  - Pool ChromaDB (si possible)

✓ Tâche 2.4: Async tasks
  - Setup Celery
  - Workers configuration
  - Tasks ingestion documents
```

### Phase 3: Document Management (Semaine 5-6)

```bash
✓ Tâche 3.1: Migration documents → DB
  - Script ingestion base_connaissances/
  - Extraction métadonnées
  - Génération embeddings
  - Stockage PostgreSQL

✓ Tâche 3.2: API documents
  - CRUD endpoints
  - Upload/download
  - Versioning
  - Validation workflow

✓ Tâche 3.3: Admin interface (optionnel)
  - Interface gestion documents
  - Validation workflow
  - Analytics
```

### Phase 4: Nouvelles Fonctionnalités (Semaine 7-8)

```bash
✓ Tâche 4.1: Recherche avancée
  - Filtres multi-critères
  - Auto-complete
  - Suggestions

✓ Tâche 4.2: Analytics
  - Dashboard métriques
  - Usage tracking
  - Cost tracking

✓ Tâche 4.3: Export & reporting
  - Export conversations
  - Génération rapports
```

### Phase 5: Tests & Déploiement (Semaine 9-10)

```bash
✓ Tâche 5.1: Tests
  - Tests unitaires nouveaux modules
  - Tests intégration
  - Tests performance (load testing)
  - Tests end-to-end

✓ Tâche 5.2: Documentation
  - API documentation (OpenAPI)
  - Documentation technique
  - Guide déploiement

✓ Tâche 5.3: Déploiement production
  - Configuration production
  - Migration données production
  - Monitoring setup
  - Rollback plan
```

---

## 📝 RÉSUMÉ DES CHANGEMENTS

### ⚡ Impact Performance (estimé)

```yaml
Query Latency:
  Avant: 2-5 secondes
  Après: 0.5-3 secondes (cache: < 100ms)
  Gain: 60-70%

Cache Hit Rate:
  Target: 60-70%
  Économie API: ~$500-1000/mois (selon usage)

Scalabilité:
  Avant: ~100 req/s (SQLite limit)
  Après: ~1000 req/s (PostgreSQL + Redis)
  Gain: 10x

Concurrent Users:
  Avant: ~50 users
  Après: ~500 users
  Gain: 10x
```

### 💰 Coûts Infrastructure

```yaml
Développement:
  Base: PostgreSQL (gratuit, self-hosted)
  Cache: Redis (gratuit, self-hosted)
  Monitoring: Prometheus + Grafana (gratuit)
  Tâches: Celery (gratuit)

Production (mensuel estimé):
  VPS/Cloud: 30-100€ (selon trafic)
  - 4 CPU, 16GB RAM, 200GB SSD

  Backups: 10-20€
  Monitoring cloud (optionnel): 0-50€

  Total: 40-170€/mois

  VS coût actuel: 15-70€/mois
  Différence: +25-100€/mois

  ROI: Réduction coûts API OpenAI compensera largement
```

### 📊 Métriques Cibles

```yaml
Performance:
  - P50 latency: < 500ms
  - P95 latency: < 2s
  - P99 latency: < 5s
  - Uptime: 99.5%

Caching:
  - Cache hit rate: > 60%
  - Embedding cache: > 80%
  - LLM cache: > 40%

Business:
  - API cost reduction: 50-70%
  - User satisfaction: > 90%
  - Error rate: < 1%
```

---

## ✅ CONCLUSION

Cette proposition d'amélioration backend permettra:

1. **Performance**: Réduction latence de 60-70%
2. **Scalabilité**: Support de 10x plus d'utilisateurs
3. **Fiabilité**: Architecture résiliente avec caching et fallbacks
4. **Coûts**: Réduction coûts API de 50-70%
5. **Maintenance**: Document management centralisé
6. **Monitoring**: Visibilité complète sur métriques

**Timeline total**: 10 semaines
**Effort estimé**: 200-300 heures
**ROI**: 3-6 mois

Prêt à implémenter! 🚀
