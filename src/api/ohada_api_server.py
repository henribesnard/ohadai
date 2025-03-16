"""
Serveur API FastAPI pour le système OHADA Expert-Comptable.
Inclut des endpoints pour les requêtes avec streaming des réponses.
"""

from fastapi import FastAPI, BackgroundTasks, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, AsyncGenerator
import asyncio
import uvicorn
import uuid
import time
import json
import logging
from datetime import datetime

# Import des modules OHADA
from src.config.ohada_config import LLMConfig
from src.retrieval.ohada_hybrid_retriever import create_ohada_query_api, OhadaHybridRetriever
from src.utils.ohada_utils import save_query_history, get_query_history, format_time
from src.utils.ohada_streaming import StreamingLLMClient, generate_streaming_response

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("ohada_api")

# Initialisation de l'API
app = FastAPI(
    title="OHADA Expert-Comptable API",
    description="API pour l'assistant d'expertise comptable OHADA",
    version="1.0.0"
)

# Configuration CORS pour permettre les requêtes cross-origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modèles de données pour l'API
class QueryRequest(BaseModel):
    query: str
    partie: Optional[int] = None
    chapitre: Optional[int] = None
    n_results: int = Field(default=5, ge=1, le=20)
    include_sources: bool = True
    stream: bool = False

class QueryResponse(BaseModel):
    id: str
    query: str
    answer: str
    sources: Optional[List[Dict[str, Any]]] = None
    performance: Dict[str, float]
    timestamp: float

# Stockage en mémoire des requêtes en cours (pour démonstration - à remplacer par une solution plus robuste en production)
ongoing_queries = {}

# Fonction pour récupérer l'instance du retriever API
def get_retriever():
    """Obtient ou crée l'instance de OhadaHybridRetriever"""
    if not hasattr(app, "retriever"):
        logger.info("Initialisation du retriever API")
        app.retriever = create_ohada_query_api()
    return app.retriever

@app.get("/")
def read_root():
    """Point d'entrée principal de l'API"""
    return {
        "status": "online",
        "service": "OHADA Expert-Comptable API",
        "version": "1.0.0",
        "endpoints": {
            "query": "/query - Point d'entrée principal pour interroger l'assistant",
            "stream": "/stream - Point d'entrée pour les requêtes avec streaming",
            "history": "/history - Récupération de l'historique des questions/réponses"
        }
    }

