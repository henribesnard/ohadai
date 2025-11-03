# Comparaison des Modèles d'Embedding Open Source

## Critères pour OHADA
- ✅ Maximum de tokens (documents longs : 8k-130k chars)
- ✅ Excellente qualité pour le français
- ✅ Open source et local
- ✅ Performance optimale

## Top 3 Modèles Recommandés

### 🥇 1. BAAI/bge-m3 (RECOMMANDÉ)
```
Modèle: BAAI/bge-m3
Tokens max: 8192 tokens
Dimension: 1024
Langues: Multilingue (100+ langues, excellent français)
Performance: #1 sur MTEB multilingue
Taille: ~2.3 GB
License: MIT
```

**Avantages:**
- ✅ **8192 tokens** → Gère les longs documents OHADA
- ✅ **Multilingue state-of-the-art** → Excellent pour français juridique
- ✅ **Dimension 1024** → Bon compromis qualité/performance
- ✅ **#1 MTEB benchmark** → Meilleure qualité générale
- ✅ Support multi-fonctionnalité (dense, sparse, colBERT)

**Inconvénients:**
- ⚠️ Taille importante (~2.3 GB)

**Benchmark MTEB (français):**
- Retrieval: 55.4
- Classification: 69.8
- Clustering: 46.2

---

### 🥈 2. jinaai/jina-embeddings-v2-base-fr
```
Modèle: jinaai/jina-embeddings-v2-base-fr
Tokens max: 8192 tokens
Dimension: 768
Langues: Français optimisé
Performance: Excellent pour français
Taille: ~550 MB
License: Apache 2.0
```

**Avantages:**
- ✅ **8192 tokens** → Gère les longs documents
- ✅ **Optimisé français** → Spécifique domaine francophone
- ✅ Plus léger que BGE-M3
- ✅ Flash Attention 2 (rapide)

**Inconvénients:**
- ⚠️ Dimension 768 (vs 1024 pour BGE-M3)
- ⚠️ Moins polyvalent que BGE-M3

---

### 🥉 3. intfloat/multilingual-e5-large
```
Modèle: intfloat/multilingual-e5-large
Tokens max: 512 tokens
Dimension: 1024
Langues: Multilingue (94 langues)
Performance: Très bon pour français
Taille: ~2.2 GB
License: MIT
```

**Avantages:**
- ✅ Excellent qualité multilingue
- ✅ Dimension 1024
- ✅ Bien testé et stable

**Inconvénients:**
- ❌ **Seulement 512 tokens** → Nécessite chunking agressif
- ⚠️ Moins performant que BGE-M3

---

## 📊 Tableau Comparatif

| Modèle | Tokens Max | Dimension | Français | Taille | Vitesse |
|--------|-----------|-----------|----------|--------|---------|
| **BGE-M3** ⭐ | **8192** | 1024 | ⭐⭐⭐⭐⭐ | 2.3 GB | ⭐⭐⭐⭐ |
| Jina-v2-fr | 8192 | 768 | ⭐⭐⭐⭐⭐ | 550 MB | ⭐⭐⭐⭐⭐ |
| E5-large | 512 | 1024 | ⭐⭐⭐⭐ | 2.2 GB | ⭐⭐⭐ |

---

## ✅ Recommandation Finale : **BAAI/bge-m3**

### Pourquoi BGE-M3 pour OHADA ?

1. **Gestion des longs documents**
   - Documents OHADA : 3k-130k chars (~750-32k tokens)
   - BGE-M3 : 8192 tokens → Réduit le chunking

2. **Qualité française exceptionnelle**
   - Entraîné sur corpus multilingue massif
   - Performance état de l'art sur benchmark français

3. **Polyvalence**
   - Dense retrieval (recherche sémantique)
   - Sparse retrieval (BM25-like)
   - Multi-vector (colBERT-style)

4. **Production-ready**
   - Très utilisé en production
   - Excellente documentation
   - Support communautaire actif

### Configuration Recommandée

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer(
    'BAAI/bge-m3',
    device='cpu'  # ou 'cuda' si GPU disponible
)

# Pour documents longs
embeddings = model.encode(
    texts,
    batch_size=4,
    show_progress_bar=True,
    normalize_embeddings=True,  # Important pour similarité cosinus
    max_length=8192  # Utiliser toute la capacité
)
```

### Alternative pour ressources limitées

Si mémoire/CPU limitée → **jina-embeddings-v2-base-fr** :
- Plus léger (550 MB vs 2.3 GB)
- Plus rapide
- Toujours 8192 tokens

---

## 🚀 Prochaines Étapes

1. ✅ Installer sentence-transformers
2. ✅ Télécharger BGE-M3
3. ✅ Configurer ChromaDB avec BGE-M3
4. ✅ Créer pipeline de chunking (cibles : 2000-4000 tokens/chunk)
5. ✅ Vectoriser les 215 documents
6. ✅ Tester la recherche

## 📚 Sources

- MTEB Leaderboard: https://huggingface.co/spaces/mteb/leaderboard
- BGE-M3: https://huggingface.co/BAAI/bge-m3
- Jina v2: https://huggingface.co/jinaai/jina-embeddings-v2-base-fr
- E5: https://huggingface.co/intfloat/multilingual-e5-large
