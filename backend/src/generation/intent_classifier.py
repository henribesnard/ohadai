"""
Module d'analyse d'intention basé sur LLM pour le système OHADA Expert-Comptable.
"""
import logging
from typing import Dict, Any, Tuple, Optional
import json

# Configuration du logging
logger = logging.getLogger("ohada_intent_analyzer")

class LLMIntentAnalyzer:
    """Analyseur d'intention utilisant un LLM pour les requêtes utilisateur"""
    
    def __init__(self, llm_client, assistant_config: Dict[str, Any] = None):
        """
        Initialise l'analyseur d'intention basé sur LLM
        
        Args:
            llm_client: Client LLM pour la génération de texte
            assistant_config: Configuration de l'assistant (nom, expertise, etc.)
        """
        self.llm_client = llm_client
        self.assistant_config = assistant_config or {
            "name": "Expert OHADA",
            "expertise": "comptabilité et normes SYSCOHADA",
            "region": "zone OHADA (Afrique)"
        }
    
    def analyze_intent(self, query: str) -> Tuple[str, Dict[str, Any]]:
        """
        Analyse l'intention de la requête utilisateur en utilisant un LLM
        
        Args:
            query: Requête de l'utilisateur
            
        Returns:
            Tuple (intention, métadonnées)
        """
        # Prompt pour classifier l'intention
        system_prompt = """
        Tu es un assistant spécialisé dans l'analyse d'intention des questions utilisateur.
        
        Ta tâche est de classifier les questions en différentes catégories :
        - "greeting": Salutations comme "bonjour", "salut", etc.
        - "identity": Questions sur l'identité ou les capacités de l'assistant.
        - "smalltalk": Conversations générales comme remerciements, questions de courtoisie, au revoir.
        - "technical": Questions techniques qui nécessitent des connaissances spécifiques.
        
        Si c'est du "smalltalk", précise la sous-catégorie ("merci", "comment_ca_va", "au_revoir", etc.)
        
        Réponds uniquement avec un objet JSON au format suivant:
        {
            "intent": "greeting|identity|smalltalk|technical",
            "confidence": 0.XX, // entre 0 et 1
            "subcategory": "string", // uniquement pour smalltalk
            "explanation": "string", // courte explication
            "needs_knowledge_base": true|false // si une recherche est nécessaire
        }
        """
        
        user_prompt = f"Question utilisateur: \"{query}\""
        
        try:
            # Générer la classification
            response = self.llm_client.generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=300,
                temperature=0.1 # Basse température pour des réponses cohérentes
            )
            
            # Extraire le JSON de la réponse
            # Parfois le LLM peut ajouter du texte supplémentaire, donc on essaie d'isoler le JSON
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > 0:
                json_response = response[json_start:json_end]
                result = json.loads(json_response)
                
                # Vérifier que les champs nécessaires sont présents
                if "intent" not in result:
                    logger.warning(f"Champ 'intent' manquant dans la réponse LLM: {result}")
                    result["intent"] = "technical"  # Fallback
                
                return result["intent"], result
            else:
                logger.error(f"Format JSON invalide dans la réponse LLM: {response}")
                return "technical", {"confidence": 0, "needs_knowledge_base": True}
                
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse d'intention: {e}")
            # En cas d'erreur, considérer comme une requête technique
            return "technical", {"confidence": 0, "needs_knowledge_base": True}
    
    def generate_response(self, intent: str, metadata: Dict[str, Any]) -> Optional[str]:
        """
        Génère une réponse en fonction de l'intention détectée
        
        Args:
            intent: Intention détectée
            metadata: Métadonnées de l'intention
            
        Returns:
            Réponse générée ou None si recherche nécessaire
        """
        # Si une recherche dans la base de connaissances est nécessaire
        if metadata.get("needs_knowledge_base", True):
            return None
            
        # Prompt pour générer une réponse appropriée selon l'intention
        system_prompt = f"""
        Tu es {self.assistant_config.get('name', 'Expert OHADA')}, un assistant spécialisé en {self.assistant_config.get('expertise', 'comptabilité et normes SYSCOHADA')} dans la {self.assistant_config.get('region', 'zone OHADA (Afrique)')}.
        
        Tu dois répondre de manière naturelle à l'utilisateur en fonction de l'intention de sa question.
        
        Points importants sur ton identité:
        - Tu es spécialiste des normes comptables OHADA et SYSCOHADA
        - Tu connais parfaitement le plan comptable OHADA
        - Tu es conçu pour aider avec des questions de comptabilité dans la zone OHADA
        - Tu peux expliquer les procédures comptables, les normes, et comment appliquer le plan comptable
        
        Réponds de façon concise, professionnelle mais chaleureuse.
        """
        
        # Construire le prompt utilisateur selon l'intention
        if intent == "greeting":
            prompt = f"L'utilisateur te dit: \"{metadata.get('query', 'Bonjour')}\". Réponds avec une salutation professionnelle qui mentionne ton rôle d'expert OHADA et propose ton aide."
        
        elif intent == "identity":
            prompt = f"L'utilisateur te demande qui tu es ou ce que tu peux faire: \"{metadata.get('query', 'Qui es-tu?')}\". Présente-toi en détaillant tes capacités en tant qu'expert comptable OHADA."
        
        elif intent == "smalltalk":
            subcategory = metadata.get("subcategory", "")
            prompt = f"L'utilisateur fait du smalltalk, catégorie '{subcategory}': \"{metadata.get('query', '')}\". Réponds de façon appropriée tout en rappelant subtilement ton domaine d'expertise OHADA."
        
        else:
            # Si l'intention n'est pas reconnue, retourner None pour utiliser la recherche
            return None
        
        try:
            # Générer la réponse
            response = self.llm_client.generate_response(
                system_prompt=system_prompt,
                user_prompt=prompt,
                max_tokens=600,
                temperature=0.7  # Plus de créativité pour les réponses personnalisées
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération de réponse personnalisée: {e}")
            return None