"""
Extension de l'API FastAPI pour gérer les utilisateurs et conversations.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging
import uuid
from datetime import datetime

# Import des modules nécessaires
from src.auth.auth_manager import create_auth_dependency
from src.db.db_manager import DatabaseManager

# Configuration du logging
logger = logging.getLogger("ohada_api_conversations")

# Initialiser le gestionnaire de base de données
db_manager = DatabaseManager()

# Créer le dépendance d'authentification
get_current_user = create_auth_dependency(db_manager)

# Créer le routeur
router = APIRouter(prefix="/conversations", tags=["conversations"])

# Modèles Pydantic pour la validation des données

class ConversationCreate(BaseModel):
    title: str = Field(..., description="Titre de la conversation")

class ConversationUpdate(BaseModel):
    title: str = Field(..., description="Nouveau titre de la conversation")

class MessageCreate(BaseModel):
    content: str = Field(..., description="Contenu du message")
    conversation_id: Optional[str] = Field(None, description="ID de conversation existante (optionnel)")
    conversation_title: Optional[str] = Field(None, description="Titre pour une nouvelle conversation (optionnel)")

class FeedbackCreate(BaseModel):
    rating: int = Field(..., ge=0, le=5, description="Note (0-5)")
    comment: Optional[str] = Field(None, description="Commentaire (optionnel)")

# Routes

@router.get("/", response_model=List[Dict[str, Any]])
async def get_conversations(
    limit: int = Query(50, ge=1, le=100, description="Nombre maximum de conversations"),
    offset: int = Query(0, ge=0, description="Décalage pour la pagination"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Récupère les conversations de l'utilisateur
    """
    try:
        conversations = db_manager.get_user_conversations(
            user_id=current_user["user_id"],
            limit=limit,
            offset=offset
        )
        return conversations
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des conversations: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des conversations")

