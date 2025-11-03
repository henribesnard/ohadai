# Corrections pour utiliser BGE-M3 comme modèle d'embedding

## Résumé des problèmes trouvés

Le système était configuré pour utiliser **BGE-M3** (dimension 1024) mais le code avait de nombreuses valeurs hardcodées qui utilisaient `text-embedding-3-small` (dimension 1536) ou `all-MiniLM-L6-v2` (dimension 384).

## Fichiers corrigés

### 1. `backend/src/utils/ohada_clients.py`

**Ligne 40** - Initialisation du client LLM :
- ❌ Avant : `embedding_model = "text-embedding-3-small"` (hardcodé)
- ✅ Après : Utilise le modèle configuré via `self.config.get_embedding_model()`

**Ligne 156** - Génération d'embedding :
- ❌ Avant : `model_to_use = "text-embedding-3-small"` (hardcodé)
- ✅ Après : Utilise `embedding_model` depuis la configuration

**Ligne 210** - Dimension par défaut :
- ❌ Avant : `default_dimension = 1536` (hardcodé)
- ✅ Après : Récupère la dimension depuis la configuration (1024 pour BGE-M3)

### 2. `backend/src/vector_db/ohada_vector_db_structure.py`

**Ligne 56** - Modèle par défaut en test :
- ❌ Avant : `model_name = "all-MiniLM-L6-v2"`
- ✅ Après : `model_name = "BAAI/bge-m3"`

**Ligne 69** - Dimension d'embedding :
- ❌ Avant : Seulement support pour Qwen (1536) et all-MiniLM (384)
- ✅ Après : Ajout du support BGE-M3 (1024)

### 3. `backend/src/main.py`

**Ligne 443** - Préchargement du modèle :
- ❌ Avant : `embedding_model = "text-embedding-3-small"` (hardcodé)
- ✅ Après : Utilise `OhadaEmbedder()` sans spécifier le modèle (auto-détection)

### 4. `backend/src/retrieval/ohada_hybrid_retriever.py`

**Lignes 587-590** - Fonction `create_ohada_query_api` :
- ❌ Avant : `embedding_model = "text-embedding-3-small"` (hardcodé en test et production)
- ✅ Après : Récupère le modèle depuis `llm_config.get_embedding_model()`

### 5. `backend/.env`

**Configuration des clés API** :
- ✅ Ajout de toutes les clés API (OPENAI_API_KEY, DEEPSEEK_API_KEY, etc.)

### 6. `backend/src/retrieval/ohada_hybrid_retriever.py`

**Ligne 93** - Chemin ChromaDB :
- ❌ Avant : `path="backend/chroma_db"` (mauvais quand le serveur tourne depuis backend/)
- ✅ Après : `path="chroma_db"` (chemin relatif correct)

## Vérifications effectuées

✅ **Configuration YAML** : BGE-M3 est bien configuré dans `llm_config_test.yaml`
```yaml
local_embedding:
  enabled: true
  local: true
  models:
    embedding: "BAAI/bge-m3"
  parameters:
    dimensions: 1024
```

✅ **Collection ChromaDB** : La collection `ohada_documents` existe avec 699 documents
✅ **Dimension des embeddings** : Les documents ont des embeddings de dimension **1024** (BGE-M3)

## Configuration finale

- **Modèle d'embedding en test** : `BAAI/bge-m3` (dimension 1024)
- **Modèle d'embedding en production** : `Alibaba-NLP/gte-Qwen2-1.5B-instruct` (dimension 1536)
- **Fallback OpenAI** : `text-embedding-3-small` (dimension 1536)

## Pour tester

1. Redémarrer le serveur backend :
   ```bash
   cd backend
   start.bat
   ```

2. Tester une requête :
   ```bash
   curl -X POST "http://localhost:8000/query" \
     -H "Content-Type: application/json" \
     -d '{"query": "Qu'\''est-ce que l'\''amortissement dans le SYSCOHADA?", "n_results": 3}'
   ```

3. Vérifier dans les logs que le modèle BGE-M3 est bien utilisé
