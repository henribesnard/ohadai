# Architecture du Backend OHADA Expert-Comptable

## Vue d'ensemble

Le projet OHADA Expert-Comptable est un système d'assistance intelligent spécialisé dans le plan comptable OHADA. L'architecture backend est conçue de façon modulaire pour assurer la flexibilité, la maintenabilité et la performance.

## Structure des fichiers

```
ohada-expert-comptable/
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── ohada_api_server.py        # Serveur FastAPI principal
│   │   ├── conversations_api.py        # API de gestion des conversations
│   │   └── auth_routes.py             # Routes d'authentification
│   │
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── auth_manager.py            # Gestion de l'authentification
│   │   ├── auth_models.py             # Modèles Pydantic pour l'auth
│   │   ├── jwt_manager.py             # Gestion des JWT
│   │   └── password_utils.py          # Utilitaires pour les mots de passe
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   ├── ohada_config.py            # Configuration des modèles LLM
│   │   ├── llm_config_production.yaml # Config pour l'environnement de production
│   │   └── llm_config_test.yaml       # Config pour l'environnement de test
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   └── db_manager.py              # Gestion de la BDD SQLite
│   │
│   ├── generation/
│   │   ├── __init__.py
│   │   ├── response_generator.py      # Génération de réponses
│   │   ├── streaming_generator.py     # Génération en streaming
│   │   ├── query_reformulator.py      # Reformulation des requêtes
│   │   └── intent_classifier.py       # Classification des intentions
│   │
│   ├── retrieval/
│   │   ├── __init__.py
│   │   ├── ohada_hybrid_retriever.py  # Récupérateur hybride principal
│   │   ├── vector_retriever.py        # Recherche vectorielle
│   │   ├── bm25_retriever.py          # Recherche BM25 (lexicale)
│   │   ├── cross_encoder_reranker.py  # Reranking des résultats
│   │   └── context_processor.py       # Traitement du contexte
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── ohada_clients.py           # Clients LLM (OpenAI, etc.)
│   │   ├── ohada_streaming.py         # Utilitaires de streaming
│   │   ├── ohada_cache.py             # Gestion du cache (embeddings, etc.)
│   │   └── ohada_utils.py             # Utilitaires généraux
│   │
│   ├── vector_db/
│   │   ├── __init__.py
│   │   ├── ohada_vector_db_structure.py  # Structure de la BDD vectorielle
│   │   └── ohada_document_ingestor.py    # Ingestion de documents
│   │
│   └── __init__.py
│
├── ohada_app.py                       # Interface Streamlit
├── ohada.py                           # Script principal CLI
├── main.py                            # Point d'entrée pour CLI
├── start.sh                           # Script de démarrage
├── Dockerfile                         # Configuration Docker
└── docker-compose.yml                 # Orchestration Docker
```

## Flux de traitement d'une question

### 1. Réception de la question

L'entrée se fait par trois canaux principaux:

- API REST (`ohada_api_server.py`) - Endpoint `/query`
- Interface Streamlit (`ohada_app.py`)
- CLI (`main.py`)

**Code principal dans `ohada_api_server.py`:**
```python
@app.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest, background_tasks: BackgroundTasks, current_user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    # Traitement de la requête
    retriever = get_retriever()
    result = retriever.search_ohada_knowledge(
        query=request.query,
        partie=request.partie,
        chapitre=request.chapitre,
        n_results=request.n_results,
        include_sources=request.include_sources
    )
    # ...
```

### 2. Analyse d'intention

L'analyseur d'intention détermine si la question est purement informative ou conversationnelle.

**Code dans `intent_classifier.py`:**
```python
class LLMIntentAnalyzer:
    # ...
    def analyze_intent(self, query: str) -> Tuple[str, Dict[str, Any]]:
        # Prompt pour classifier l'intention
        system_prompt = """
        Tu es un assistant spécialisé dans l'analyse d'intention des questions utilisateur.
        
        Ta tâche est de classifier les questions en différentes catégories:
        - "greeting": Salutations comme "bonjour", "salut", etc.
        - "identity": Questions sur l'identité ou les capacités de l'assistant.
        - "smalltalk": Conversations générales comme remerciements, questions de courtoisie.
        - "technical": Questions techniques qui nécessitent des connaissances spécifiques.
        # ...
```

### 3. Reformulation de la requête

Pour les requêtes techniques, le système optimise la question pour la recherche.

