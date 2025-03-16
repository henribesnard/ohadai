"""
Serveur API FastAPI pour le système OHADA Expert-Comptable.
Version étendue avec gestion des utilisateurs et conversations.
"""

from fastapi import FastAPI, BackgroundTasks, HTTPException, Query, Depends, Path, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, AsyncGenerator
import asyncio
import uvicorn
import uuid
import time
import json
import logging
import os
from datetime import datetime

# Import des modules OHADA
from src.config.ohada_config import LLMConfig
from src.retrieval.ohada_hybrid_retriever import create_ohada_query_api, OhadaHybridRetriever
from src.utils.ohada_utils import save_query_history, get_query_history, format_time
from src.utils.ohada_streaming import StreamingLLMClient, generate_streaming_response
from src.db.db_manager import DatabaseManager
from src.auth.auth_manager import AuthManager, create_auth_dependency

# Import du routeur de conversations
from src.api.conversations_api import router as conversations_router

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("ohada_api")

# Initialisation de l'API
app = FastAPI(
    title="OHADA Expert-Comptable API",
    description="API pour l'assistant d'expertise comptable OHADA avec gestion utilisateurs",
    version="1.1.0"
)

# Configuration CORS pour permettre les requêtes cross-origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialisation du gestionnaire de base de données
db_manager = DatabaseManager()

# Création de la dépendance d'authentification
get_current_user = create_auth_dependency(db_manager)

# Modèles de données pour l'API - Requêtes OHADA
class QueryRequest(BaseModel):
    query: str
    partie: Optional[int] = None
    chapitre: Optional[int] = None
    n_results: int = Field(default=5, ge=1, le=20)
    include_sources: bool = True
    stream: bool = False
    save_to_conversation: Optional[str] = None  # ID de conversation optionnel pour sauvegarder la requête

class QueryResponse(BaseModel):
    id: str
    query: str
    answer: str
    sources: Optional[List[Dict[str, Any]]] = None
    performance: Dict[str, float]
    timestamp: float
    conversation_id: Optional[str] = None
    user_message_id: Optional[str] = None
    ia_message_id: Optional[str] = None

# Modèles pour l'authentification
class GoogleAuthRequest(BaseModel):
    token: str

# Stockage en mémoire des requêtes en cours
ongoing_queries = {}

# Fonction pour récupérer l'instance du retriever API
def get_retriever():
    """Obtient ou crée l'instance de OhadaHybridRetriever"""
    if not hasattr(app, "retriever"):
        logger.info("Initialisation du retriever API")
        app.retriever = create_ohada_query_api()
    return app.retriever

#######################
# INCLUSION DES ROUTERS
#######################

# Inclusion du routeur de conversations
app.include_router(conversations_router)

#######################
# ROUTES PRINCIPALES
#######################

@app.get("/")
def read_root():
    """Point d'entrée principal de l'API"""
    return {
        "status": "online",
        "service": "OHADA Expert-Comptable API",
        "version": "1.1.0",
        "endpoints": {
            "query": "/query - Point d'entrée principal pour interroger l'assistant",
            "stream": "/stream - Point d'entrée pour les requêtes avec streaming",
            "history": "/history - Récupération de l'historique des questions/réponses",
            "auth": "/auth/* - Points d'entrée pour l'authentification",
            "conversations": "/conversations/* - Points d'entrée pour la gestion des conversations"
        }
    }

#######################
# ROUTES AUTHENTICATION
#######################