@app.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest, background_tasks: BackgroundTasks):
    """Endpoint pour interroger l'assistant OHADA"""
    retriever = get_retriever()
    
    if request.stream:
        # Rediriger vers le point d'entrée de streaming
        return StreamingResponse(
            stream_response(request, retriever),
            media_type="text/event-stream"
        )
    
    # Traitement sans streaming
    start_time = time.time()
    
    try:
        # Exécuter la recherche
        logger.info(f"Requête reçue: {request.query}")
        
        result = retriever.search_ohada_knowledge(
            query=request.query,
            partie=request.partie,
            chapitre=request.chapitre,
            n_results=request.n_results,
            include_sources=request.include_sources
        )
        
        # Ajouter un ID unique et horodatage
        query_id = str(uuid.uuid4())
        result["id"] = query_id
        result["query"] = request.query
        result["timestamp"] = time.time()
        
        # Sauvegarder dans l'historique de manière asynchrone
        background_tasks.add_task(
            save_query_history,
            request.query,
            result["answer"],
            {"performance": result.get("performance", {})}
        )
        
        logger.info(f"Requête traitée en {time.time() - start_time:.2f} secondes")
        return result
        
    except Exception as e:
        logger.error(f"Erreur lors du traitement de la requête: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def stream_response(request: QueryRequest, retriever: OhadaHybridRetriever) -> AsyncGenerator[str, None]:
    """Générateur asynchrone pour le streaming des réponses"""
    # Générer un ID unique pour cette requête
    query_id = str(uuid.uuid4())
    ongoing_queries[query_id] = {"status": "processing", "completion": 0}
    
    # Événement de début avec ID et métadonnées
    yield f"event: start\ndata: {json.dumps({'id': query_id, 'query': request.query, 'timestamp': time.time()})}\n\n"
    
    try:
        # Étape 1: Recherche des documents pertinents
        yield f"event: progress\ndata: {json.dumps({'status': 'retrieving', 'completion': 0.1})}\n\n"
        
        # Exécuter la recherche (non streamée)
        search_start = time.time()
        search_results = retriever.search_hybrid(
            query=request.query,
            partie=request.partie,
            chapitre=request.chapitre,
            n_results=request.n_results,
            rerank=True
        )
        search_time = time.time() - search_start
        
        # Mise à jour du statut
        yield f"event: progress\ndata: {json.dumps({'status': 'analyzing', 'completion': 0.3})}\n\n"
        
        # Étape 2: Génération du contexte
        context_start = time.time()
        # Utiliser le processeur de contexte via l'attribut context_processor
        context = retriever.context_processor.summarize_context(
            query=request.query, 
            search_results=search_results
        )
        context_time = time.time() - context_start
        
        # Mise à jour du statut
        yield f"event: progress\ndata: {json.dumps({'status': 'generating', 'completion': 0.4})}\n\n"
        
        # Étape 3: Générer la réponse avec streaming
        llm_config = retriever.llm_config
        streaming_client = StreamingLLMClient(llm_config)
        
        # Préparer les sources pour l'inclure dans la réponse finale
        sources = []
        if request.include_sources:
            # Utiliser l'attribut context_processor pour préparer les sources
            sources = retriever.context_processor.prepare_sources(search_results)
        
        # Générer la réponse avec streaming
        generation_start = time.time()
        completion = 0.4  # Progression de départ pour la génération
        
        # Système de prompt et prompt utilisateur
        system_prompt = "Vous êtes un expert-comptable spécialisé dans le plan comptable OHADA. N'utilisez jamais de notation mathématique LaTeX ou de formules entre crochets."
        user_prompt = f"""
        Question: {request.query}
        
        Contexte:
        {context}
        
        Répondez à la question de manière claire, précise et structurée en vous basant sur le contexte fourni.
        """
        
        answer_chunks = []
        async for chunk in generate_streaming_response(streaming_client, system_prompt, user_prompt):
            answer_chunks.append(chunk)
            
            # Mettre à jour la progression (de 0.4 à 0.9)
            completion += 0.01
            if completion > 0.9:
                completion = 0.9
                
            # Envoyer le chunk au client
            yield f"event: chunk\ndata: {json.dumps({'text': chunk, 'completion': completion})}\n\n"
            
            # Petite pause pour simuler un temps de génération naturel
            await asyncio.sleep(0.01)
        
        # Assembler la réponse complète
        answer = "".join(answer_chunks)
        generation_time = time.time() - generation_start
        
        # Préparer la réponse finale
        total_time = search_time + context_time + generation_time
        final_response = {
            "id": query_id,
            "query": request.query,
            "answer": answer,
            "sources": sources if request.include_sources else None,
            "performance": {
                "search_time_seconds": search_time,
                "context_time_seconds": context_time,
                "generation_time_seconds": generation_time,
                "total_time_seconds": total_time
            },
            "timestamp": time.time()
        }
        
        # Événement de complétion
        yield f"event: complete\ndata: {json.dumps(final_response)}\n\n"
        
        # Sauvegarder dans l'historique
        save_query_history(
            request.query,
            answer,
            {"performance": final_response["performance"]}
        )
        
        # Mettre à jour le statut de la requête
        ongoing_queries[query_id] = {"status": "complete", "completion": 1.0}
        
    except Exception as e:
        logger.error(f"Erreur pendant le streaming: {e}")
        error_response = {
            "error": str(e),
            "id": query_id,
            "query": request.query,
            "timestamp": time.time()
        }
        yield f"event: error\ndata: {json.dumps(error_response)}\n\n"
        ongoing_queries[query_id] = {"status": "error", "completion": 0, "error": str(e)}
    
    finally:
        # Nettoyage après un certain temps
        await asyncio.sleep(300)  # 5 minutes
        if query_id in ongoing_queries:
            del ongoing_queries[query_id]

@app.get("/stream")
async def stream_endpoint(
    query: str = Query(..., description="Question à poser"),
    partie: Optional[int] = Query(None, description="Numéro de partie (optionnel)"),
    chapitre: Optional[int] = Query(None, description="Numéro de chapitre (optionnel)"),
    n_results: int = Query(5, ge=1, le=20, description="Nombre de résultats à considérer"),
    include_sources: bool = Query(True, description="Inclure les sources dans la réponse")
):
    """Endpoint pour le streaming des réponses"""
    request = QueryRequest(
        query=query,
        partie=partie,
        chapitre=chapitre,
        n_results=n_results,
        include_sources=include_sources,
        stream=True
    )
    
    retriever = get_retriever()
    
    return StreamingResponse(
        stream_response(request, retriever),
        media_type="text/event-stream"
    )

@app.get("/history")
async def history_endpoint(limit: int = Query(10, ge=1, le=100)):
    """Récupère l'historique des questions et réponses"""
    try:
        history = get_query_history(limit)
        return {"history": history, "count": len(history)}
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de l'historique: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{query_id}")
async def status_endpoint(query_id: str):
    """Récupère le statut d'une requête en cours"""
    if query_id in ongoing_queries:
        return ongoing_queries[query_id]
    else:
        raise HTTPException(status_code=404, detail="Requête non trouvée")

if __name__ == "__main__":
    # Lancer le serveur avec uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)