**Code dans `query_reformulator.py`:**
```python
class QueryReformulator:
    # ...
    def reformulate(self, query: str) -> str:
        # Pour les requêtes courtes (moins de 100 caractères), pas besoin de reformulation
        if len(query) < 100:
            return query
            
        # Utiliser le LLM pour reformuler la requête
        prompt = f"""
        Vous êtes un assistant spécialisé dans la recherche d'informations sur le plan comptable OHADA.
        Votre tâche est de reformuler la question suivante pour maximiser les chances de trouver 
        des informations pertinentes dans une base de données. # ...
```

### 4. Recherche hybride

Le cœur du système est la recherche hybride qui combine recherche lexicale (BM25) et sémantique (vectorielle).

**Code dans `ohada_hybrid_retriever.py`:**
```python
def search_hybrid(self, query: str, collection_name: str = None, partie: int = None,
                chapitre: int = None, n_results: int = 10, rerank: bool = True) -> List[Dict[str, Any]]:
    # Déterminer les collections à utiliser
    collections = self.determine_search_collections(query, collection_name, partie)
    
    # Exécuter les recherches BM25 et vectorielle en parallèle
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        
        # Générer l'embedding de la requête (pour la recherche vectorielle)
        embedding_future = executor.submit(
           self.vector_retriever.get_embedding, 
           query, 
           self.llm_client.generate_embedding
        )
        
        # Lancer la recherche BM25 pour chaque collection
        for coll in collections:
           # ...
        
        # Attendre l'embedding
        query_embedding = embedding_future.result()
        
        # Lancer la recherche vectorielle pour chaque collection
        # ...
    
    # Déduplication des résultats par ID de document
    # ...
    
    # Appliquer le reranking si demandé
    if rerank and candidates:
        # ...
```

#### 4.1 Recherche BM25

**Code dans `bm25_retriever.py`:**
```python
def search(self, collection_name: str, query: str, filter_dict: Dict, 
          n_results: int, documents_provider=None) -> List[Dict[str, Any]]:
    # ...
    bm25_index, doc_mapping = self.get_or_create_index(collection_name, documents_provider)
    if bm25_index:
        # Tokeniser la requête avec NLTK
        tokenized_query = word_tokenize(query.lower())
        
        # Récupérer les scores BM25
        bm25_scores = bm25_index.get_scores(tokenized_query)
        
        # Récupérer les meilleurs résultats BM25
        # ...
```

#### 4.2 Recherche vectorielle

**Code dans `vector_retriever.py`:**
```python
def search(self, collection_name: str, query_embedding: List[float], 
          filter_dict: Dict, n_results: int) -> List[Dict[str, Any]]:
    # ...
    vector_results = self.vector_db.query(
        collection_name=collection_name,
        query_embedding=query_embedding,
        filter_dict=filter_dict if filter_dict else None,
        n_results=n_results*2  # Doubler pour avoir plus de candidats
    )
    # ...
```

#### 4.3 Reranking

**Code dans `cross_encoder_reranker.py`:**
```python
def rerank(self, query: str, candidates: List[Dict[str, Any]], top_k: int = None) -> List[Dict[str, Any]]:
    # ...
    # Préparer les paires (requête, passage) pour le cross-encoder
    pairs = [(query, doc["text"]) for doc in candidates_to_rerank]
    
    # Obtenir les scores du cross-encoder
    cross_scores = cross_encoder.predict(pairs)
    
    # Mettre à jour les scores
    for i, score in enumerate(cross_scores):
        # ...
        # Combinaison finale: 30% BM25, 30% vectoriel, 40% cross-encoder
        candidates_to_rerank[i]["final_score"] = (
            candidates_to_rerank[i]["bm25_score"] * 0.3 +
            candidates_to_rerank[i]["vector_score"] * 0.3 +
            candidates_to_rerank[i]["cross_score"] * 0.4
        )
    # ...
```

### 5. Traitement du contexte

Le processeur de contexte prépare les informations récupérées pour la génération de réponse.

**Code dans `context_processor.py`:**
```python
def summarize_context(self, query: str, search_results: List[Dict[str, Any]], 
                     max_tokens: int = 1800) -> str:
    # ...
    # Construire un contexte contenant les extraits les plus pertinents
    context_parts = []
    
    # Estimation grossière des tokens (environ 4 caractères par token)
    current_length = 0
    max_chars = max_tokens * 4
    
    for i, result in enumerate(search_results):
        # Extraire les métadonnées essentielles
        # ...
        
        # Calcul approximatif des caractères
        entry_text = f"Document {i+1} (score: {result['relevance_score']:.2f}):\n{metadata_str}\n{result['text']}\n\n"
        # ...
```