@app.post("/auth/google", response_model=Dict[str, Any])
async def google_auth(request: GoogleAuthRequest):
    """
    Authentification avec Google OAuth
    """
    try:
        # Créer une instance du gestionnaire d'authentification
        auth_manager = AuthManager(db_manager)
        
        # Vérifier le token Google
        user_info = await auth_manager.verify_google_token(request.token)
        
        # Créer ou mettre à jour l'utilisateur
        user = await auth_manager.create_or_update_user(user_info)
        
        # Retourner les informations utilisateur
        return {
            "user": user,
            "status": "success"
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'authentification: {str(e)}")

@app.get("/auth/me", response_model=Dict[str, Any])
async def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Récupère les informations de l'utilisateur actuellement authentifié
    """
    return current_user

#######################
# ROUTES OHADA QUERY
#######################

@app.post("/query", response_model=QueryResponse)
async def query_endpoint(
    request: QueryRequest, 
    background_tasks: BackgroundTasks,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """Endpoint pour interroger l'assistant OHADA"""
    retriever = get_retriever()
    
    if request.stream:
        # Rediriger vers le point d'entrée de streaming
        return StreamingResponse(
            stream_response(request, retriever, current_user),
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
        
        # Si l'utilisateur est authentifié et a spécifié une conversation, enregistrer dans la conversation
        user_message_id = None
        ia_message_id = None
        
        if current_user and request.save_to_conversation:
            conversation_id = request.save_to_conversation
            # Vérifier si la conversation existe et appartient à l'utilisateur
            conversation = db_manager.get_conversation(conversation_id)
            
            if conversation and conversation["user_id"] == current_user["user_id"]:
                # Ajouter la question et la réponse à la conversation
                user_message_id = db_manager.add_message(
                    conversation_id=conversation_id,
                    user_id=current_user["user_id"],
                    content=request.query,
                    is_user=True
                )
                
                ia_message_id = db_manager.add_message(
                    conversation_id=conversation_id,
                    user_id=current_user["user_id"],
                    content=result["answer"],
                    is_user=False,
                    metadata={
                        "performance": result.get("performance", {}),
                        "sources": result.get("sources", [])
                    }
                )
                
                # Mettre à jour la date de mise à jour de la conversation
                db_manager.update_conversation(conversation_id)
                
                # Ajouter les IDs à la réponse
                result["conversation_id"] = conversation_id
                result["user_message_id"] = user_message_id
                result["ia_message_id"] = ia_message_id
        
        # Sauvegarder dans l'historique de manière asynchrone (pour rétrocompatibilité)
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

async def stream_response(
    request: QueryRequest, 
    retriever: OhadaHybridRetriever, 
    current_user: Optional[Dict[str, Any]] = None
) -> AsyncGenerator[str, None]:
    """Générateur asynchrone pour le streaming des réponses"""
    # Générer un ID unique pour cette requête
    query_id = str(uuid.uuid4())
    ongoing_queries[query_id] = {"status": "processing", "completion": 0}
    
    # Variables pour enregistrement dans la conversation
    conversation_id = request.save_to_conversation if current_user else None
    user_message_id = None
    ia_message_id = None
    
    # Vérifier si la conversation existe et appartient à l'utilisateur
    if current_user and conversation_id:
        try:
            conversation = db_manager.get_conversation(conversation_id)
            if not conversation or conversation["user_id"] != current_user["user_id"]:
                conversation_id = None  # Ignorer si la conversation n'existe pas ou n'appartient pas à l'utilisateur
            else:
                # Ajouter la question à la conversation
                user_message_id = db_manager.add_message(
                    conversation_id=conversation_id,
                    user_id=current_user["user_id"],
                    content=request.query,
                    is_user=True
                )
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de la conversation: {e}")
            conversation_id = None
    
    # Événement de début avec ID et métadonnées
    start_data = {
        'id': query_id, 
        'query': request.query, 
        'timestamp': time.time()
    }
    if conversation_id:
        start_data['conversation_id'] = conversation_id
        start_data['user_message_id'] = user_message_id
    
    yield f"event: start\ndata: {json.dumps(start_data)}\n\n"
    
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
        
        # Enregistrer la réponse dans la conversation si nécessaire
        if current_user and conversation_id and user_message_id:
            try:
                ia_message_id = db_manager.add_message(
                    conversation_id=conversation_id,
                    user_id=current_user["user_id"],
                    content=answer,
                    is_user=False,
                    metadata={
                        "performance": {
                            "search_time_seconds": search_time,
                            "context_time_seconds": context_time,
                            "generation_time_seconds": generation_time,
                            "total_time_seconds": search_time + context_time + generation_time
                        },
                        "sources": sources
                    }
                )
                # Mettre à jour la date de mise à jour de la conversation
                db_manager.update_conversation(conversation_id)
            except Exception as e:
                logger.error(f"Erreur lors de l'enregistrement de la réponse dans la conversation: {e}")
        
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
        
        # Ajouter les informations de conversation si disponibles
        if conversation_id:
            final_response["conversation_id"] = conversation_id
            final_response["user_message_id"] = user_message_id
            final_response["ia_message_id"] = ia_message_id
        
        # Événement de complétion
        yield f"event: complete\ndata: {json.dumps(final_response)}\n\n"
        
        # Sauvegarder dans l'historique (pour rétrocompatibilité)
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
    include_sources: bool = Query(True, description="Inclure les sources dans la réponse"),
    save_to_conversation: Optional[str] = Query(None, description="ID de conversation à utiliser"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """Endpoint pour le streaming des réponses"""
    request = QueryRequest(
        query=query,
        partie=partie,
        chapitre=chapitre,
        n_results=n_results,
        include_sources=include_sources,
        stream=True,
        save_to_conversation=save_to_conversation
    )
    
    retriever = get_retriever()
    
    return StreamingResponse(
        stream_response(request, retriever, current_user),
        media_type="text/event-stream"
    )

@app.get("/history")
async def history_endpoint(
    limit: int = Query(10, ge=1, le=100),
    current_user: Optional[Dict[str, Any]] = None
):
    """Récupère l'historique des questions et réponses"""
    try:
        # Version simple pour la compatibilité avec l'existant
        # Si un utilisateur est connecté, on pourrait filtrer par utilisateur
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

#######################
# ROUTES ADMIN
#######################

@app.get("/admin/stats", response_model=Dict[str, Any])
async def get_db_stats(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Récupère des statistiques sur la base de données (réservé aux admins)
    """
    try:
        # Vérifier si l'utilisateur est admin (dans une vraie implémentation, ce serait stocké dans la BDD)
        admin_emails = os.getenv("ADMIN_EMAILS", "").split(",")
        if current_user["email"] not in admin_emails:
            raise HTTPException(status_code=403, detail="Accès non autorisé")
        
        # Récupérer les statistiques
        stats = db_manager.get_statistics()
        
        # Ajouter des métriques supplémentaires
        stats["active_queries"] = len(ongoing_queries)
        return stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des statistiques: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des statistiques")

#######################
# LANCEMENT DU SERVEUR
#######################

if __name__ == "__main__":
    # Lancer le serveur avec uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)