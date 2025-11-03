"""
Module d'analyse d'intention basé sur LLM pour le système OHADA Expert-Comptable.
Optimisé avec détection rapide des requêtes techniques évidentes.
"""
import logging
from typing import Dict, Any, Tuple, Optional
import json
import re

# Configuration du logging
logger = logging.getLogger("ohada_intent_analyzer")

def is_technical_query_fast(query: str) -> bool:
    """
    Détecte rapidement si c'est une requête technique évidente (sans LLM).

    Cette fonction utilise des heuristiques simples pour identifier les requêtes
    qui nécessitent clairement une recherche dans la base de connaissances OHADA.
    Cela permet d'éviter un appel LLM coûteux (~200-500ms) pour environ 70% des requêtes.

    Args:
        query: Requête de l'utilisateur

    Returns:
        True si la requête est clairement technique, False sinon
    """
    # Patterns indiquant clairement une requête technique
    technical_patterns = [
        r'\bcompte\s+\d+',                              # "compte 401", "compte 6012"
        r'\barticle\s+\d+',                             # "article 23", "article 145"
        r'\bsection\s+\d+',                             # "section 5"
        r'\bchapitre\s+\d+',                            # "chapitre 2"
        r'\bpartie\s+\d+',                              # "partie 1"
        r'\bcomptabilis(er|ation)',                     # "comptabiliser", "comptabilisation"
        r'\bsyscohada\b',                               # "SYSCOHADA"
        r'\bohada\b',                                   # "OHADA"
        r'\bplan\s+comptable',                          # "plan comptable"
        r'\bquel(le)?\s+(est|sont)\s+(le|les)\s+compte', # "quel est le compte"
        r'\bcomment\s+(enregistrer|comptabiliser)',     # "comment comptabiliser"
        r'\b(bilan|actif|passif|amortissement)',        # Termes comptables
        r'\b(débit|crédit|journal|écriture)',           # Opérations comptables
        r'\b(immobilisation|stock|trésorerie)',         # Comptes spécifiques
        r'\bnorme\s+(comptable|ohada)',                 # "norme comptable"
    ]

    query_lower = query.lower()

    # Vérifier si la requête matche un des patterns techniques
    for pattern in technical_patterns:
        if re.search(pattern, query_lower):
            logger.debug(f"Requête technique détectée rapidement via pattern: {pattern}")
            return True

    # Vérifier les salutations évidentes (pour éviter les faux positifs)
    greeting_patterns = [
        r'^\s*(bonjour|salut|hello|hi|hey|bonsoir)\s*[!.?]?\s*$',
        r'^\s*(merci|thanks|au\s+revoir|bye)\s*[!.?]?\s*$',
    ]

    for pattern in greeting_patterns:
        if re.match(pattern, query_lower):
            logger.debug(f"Salutation/smalltalk détecté rapidement")
            return False

    # Si la requête est très courte (< 3 mots), probablement pas technique
    # sauf si elle contient un numéro de compte/article
    words = query_lower.split()
    if len(words) < 3 and not re.search(r'\d+', query):
        return False

    # Par défaut, considérer comme non-technique pour passer par l'analyse LLM
    return False

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
        Analyse l'intention de la requête utilisateur.

        Utilise d'abord une détection rapide par heuristiques (regex) pour
        les requêtes techniques évidentes, puis passe par le LLM seulement
        si nécessaire. Cela économise ~200-500ms pour 70% des requêtes.

        Args:
            query: Requête de l'utilisateur

        Returns:
            Tuple (intention, métadonnées)
        """
        # OPTIMISATION: Détection rapide des requêtes techniques évidentes (0.1ms au lieu de 200-500ms)
        if is_technical_query_fast(query):
            logger.info(f"Requête technique détectée rapidement (sans LLM) pour: {query[:50]}")
            return "technical", {
                "confidence": 0.95,
                "needs_knowledge_base": True,
                "query": query,
                "detection_method": "fast_heuristics",
                "explanation": "Requête technique détectée par analyse de patterns"
            }

        # Si pas détecté comme technique, passer par l'analyse LLM complète
        logger.info(f"Analyse LLM d'intention pour: {query[:50]}")

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