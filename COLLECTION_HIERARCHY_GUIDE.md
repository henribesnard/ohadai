# Guide de la Hiérarchie Organisationnelle (Collections)

## ✅ Problème Résolu

Le système capture maintenant **DEUX hiérarchies distinctes**:

### 1. **Hiérarchie Organisationnelle** (Structure des répertoires) - **NOUVEAU**

Basée sur la structure `base_connaissances/`:

- **collection**: Catégorie principale (Actes Uniformes, Plan Comptable, Présentation OHADA, etc.)
- **sub_collection**: Sous-catégorie (nom de l'acte spécifique, numéro de partie, etc.)

### 2. **Hiérarchie OHADA** (Structure interne des documents) - **EXISTANT**

Basée sur le contenu du document:

- acte_uniforme, livre, titre, partie, chapitre, section, sous_section, article, alinéa

## Structure Complète Supportée

### 1. Actes Uniformes

**Structure:**
```
base_connaissances/actes_uniformes/
├── contrats de transport de marchandises par route/
├── droit commercial général/
├── droit comptable et information financière/
├── droit de l'arbitrage/
├── droit des sociétés commerciales et du GIE/
├── droit des sociétés coopératives/
├── médiation/
├── organisation de procédures collectives d'apurement du passif/
├── organisation des procédures simplifiées de recouvrement/
├── organisation des sûretés/
└── système comptable des entités à but non lucratif/
```

**Exemple de fichier:**
```
base_connaissances/actes_uniformes/droit commercial général/Livre_1.docx
```

**Métadonnées extraites:**
```json
{
  "collection": "Actes Uniformes",
  "sub_collection": "Droit Commercial Général",
  "livre": 1,
  "partie": null,
  "chapitre": null
}
```

**Affichage complet:**
```
Actes Uniformes > Droit Commercial Général > Livre 1
```

### 2. Plan Comptable SYSCOHADA

**Structure:**
```
base_connaissances/plan_comptable/
└── chapitres_word/
    ├── partie_1/
    │   ├── chapitre_1.docx
    │   ├── chapitre_2.docx
    │   └── ...
    ├── partie_2/
    ├── partie_3/
    └── partie_4/
```

**Exemple de fichier:**
```
base_connaissances/plan_comptable/chapitres_word/partie_2/chapitre_5.docx
```

**Métadonnées extraites:**
```json
{
  "collection": "Plan Comptable SYSCOHADA",
  "sub_collection": "Partie 2",
  "partie": 2,
  "chapitre": 5,
  "section": null
}
```

**Affichage complet:**
```
Plan Comptable SYSCOHADA > Partie 2 > Chapitre 5
```

### 3. Présentation OHADA

**Structure:**
```
base_connaissances/presentation_ohada/
├── Introduction.docx
├── Historique.docx
└── Institutions.docx
```

**Exemple de fichier:**
```
base_connaissances/presentation_ohada/Introduction.docx
```

**Métadonnées extraites:**
```json
{
  "collection": "Présentation OHADA",
  "sub_collection": null,
  "document_type": "presentation"
}
```

**Affichage complet:**
```
Présentation OHADA
```

### 4. Futures Collections (Extensible)

Le système supporte automatiquement d'autres collections :

```
base_connaissances/
├── jurisprudence/              → "Jurisprudence"
├── doctrine/                   → "Doctrine"
├── reglements/                 → "Règlements"
└── [tout autre répertoire]/    → Titre automatique
```

## Nouveaux Champs PostgreSQL

### Table `documents`

```sql
-- Organizational hierarchy (NEW)
collection VARCHAR(100),        -- "Actes Uniformes", "Plan Comptable SYSCOHADA", etc.
sub_collection VARCHAR(200),    -- "Droit Commercial Général", "Partie 2", etc.

-- OHADA hierarchy (EXISTING)
acte_uniforme VARCHAR(200),
livre INT,
titre INT,
partie INT,
chapitre INT,
section INT,
sous_section VARCHAR(10),
article VARCHAR(50),
alinea INT
```

### Indexes Créés

```sql
CREATE INDEX idx_documents_collection ON documents(collection);
CREATE INDEX idx_documents_sub_collection ON documents(sub_collection);
CREATE INDEX idx_documents_collection_sub ON documents(collection, sub_collection);
```

### Vue Enrichie

```sql
CREATE VIEW v_documents_active AS
SELECT
    d.*,
    -- Collection hierarchy
    CONCAT_WS(' > ', d.collection, d.sub_collection) as collection_display,

    -- OHADA hierarchy
    CONCAT_WS(' > ',
        CASE WHEN d.partie IS NOT NULL THEN 'Partie ' || d.partie END,
        CASE WHEN d.chapitre IS NOT NULL THEN 'Chapitre ' || d.chapitre END,
        ...
    ) as hierarchy_display,

    -- Full hierarchy (collection + OHADA)
    CONCAT_WS(' > ',
        d.collection,
        d.sub_collection,
        CASE WHEN d.partie IS NOT NULL THEN 'Partie ' || d.partie END,
        ...
    ) as full_hierarchy_display
FROM documents d
WHERE d.status = 'published' AND d.is_latest = TRUE;
```

## Parser Automatique

Le parser extrait automatiquement `collection` et `sub_collection` du chemin du fichier:

### Exemple 1: Acte Uniforme

```python
from src.document_parser import OhadaDocumentParser

parser = OhadaDocumentParser()
doc_data = parser.parse_docx(
    'base_connaissances/actes_uniformes/droit commercial général/Livre_1.docx'
)

print(doc_data['collection'])       # "Actes Uniformes"
print(doc_data['sub_collection'])   # "Droit Commercial Général"
print(doc_data['livre'])            # 1
```

### Exemple 2: Plan Comptable

```python
doc_data = parser.parse_docx(
    'base_connaissances/plan_comptable/chapitres_word/partie_2/chapitre_5.docx'
)

print(doc_data['collection'])       # "Plan Comptable SYSCOHADA"
print(doc_data['sub_collection'])   # "Partie 2"
print(doc_data['partie'])           # 2
print(doc_data['chapitre'])         # 5
```

### Exemple 3: Présentation

```python
doc_data = parser.parse_docx(
    'base_connaissances/presentation_ohada/Introduction.docx'
)

print(doc_data['collection'])       # "Présentation OHADA"
print(doc_data['sub_collection'])   # None
print(doc_data['document_type'])    # "presentation"
```

## Résultats de Recherche Enrichis

Après enrichissement avec PostgreSQL, chaque résultat contient:

```json
{
  "document_id": "uuid",
  "text": "chunk text",
  "relevance_score": 0.85,
  "metadata": {
    // Collection (organizational hierarchy)
    "collection": "Actes Uniformes",
    "sub_collection": "Droit Commercial Général",

    // OHADA hierarchy (document internal structure)
    "livre": 1,
    "partie": null,
    "chapitre": null,
    "section": null,
    "article": null,

    // Display fields
    "collection_display": "Actes Uniformes > Droit Commercial Général",
    "hierarchy_display": "Livre 1",
    "full_hierarchy_display": "Actes Uniformes > Droit Commercial Général > Livre 1",

    // Other metadata
    "title": "Droit Commercial Général - Livre 1",
    "tags": ["commercial", "droit", "entreprise"],
    "status": "published"
  }
}
```

## Utilisation dans le Frontend

### Affichage Hiérarchique

```javascript
function DocumentCard({ result }) {
  const { metadata } = result;

  return (
    <div className="document-card">
      {/* Collection breadcrumb */}
      <div className="breadcrumb">
        {metadata.collection_display}
      </div>

      {/* Title */}
      <h3>{metadata.title}</h3>

      {/* Full hierarchy */}
      <div className="hierarchy">
        📁 {metadata.full_hierarchy_display}
      </div>

      {/* Content preview */}
      <p>{result.text}</p>

      {/* Tags */}
      <div className="tags">
        {metadata.tags?.map(tag => (
          <span key={tag} className="tag">{tag}</span>
        ))}
      </div>
    </div>
  );
}
```

### Filtrage par Collection

```javascript
// API call with collection filter
const searchDocuments = async (query, filters) => {
  const response = await fetch('/api/v1/documents/', {
    method: 'GET',
    headers: { 'Authorization': `Bearer ${token}` },
    body: JSON.stringify({
      query,
      collection: filters.collection,          // "Actes Uniformes"
      sub_collection: filters.subCollection,   // "Droit Commercial Général"
      partie: filters.partie,
      chapitre: filters.chapitre
    })
  });

  return response.json();
};
```

### Navigation Hiérarchique

```javascript
// Sidebar navigation
function CollectionNavigator() {
  const [collections, setCollections] = useState([]);

  useEffect(() => {
    // Get distinct collections
    fetch('/api/v1/documents/collections')
      .then(res => res.json())
      .then(setCollections);
  }, []);

  return (
    <nav className="collection-nav">
      {collections.map(collection => (
        <div key={collection.name} className="collection-group">
          <h3>{collection.name}</h3>
          <ul>
            {collection.sub_collections.map(sub => (
              <li key={sub}>
                <Link to={`/documents/${collection.name}/${sub}`}>
                  {sub}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </nav>
  );
}
```

## Recherche par Collection

### SQL Direct

```sql
-- Tous les documents d'une collection
SELECT * FROM documents
WHERE collection = 'Actes Uniformes'
  AND is_latest = TRUE
  AND status = 'published';

-- Tous les documents d'une sous-collection
SELECT * FROM documents
WHERE collection = 'Actes Uniformes'
  AND sub_collection = 'Droit Commercial Général'
  AND is_latest = TRUE;

-- Grouper par collection
SELECT
  collection,
  sub_collection,
  COUNT(*) as doc_count
FROM documents
WHERE is_latest = TRUE
GROUP BY collection, sub_collection
ORDER BY collection, sub_collection;
```

### API REST

```bash
# Tous les actes uniformes
curl "http://localhost:8000/api/v1/documents/?collection=Actes+Uniformes"

# Un acte spécifique
curl "http://localhost:8000/api/v1/documents/?collection=Actes+Uniformes&sub_collection=Droit+Commercial+Général"

# Plan comptable partie 2
curl "http://localhost:8000/api/v1/documents/?collection=Plan+Comptable+SYSCOHADA&sub_collection=Partie+2"
```

### Python

```python
from backend.src.retrieval.postgres_metadata_enricher import PostgresMetadataEnricher

enricher = PostgresMetadataEnricher()

# Rechercher par collection
results = enricher.search_by_hierarchy(
    collection="Actes Uniformes",
    sub_collection="Droit Commercial Général",
    limit=10
)

for doc in results:
    print(doc['full_hierarchy_display'])
```

## Migration

### Appliquer la Migration SQL

```bash
# Se connecter à PostgreSQL
docker-compose -f docker-compose.prod.yml exec postgres psql -U ohada_user -d ohada

# Appliquer la migration
\i backend/db/migrations/002_add_collection_fields.sql
```

### Vérifier

```sql
-- Vérifier que les colonnes existent
\d documents

-- Devrait afficher:
-- collection          | character varying(100)  |
-- sub_collection      | character varying(200)  |
```

### Réimporter les Documents

Les documents déjà importés n'auront pas `collection` et `sub_collection`. Deux options:

**Option 1: Réimporter complètement**

```bash
# Supprimer les anciens documents
docker-compose exec postgres psql -U ohada_user -d ohada -c "DELETE FROM documents;"

# Réimporter avec la nouvelle version du parser
python backend/scripts/migrate_all_documents.py \
  --source-dir base_connaissances \
  --publish
```

**Option 2: Mettre à jour en place (UPDATE SQL)**

```sql
-- Pour les actes uniformes
UPDATE documents
SET
  collection = 'Actes Uniformes',
  sub_collection = split_part(metadata->>'file_path', '/', -2)
WHERE metadata->>'file_path' LIKE '%actes_uniformes%';

-- Pour le plan comptable
UPDATE documents
SET
  collection = 'Plan Comptable SYSCOHADA',
  sub_collection = CASE
    WHEN metadata->>'file_path' LIKE '%partie_1%' THEN 'Partie 1'
    WHEN metadata->>'file_path' LIKE '%partie_2%' THEN 'Partie 2'
    WHEN metadata->>'file_path' LIKE '%partie_3%' THEN 'Partie 3'
    WHEN metadata->>'file_path' LIKE '%partie_4%' THEN 'Partie 4'
  END
WHERE metadata->>'file_path' LIKE '%plan_comptable%';

-- Pour la présentation
UPDATE documents
SET
  collection = 'Présentation OHADA',
  sub_collection = NULL
WHERE metadata->>'file_path' LIKE '%presentation_ohada%';
```

## Test du Système

### Test 1: Parser

```bash
cd backend
python -c "
from src.document_parser import OhadaDocumentParser
from pathlib import Path

parser = OhadaDocumentParser()

# Test Acte Uniforme
path = Path('../base_connaissances/actes_uniformes/droit commercial général/Livre_1.docx')
if path.exists():
    doc = parser.parse_docx(str(path))
    print('Collection:', doc['collection'])
    print('Sub-collection:', doc['sub_collection'])
    assert doc['collection'] == 'Actes Uniformes'
    assert doc['sub_collection'] == 'Droit Commercial Général'
    print('✅ Test Acte Uniforme passed')
"
```

### Test 2: Import

```bash
python backend/scripts/import_document.py \
  base_connaissances/actes_uniformes/droit\ commercial\ général/Livre_1.docx \
  --publish

# Vérifier
docker-compose exec postgres psql -U ohada_user -d ohada \
  -c "SELECT collection, sub_collection, titre FROM documents ORDER BY created_at DESC LIMIT 1;"
```

### Test 3: Recherche Enrichie

```python
from src.retrieval.ohada_hybrid_retriever import create_ohada_query_api

api = create_ohada_query_api()
result = api.search_ohada_knowledge(
    query="droit commercial",
    n_results=3,
    include_sources=True
)

for source in result['sources']:
    m = source['metadata']
    print(f"Collection: {m['collection']}")
    print(f"Sub-collection: {m['sub_collection']}")
    print(f"Full hierarchy: {m['full_hierarchy_display']}")
    print()
```

## Statistiques par Collection

```sql
-- Vue d'ensemble
SELECT
  collection,
  COUNT(*) as total_docs,
  COUNT(DISTINCT sub_collection) as sub_collections,
  COUNT(CASE WHEN status = 'published' THEN 1 END) as published
FROM documents
WHERE is_latest = TRUE
GROUP BY collection
ORDER BY total_docs DESC;

-- Détail par sous-collection
SELECT
  collection,
  sub_collection,
  COUNT(*) as doc_count,
  MIN(created_at) as first_doc,
  MAX(updated_at) as last_update
FROM documents
WHERE is_latest = TRUE
GROUP BY collection, sub_collection
ORDER BY collection, sub_collection;
```

## Résumé

### Avant

- ❌ Hiérarchie organisationnelle non capturée
- ❌ Impossible de filtrer par collection
- ❌ Navigation par type de document difficile

### Après

- ✅ **Collection** et **sub_collection** extraits automatiquement du chemin
- ✅ **3 niveaux d'affichage** : collection, hiérarchie OHADA, hiérarchie complète
- ✅ **Filtrage** et **recherche** par collection
- ✅ **Extensible** pour futures collections (jurisprudence, doctrine, etc.)
- ✅ **Navigation** hiérarchique dans le frontend

---

**Version:** 1.0
**Date:** 2025-01-02
**Fichiers modifiés:**
- `backend/db/migrations/002_add_collection_fields.sql` (NEW)
- `backend/src/models/document.py`
- `backend/src/document_parser/parser.py`
- `backend/src/retrieval/postgres_metadata_enricher.py`
- `backend/scripts/import_document.py`
- `backend/scripts/migrate_all_documents.py`
