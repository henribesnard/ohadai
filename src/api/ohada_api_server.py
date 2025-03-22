"""
Serveur API FastAPI pour le système OHADA Expert-Comptable.
Version optimisée pour les environnements de production et test.
"""

import os
import asyncio
import time
import json
import logging
import uuid
from typing import List, Dict, Any, Optional, Tuple, AsyncGenerator
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, BackgroundTasks, HTTPException, Query, Depends, Path as PathParam, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import uvicorn

# Import des modules OHADA
from src.config.ohada_config import LLMConfig
from src.retrieval.ohada_hybrid_retriever import create_ohada_query_api, OhadaHybridRetriever
from src.utils.ohada_utils import save_query_history, get_query_history, format_time
from src.utils.ohada_streaming import StreamingLLMClient, generate_streaming_response
from src.db.db_manager import DatabaseManager
from src.auth.auth_manager import create_auth_dependency
from src.auth.jwt_manager import JWTManager
from src.generation.intent_classifier import LLMIntentAnalyzer

# Import des routeurs
from src.api.conversations_api import router as conversations_router
from src.api.auth_routes import router as auth_router

# Déterminer l'environnement
ENVIRONMENT = os.getenv("OHADA_ENV", "test")
CONFIG_PATH = os.getenv("OHADA_CONFIG_PATH", "./src/config")

# Configuration du logging
logging.basicConfig(
    level=logging.INFO if ENVIRONMENT == "production" else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"ohada_api_{ENVIRONMENT}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ohada_api")

logger.info(f"Démarrage du serveur API en environnement: {ENVIRONMENT}")
logger.info(f"Utilisation du chemin de configuration: {CONFIG_PATH}")

# Initialisation de l'API
app = FastAPI(
    title="OHADA Expert-Comptable API",
    description="API pour l'assistant d'expertise comptable OHADA avec authentification interne",
    version="1.3.0"
)

# Configuration CORS pour permettre les requêtes cross-origin
origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialisation du gestionnaire de base de données
DB_PATH = os.getenv("OHADA_DB_PATH", "./data/ohada_users.db")
db_manager = DatabaseManager(db_path=DB_PATH)

# Initialisation du gestionnaire JWT
JWT_SECRET = os.getenv("JWT_SECRET_KEY")
jwt_manager = JWTManager(db_manager, secret_key=JWT_SECRET)

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
    create_conversation: bool = True  # Nouveau paramètre pour contrôler la création automatique de conversation

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

# Stockage en mémoire des requêtes en cours
ongoing_queries = {}

# Fonction pour récupérer l'instance du retriever API
def get_retriever():
    """Obtient ou crée l'instance de OhadaHybridRetriever"""
    if not hasattr(app, "retriever"):
        logger.info("Initialisation du retriever API")
        app.retriever = create_ohada_query_api(config_path=CONFIG_PATH)
    return app.retriever