@router.post("/", response_model=Dict[str, Any])
async def create_conversation(
    data: ConversationCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Crée une nouvelle conversation
    """
    try:
        conversation_id = db_manager.create_conversation(
            user_id=current_user["user_id"],
            title=data.title
        )
        
        if not conversation_id:
            raise HTTPException(status_code=500, detail="Erreur lors de la création de la conversation")
            
        return {
            "conversation_id": conversation_id,
            "title": data.title,
            "user_id": current_user["user_id"],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Erreur lors de la création de la conversation: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la création de la conversation")

@router.get("/{conversation_id}", response_model=Dict[str, Any])
async def get_conversation(
    conversation_id: str = Path(..., description="ID de la conversation"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Récupère les détails d'une conversation
    """
    try:
        conversation = db_manager.get_conversation(conversation_id)
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation non trouvée")
            
        # Vérifier que l'utilisateur est bien le propriétaire
        if conversation["user_id"] != current_user["user_id"]:
            raise HTTPException(status_code=403, detail="Accès non autorisé à cette conversation")
            
        # Récupérer les messages de la conversation
        messages = db_manager.get_conversation_messages(conversation_id)
        
        # Ajouter les messages à la réponse
        conversation["messages"] = messages
        
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de la conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération de la conversation")

@router.put("/{conversation_id}", response_model=Dict[str, Any])
async def update_conversation(
    data: ConversationUpdate,
    conversation_id: str = Path(..., description="ID de la conversation"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Met à jour le titre d'une conversation
    """
    try:
        # Vérifier que la conversation existe et appartient à l'utilisateur
        conversation = db_manager.get_conversation(conversation_id)
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation non trouvée")
            
        if conversation["user_id"] != current_user["user_id"]:
            raise HTTPException(status_code=403, detail="Accès non autorisé à cette conversation")
        
        # Mettre à jour le titre
        success = db_manager.update_conversation(conversation_id, data.title)
        
        if not success:
            raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour de la conversation")
        
        # Récupérer la conversation mise à jour
        updated_conversation = db_manager.get_conversation(conversation_id)
        return updated_conversation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour de la conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour de la conversation")

@router.delete("/{conversation_id}", response_model=Dict[str, str])
async def delete_conversation(
    conversation_id: str = Path(..., description="ID de la conversation"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Supprime une conversation
    """
    try:
        # Vérifier que la conversation existe et appartient à l'utilisateur
        conversation = db_manager.get_conversation(conversation_id)
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation non trouvée")
            
        if conversation["user_id"] != current_user["user_id"]:
            raise HTTPException(status_code=403, detail="Accès non autorisé à cette conversation")
        
        # Supprimer la conversation
        success = db_manager.delete_conversation(conversation_id, current_user["user_id"])
        
        if not success:
            raise HTTPException(status_code=500, detail="Erreur lors de la suppression de la conversation")
        
        return {"status": "success", "message": "Conversation supprimée avec succès"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la suppression de la conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la suppression de la conversation")

@router.post("/{conversation_id}/messages", response_model=Dict[str, Any])
async def add_message_to_conversation(
    data: MessageCreate,
    conversation_id: str = Path(..., description="ID de la conversation"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Ajoute un message à une conversation existante
    """
    try:
        # Vérifier que la conversation existe et appartient à l'utilisateur
        conversation = db_manager.get_conversation(conversation_id)
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation non trouvée")
            
        if conversation["user_id"] != current_user["user_id"]:
            raise HTTPException(status_code=403, detail="Accès non autorisé à cette conversation")
        
        # Ajouter le message à la conversation
        message_id = db_manager.add_message(
            conversation_id=conversation_id,
            user_id=current_user["user_id"],
            content=data.content,
            is_user=True
        )
        
        if not message_id:
            raise HTTPException(status_code=500, detail="Erreur lors de l'ajout du message")
        
        # Mettre à jour la date de mise à jour de la conversation
        db_manager.update_conversation(conversation_id)
        
        # Intégration avec le service OHADA pour générer une réponse
        from src.retrieval.ohada_hybrid_retriever import create_ohada_query_api
        
        # Créer l'API
        retriever = create_ohada_query_api()
        
        # Exécuter la recherche
        result = retriever.search_ohada_knowledge(
            query=data.content,
            n_results=5,
            include_sources=True
        )
        
        # Sauvegarder la réponse de l'IA
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
        
        # Récupérer les messages mis à jour
        messages = db_manager.get_conversation_messages(conversation_id)
        
        return {
            "conversation_id": conversation_id,
            "messages": messages,
            "user_message_id": message_id,
            "ia_message_id": ia_message_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de l'ajout du message à la conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'ajout du message")

@router.post("/messages", response_model=Dict[str, Any])
async def create_message(
    data: MessageCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Crée un nouveau message, soit dans une conversation existante, soit dans une nouvelle
    """
    try:
        conversation_id = data.conversation_id
        
        # Si aucun ID de conversation n'est fourni, en créer une nouvelle
        if not conversation_id:
            # Vérifier qu'un titre est fourni
            if not data.conversation_title:
                raise HTTPException(status_code=400, detail="Un titre de conversation est requis")
                
            # Créer une nouvelle conversation
            conversation_id = db_manager.create_conversation(
                user_id=current_user["user_id"],
                title=data.conversation_title
            )
            
            if not conversation_id:
                raise HTTPException(status_code=500, detail="Erreur lors de la création de la conversation")
        else:
            # Vérifier que la conversation existe et appartient à l'utilisateur
            conversation = db_manager.get_conversation(conversation_id)
            
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation non trouvée")
                
            if conversation["user_id"] != current_user["user_id"]:
                raise HTTPException(status_code=403, detail="Accès non autorisé à cette conversation")
        
        # Ajouter le message à la conversation
        message_id = db_manager.add_message(
            conversation_id=conversation_id,
            user_id=current_user["user_id"],
            content=data.content,
            is_user=True
        )
        
        if not message_id:
            raise HTTPException(status_code=500, detail="Erreur lors de l'ajout du message")
        
        # Intégration avec le service OHADA pour générer une réponse
        from src.retrieval.ohada_hybrid_retriever import create_ohada_query_api
        
        # Créer l'API
        retriever = create_ohada_query_api()
        
        # Exécuter la recherche
        result = retriever.search_ohada_knowledge(
            query=data.content,
            n_results=5,
            include_sources=True
        )
        
        # Sauvegarder la réponse de l'IA
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
        
        # Récupérer les messages mis à jour
        messages = db_manager.get_conversation_messages(conversation_id)
        
        return {
            "conversation_id": conversation_id,
            "messages": messages,
            "user_message_id": message_id,
            "ia_message_id": ia_message_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la création du message: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la création du message")

@router.post("/messages/{message_id}/feedback", response_model=Dict[str, Any])
async def add_feedback(
    data: FeedbackCreate,
    message_id: str = Path(..., description="ID du message"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Ajoute un feedback à un message
    """
    try:
        # Ajouter le feedback
        feedback_id = db_manager.add_feedback(
            message_id=message_id,
            user_id=current_user["user_id"],
            rating=data.rating,
            comment=data.comment
        )
        
        if not feedback_id:
            raise HTTPException(status_code=500, detail="Erreur lors de l'ajout du feedback")
        
        # Récupérer le feedback
        feedback = db_manager.get_message_feedback(message_id)
        
        return {
            "feedback_id": feedback_id,
            "message_id": message_id,
            "rating": data.rating,
            "comment": data.comment,
            "created_at": feedback.get("created_at") if feedback else datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Erreur lors de l'ajout du feedback au message {message_id}: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'ajout du feedback")