### 6. Génération de la réponse

Le générateur de réponse analyse le contexte et produit une réponse cohérente.

**Code dans `response_generator.py`:**
```python
def generate_response(self, query: str, context: str) -> str:
    # ...
    # Étape 1: Analyse du contexte pour extraire les informations pertinentes
    analysis_prompt = f"""
    Vous êtes un expert-comptable spécialisé dans le plan comptable OHADA.
    
    Analysez d'abord le contexte suivant pour extraire les informations pertinentes à la question posée.
    Identifiez les concepts clés, les règles et les procédures comptables qui s'appliquent.
    
    Question: {query}
    
    Contexte:
    {context}
    
    Votre analyse:
    """
    
    # Génération de l'analyse
    analysis = self.llm_client.generate_response(
        system_prompt="Analysez le contexte et extrayez les informations pertinentes pour répondre à la question.",
        user_prompt=analysis_prompt,
        max_tokens=800,
        temperature=0.3
    )
    
    # Étape 2: Génération de la réponse basée sur l'analyse
    answer_prompt = f"""
    Vous êtes un expert-comptable spécialisé dans le plan comptable OHADA.
    
    Voici votre analyse des informations disponibles sur la question:
    {analysis}
    
    Maintenant, répondez à la question de manière claire, précise et structurée:
    {query}
    # ...
```

Pour le streaming, le code est similaire mais envoie des morceaux progressifs via `streaming_generator.py`.

### 7. Clients LLM et accès aux modèles

Le module `ohada_clients.py` unifie l'accès aux différents fournisseurs de modèles de langage.

```python
def generate_response(self, system_prompt: str, user_prompt: str, 
                     max_tokens: int = None, temperature: float = None) -> str:
    # ...
    # Utiliser la liste de priorité pour les réponses
    provider_list = self.config.get_provider_list()
    
    # Essayer chaque fournisseur dans l'ordre
    for provider in provider_list:
        provider_config = self.config.get_provider_config(provider)
        # ...
        
        response = client.chat.completions.create(
            model=response_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            **params  # Autres paramètres spécifiques au fournisseur
        )
        # ...
```

### 8. Base de données vectorielle

La base vectorielle stocke les documents et leurs embeddings pour permettre une recherche sémantique efficace.

**Code dans `ohada_vector_db_structure.py`:**
```python
def query(self, 
         collection_name: str = "chapitres",  # Par défaut, chercher dans les chapitres
         query_text: str = None, 
         query_embedding: List[float] = None,
         filter_dict: Dict[str, Any] = None,
         n_results: int = 5):
    # ...
    # Exécuter la requête
    results = self.collections[collection_name].query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=filter_dict,
        include=["documents", "metadatas", "distances"]
    )
    # ...
```

## Gestion des configurations

Le système utilise une configuration flexible pour s'adapter à différents environnements (test/production).

**Code dans `ohada_config.py`:**
```python
class LLMConfig:
    def _load_config(self) -> Dict[str, Any]:
        # Vérifier l'environnement d'exécution
        environment = os.getenv("OHADA_ENV", "test")
        
        # Déterminer le chemin du fichier de configuration
        if environment == "production":
            config_file = "llm_config_production.yaml"
        else:
            config_file = "llm_config_test.yaml"
        # ...
```

## Gestion des utilisateurs et persistance

Le système inclut une gestion complète des utilisateurs et des conversations.

**Code dans `db_manager.py`:**
```python
def add_message(self, conversation_id: str, user_id: str, content: str, 
               is_user: bool, metadata: Dict[str, Any] = None) -> Optional[str]:
    # Générer un ID pour le message
    message_id = str(uuid.uuid4())
    
    # Convertir les métadonnées en JSON si présentes
    metadata_json = json.dumps(metadata) if metadata else None
    
    # ...
```

## Conclusion

Cette architecture modulaire permet:

1. Une séparation claire des responsabilités
2. Une flexibilité dans le choix des fournisseurs LLM
3. Une robustesse via des mécanismes de fallback
4. Une adaptabilité à différents environnements
5. Une extensibilité pour ajouter de nouvelles fonctionnalités

Le projet utilise des techniques modernes de RAG (Retrieval-Augmented Generation) et une approche hybride de la recherche pour fournir des réponses précises sur le domaine spécialisé qu'est le plan comptable OHADA.