# Fonction pour authentifier via token (pour les endpoints SSE)
def authenticate_via_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Authentifie un utilisateur via un token JWT
    
    Args:
        token: Token JWT
        
    Returns:
        Informations utilisateur ou None si authentification échouée
    """
    try:
        payload = jwt_manager.decode_token(token)
        user_id = payload.get("sub")
        if user_id:
            return db_manager.get_user(user_id)
        return None
    except Exception as e:
        logger.error(f"Erreur lors de l'authentification via token: {e}")
        return None

# Fonction pour créer ou vérifier une conversation
def ensure_conversation(user_id: str, conversation_id: Optional[str], query: str) -> Tuple[str, bool]:
    """
    Vérifie qu'une conversation existe et appartient à l'utilisateur, ou en crée une nouvelle
    
    Args:
        user_id: ID de l'utilisateur
        conversation_id: ID de conversation (optionnel)
        query: Requête pour générer un titre si nécessaire
        
    Returns:
        Tuple (conversation_id, created_new) où created_new est True si une nouvelle conversation a été créée
    """
    # Si un ID de conversation est fourni, vérifier qu'il existe et appartient à l'utilisateur
    if conversation_id:
        conversation = db_manager.get_conversation(conversation_id)
        if conversation and conversation["user_id"] == user_id:
            return conversation_id, False
    
    # Créer une nouvelle conversation
    title = query[:50] + "..." if len(query) > 50 else query
    new_conversation_id = db_manager.create_conversation(user_id=user_id, title=title)
    logger.info(f"Nouvelle conversation créée pour l'utilisateur {user_id}: {new_conversation_id}")
    return new_conversation_id, True

# Fonction pour analyser l'intention d'une requête
def analyze_intent(query: str) -> Tuple[str, Dict[str, Any], Optional[str]]:
    """
    Analyse l'intention d'une requête et génère une réponse directe si nécessaire
    
    Args:
        query: Requête de l'utilisateur
    
    Returns:
        Tuple (intention, métadonnées, réponse directe ou None)
    """
    # Récupérer le retriever et le config
    retriever = get_retriever()
    llm_config = retriever.llm_config
    
    # Récupérer la configuration de l'assistant
    assistant_config = llm_config.get_assistant_personality()
    
    # Initialiser l'analyseur d'intention
    intent_analyzer = LLMIntentAnalyzer(
        llm_client=retriever.llm_client,
        assistant_config=assistant_config
    )
    
    # Analyser l'intention de la requête
    intent, metadata = intent_analyzer.analyze_intent(query)
    logger.info(f"Intention détectée: {intent} (confidence: {metadata.get('confidence', 0)})")
    
    # Enrichir les métadonnées avec la requête originale pour référence future
    metadata["query"] = query
    
    # Générer une réponse directe si nécessaire
    direct_response = intent_analyzer.generate_response(intent, metadata)
    
    return intent, metadata, direct_response

#######################
# INCLUSION DES ROUTERS
#######################

# Inclusion du routeur de conversations
app.include_router(conversations_router)

# Inclusion du routeur d'authentification
app.include_router(auth_router)

#######################
# ROUTES PRINCIPALES
#######################

@app.get("/")
def read_root():
    """Point d'entrée principal de l'API"""
    return {
        "status": "online",
        "service": "OHADA Expert-Comptable API",
        "version": "1.3.0",
        "environment": ENVIRONMENT,
        "endpoints": {
            "query": "/query - Point d'entrée principal pour interroger l'assistant",
            "stream": "/stream - Point d'entrée pour les requêtes avec streaming",
            "history": "/history - Récupération de l'historique des questions/réponses",
            "auth": "/auth/* - Points d'entrée pour l'authentification",
            "conversations": "/conversations/* - Points d'entrée pour la gestion des conversations"
        }
    }

@app.get("/status")
def status_endpoint():
    """Endpoint pour vérifier l'état du service"""
    # Vérifier que les bases vectorielles sont chargées
    retriever = get_retriever()
    
    stats = {
        "status": "online",
        "environment": ENVIRONMENT,
        "timestamp": datetime.now().isoformat(),
        "databases": {},
        "models": {}
    }
    
    # Obtenir les statistiques des collections
    try:
        vector_stats = retriever.vector_db.get_collection_stats()
        stats["databases"]["vector_db"] = {
            "status": "online",
            "collections": {
                name: data.get("count", 0) for name, data in vector_stats.items() 
                if "error" not in data
            }
        }
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des statistiques vectorielles: {e}")
        stats["databases"]["vector_db"] = {"status": "error", "message": str(e)}
    
    # Obtenir les informations sur les modèles utilisés
    try:
        provider_name, model_name, _ = retriever.llm_config.get_response_model()
        embedding_provider, embedding_model, _ = retriever.llm_config.get_embedding_model()
        
        stats["models"]["llm"] = {
            "provider": provider_name,
            "model": model_name
        }
        
        stats["models"]["embedding"] = {
            "provider": embedding_provider,
            "model": embedding_model
        }
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des informations sur les modèles: {e}")
        stats["models"] = {"status": "error", "message": str(e)}
    
    # Obtenir les statistiques de base de données relationnelle
    try:
        db_stats = db_manager.get_statistics()
        stats["databases"]["sql"] = {"status": "online", **db_stats}
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des statistiques de base de données: {e}")
        stats["databases"]["sql"] = {"status": "error", "message": str(e)}
    
    return stats

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
        # Gérer la conversation - S'assurer qu'une conversation existe si l'utilisateur est authentifié
        conversation_id = request.save_to_conversation
        user_message_id = None
        ia_message_id = None
        
        if current_user and request.create_conversation:
            # Créer ou vérifier une conversation
            conversation_id, is_new = ensure_conversation(
                user_id=current_user["user_id"],
                conversation_id=conversation_id,
                query=request.query
            )
            request.save_to_conversation = conversation_id  # Mettre à jour l'ID de conversation

        # Analyser l'intention pour déterminer si c'est une requête conversationnelle
        intent, metadata, direct_response = analyze_intent(request.query)
        
        # Si une réponse directe est disponible, l'utiliser sans passer par la recherche
        if direct_response:
            logger.info(f"Réponse directe générée pour l'intention: {intent}")
            result = {
                "answer": direct_response,
                "performance": {
                    "intent_analysis_time_seconds": time.time() - start_time,
                    "total_time_seconds": time.time() - start_time
                }
            }
        else:
            # Exécuter la recherche pour les requêtes techniques
            logger.info(f"Requête technique reçue: {request.query[:50]}")
            
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
        
        # Si l'utilisateur est authentifié et que nous avons une conversation, enregistrer le message
        if current_user and conversation_id:
            # Ajouter la question à la conversation
            user_message_id = db_manager.add_message(
                conversation_id=conversation_id,
                user_id=current_user["user_id"],
                content=request.query,
                is_user=True
            )
            
            # Ajouter les métadonnées d'intention si disponibles
            metadata_to_save = {
                "performance": result.get("performance", {}),
                "sources": result.get("sources", [])
            }
            
            if intent != "technical":
                metadata_to_save["intent"] = intent
                metadata_to_save["intent_metadata"] = metadata
            
            # Ajouter la réponse à la conversation
            ia_message_id = db_manager.add_message(
                conversation_id=conversation_id,
                user_id=current_user["user_id"],
                content=result["answer"],
                is_user=False,
                metadata=metadata_to_save
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
            {"performance": result.get("performance", {}), "intent": intent if intent != "technical" else None}
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
    start_time = time.time()
    
    # Variables pour enregistrement dans la conversation
    conversation_id = request.save_to_conversation
    user_message_id = None
    ia_message_id = None
    
    # Gérer la conversation si l'utilisateur est authentifié
    if current_user and request.create_conversation:
        try:
            # Créer ou vérifier une conversation
            conversation_id, is_new = ensure_conversation(
                user_id=current_user["user_id"],
                conversation_id=conversation_id,
                query=request.query
            )
            
            # Ajouter la question à la conversation
            user_message_id = db_manager.add_message(
                conversation_id=conversation_id,
                user_id=current_user["user_id"],
                content=request.query,
                is_user=True
            )
            logger.info(f"Message utilisateur ajouté à la conversation {conversation_id}: {user_message_id}")
        except Exception as e:
            logger.error(f"Erreur lors de la gestion de la conversation: {e}")
            conversation_id = None
            user_message_id = None
    
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
        # Analyser l'intention pour déterminer si c'est une requête conversationnelle
        yield f"event: progress\ndata: {json.dumps({'status': 'analyzing_intent', 'completion': 0.05})}\n\n"
        
        intent, metadata, direct_response = analyze_intent(request.query)
        
        # Si une réponse directe est disponible, l'envoyer progressivement
        if direct_response:
            yield f"event: progress\ndata: {json.dumps({'status': 'direct_response', 'completion': 0.5, 'intent': intent})}\n\n"
            
            # Diviser la réponse en chunks pour simuler un streaming
            chunks = []
            chunk_size = max(10, len(direct_response) // 20)  # Environ 20 chunks
            
            for i in range(0, len(direct_response), chunk_size):
                chunk = direct_response[i:i+chunk_size]
                chunks.append(chunk)
                
                # Envoyer le chunk au client
                completion = 0.5 + (0.4 * (i / len(direct_response)))
                yield f"event: chunk\ndata: {json.dumps({'text': chunk, 'completion': completion})}\n\n"
                
                # Petite pause pour simuler une génération naturelle
                await asyncio.sleep(0.05)
            
            # Enregistrer la réponse dans la conversation si nécessaire
            if current_user and conversation_id and user_message_id:
                try:
                    ia_message_id = db_manager.add_message(
                        conversation_id=conversation_id,
                        user_id=current_user["user_id"],
                        content=direct_response,
                        is_user=False,
                        metadata={
                            "intent": intent,
                            "intent_metadata": metadata,
                            "performance": {
                                "intent_analysis_time_seconds": time.time() - start_time,
                                "total_time_seconds": time.time() - start_time
                            }
                        }
                    )
                    # Mettre à jour la date de mise à jour de la conversation
                    db_manager.update_conversation(conversation_id)
                except Exception as e:
                    logger.error(f"Erreur lors de l'enregistrement de la réponse dans la conversation: {e}")
            
            # Préparer la réponse finale
            final_response = {
                "id": query_id,
                "query": request.query,
                "answer": direct_response,
                "sources": None,
                "performance": {
                    "intent_analysis_time_seconds": time.time() - start_time,
                    "total_time_seconds": time.time() - start_time
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
            
            # Sauvegarder dans l'historique
            save_query_history(
                request.query,
                direct_response,
                {"intent": intent, "performance": final_response["performance"]}
            )
            
            # Mettre à jour le statut de la requête
            ongoing_queries[query_id] = {"status": "complete", "completion": 1.0}
            return
        
        # Si c'est une requête technique, continuer avec le processus normal
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
    create_conversation: bool = Query(True, description="Créer automatiquement une conversation"),
    _token: Optional[str] = Query(None, description="Token JWT pour authentification via paramètre"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """Endpoint pour le streaming des réponses"""
    # Si on n'a pas d'utilisateur mais qu'un token a été fourni, essayer de l'authentifier
    if not current_user and _token:
        current_user = authenticate_via_token(_token)
        if current_user:
            logger.info(f"Utilisateur authentifié via _token: {current_user['email']}")

    request = QueryRequest(
        query=query,
        partie=partie,
        chapitre=chapitre,
        n_results=n_results,
        include_sources=include_sources,
        stream=True,
        save_to_conversation=save_to_conversation,
        create_conversation=create_conversation
    )
    
    retriever = get_retriever()
    
    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Access-Control-Allow-Origin": "*",
    }
    
    return StreamingResponse(
        stream_response(request, retriever, current_user),
        media_type="text/event-stream",
        headers=headers
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
        
        # Ajouter les statistiques de la base vectorielle
        try:
            retriever = get_retriever()
            vector_stats = retriever.vector_db.get_collection_stats()
            stats["vector_db"] = {
                name: {"count": data.get("count", 0)} for name, data in vector_stats.items()
                if "error" not in data
            }
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des statistiques vectorielles: {e}")
            stats["vector_db"] = {"error": str(e)}
            
        # Ajouter les informations sur l'environnement
        stats["environment"] = ENVIRONMENT
        stats["config_path"] = CONFIG_PATH
        stats["database_path"] = DB_PATH
        
        return stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des statistiques: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des statistiques")

@app.get("/admin/cleanup", response_model=Dict[str, Any])
async def cleanup_database(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Nettoie la base de données (supprime les tokens révoqués expirés)
    """
    try:
        # Vérifier si l'utilisateur est admin
        admin_emails = os.getenv("ADMIN_EMAILS", "").split(",")
        if current_user["email"] not in admin_emails:
            raise HTTPException(status_code=403, detail="Accès non autorisé")
        
        # Nettoyer la base de données
        cleanup_stats = db_manager.cleanup_database()
        
        return {
            "status": "success",
            "message": "Nettoyage de la base de données effectué",
            "details": cleanup_stats
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors du nettoyage de la base de données: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors du nettoyage de la base de données")

@app.get("/admin/models")
async def get_model_info(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Récupère des informations sur les modèles utilisés
    """
    try:
        # Vérifier si l'utilisateur est admin
        admin_emails = os.getenv("ADMIN_EMAILS", "").split(",")
        if current_user["email"] not in admin_emails:
            raise HTTPException(status_code=403, detail="Accès non autorisé")
        
        # Récupérer les informations sur les modèles
        retriever = get_retriever()
        llm_config = retriever.llm_config
        
        # Obtenir les informations sur les modèles configurés
        provider_list = llm_config.get_provider_list()
        embedding_provider_list = llm_config.get_embedding_provider_list()
        
        provider_name, model_name, params = llm_config.get_response_model()
        embedding_provider, embedding_model, embedding_params = llm_config.get_embedding_model()
        
        # Informations sur l'environnement
        environment_info = {
            "environment": ENVIRONMENT,
            "config_path": CONFIG_PATH
        }
        
        # Informations sur les modèles
        models_info = {
            "active_llm": {
                "provider": provider_name,
                "model": model_name
            },
            "active_embedding": {
                "provider": embedding_provider,
                "model": embedding_model,
                "dimensions": embedding_params.get("dimensions", "unknown")
            },
            "provider_priority": provider_list,
            "embedding_provider_priority": embedding_provider_list,
            "provider_configs": {}
        }
        
        # Ajouter des informations sur chaque fournisseur configuré
        for provider in provider_list:
            provider_config = llm_config.get_provider_config(provider)
            if provider_config:
                models_info["provider_configs"][provider] = {
                    "models": provider_config.get("models", {}),
                    "base_url": provider_config.get("base_url", "default"),
                    "local": provider_config.get("parameters", {}).get("local", False)
                }
        
        return {
            "environment": environment_info,
            "models": models_info
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des informations sur les modèles: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des informations sur les modèles")

#######################
# OUTILS DE TEST
#######################

@app.post("/test/intent")
async def test_intent(
    query: str = Body(..., embed=True),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """
    Endpoint pour tester l'analyse d'intention
    """
    try:
        intent, metadata, direct_response = analyze_intent(query)
        
        return {
            "query": query,
            "intent": intent,
            "confidence": metadata.get("confidence", 0),
            "subcategory": metadata.get("subcategory", ""),
            "needs_knowledge_base": metadata.get("needs_knowledge_base", True),
            "has_direct_response": direct_response is not None,
            "direct_response_preview": direct_response[:100] + "..." if direct_response else None,
            "explanation": metadata.get("explanation", "")
        }
    except Exception as e:
        logger.error(f"Erreur lors du test d'intention: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/test/search")
async def test_search(
    query: str = Body(...),
    n_results: int = Body(3, ge=1, le=10),
    partie: Optional[int] = Body(None),
    chapitre: Optional[int] = Body(None),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """
    Endpoint pour tester la recherche seule
    """
    try:
        retriever = get_retriever()
        start_time = time.time()
        
        # Exécuter la recherche
        search_results = retriever.search_only(
            query=query,
            partie=partie,
            chapitre=chapitre,
            n_results=n_results
        )
        
        # Formatage des résultats pour l'affichage
        results = []
        for i, result in enumerate(search_results):
            # Extraire les métadonnées essentielles
            metadata_display = {
                "title": result["metadata"].get("title", ""),
                "partie": result["metadata"].get("partie", ""),
                "chapitre": result["metadata"].get("chapitre", ""),
                "document_type": result["metadata"].get("document_type", "")
            }
            
            # Tronquer le texte pour l'affichage
            text_preview = result["text"]
            if len(text_preview) > 300:
                text_preview = text_preview[:300] + "..."
                
            results.append({
                "position": i + 1,
                "document_id": result["document_id"],
                "metadata": metadata_display,
                "relevance_score": result["relevance_score"],
                "text_preview": text_preview
            })
        
        return {
            "query": query,
            "results_count": len(search_results),
            "search_time_seconds": time.time() - start_time,
            "results": results
        }
    except Exception as e:
        logger.error(f"Erreur lors du test de recherche: {e}")
        raise HTTPException(status_code=500, detail=str(e))

#######################
# LANCEMENT DU SERVEUR
#######################

def start():
    """Démarre le serveur FastAPI avec Uvicorn"""
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "false").lower() == "true"
    
    # Log des informations de démarrage
    logger.info(f"Démarrage du serveur API OHADA sur {host}:{port}")
    logger.info(f"Environnement: {ENVIRONMENT}")
    logger.info(f"Rechargement automatique: {reload}")
    
    # Démarrer le serveur
    uvicorn.run(
        "src.api.ohada_api_server:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )

if __name__ == "__main__":
    # Lancer le serveur avec uvicorn
    start()