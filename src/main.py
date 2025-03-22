"""
Main entry point for the OHADA Expert Accounting system.
Version optimisée avec configuration flexible des modèles de langage et gestion de l'environnement.
"""

import os
import sys
import time
import threading
import signal
import logging
import yaml
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any, Optional, List

# Load environment variables
load_dotenv()

# Déterminer l'environnement et le chemin de configuration
ENVIRONMENT = os.getenv("OHADA_ENV", "test")
CONFIG_PATH = os.getenv("OHADA_CONFIG_PATH", "./src/config")
CONFIG_FILE = os.path.join(CONFIG_PATH, f"llm_config_{ENVIRONMENT}.yaml")

# Configuration du logging
logging.basicConfig(
    level=logging.INFO if ENVIRONMENT == "production" else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"ohada_main_{ENVIRONMENT}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ohada_main")

# Constantes
DEFAULT_TIMEOUT = 180  # Secondes

def load_llm_config():
    """Charge la configuration des modèles de langage depuis le fichier YAML"""
    try:
        logger.info(f"Chargement de la configuration depuis {CONFIG_FILE}")
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logger.error(f"Erreur lors du chargement de la configuration: {e}")
        # Essayer avec le chemin par défaut si le fichier n'est pas trouvé
        default_config = f"./src/config/llm_config.yaml"
        if os.path.exists(default_config):
            logger.info(f"Tentative avec le fichier par défaut: {default_config}")
            try:
                with open(default_config, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                return config
            except Exception as e2:
                logger.error(f"Erreur lors du chargement de la configuration par défaut: {e2}")
        return None

def print_welcome():
    """Affiche le message de bienvenue et les instructions"""
    # Logo différent selon l'environnement
    if ENVIRONMENT == "production":
        env_indicator = "💼 [PRODUCTION]"
    else:
        env_indicator = "🧪 [TEST]"
        
    print("\n" + "=" * 80)
    print(f"                  OHADA EXPERT-COMPTABLE AI {env_indicator}".center(80))
    print("=" * 80)
    print("\nBienvenue dans votre assistant d'expertise comptable OHADA!")
    print("Posez des questions sur le plan comptable, les normes et règlements OHADA.")
    print("\nExemples de questions:")
    print("  - Comment fonctionne l'amortissement dégressif dans le SYSCOHADA?")
    print("  - Expliquez la structure du plan comptable OHADA.")
    print("  - Quelles sont les règles pour la comptabilisation des subventions?")
    print("\nTapez 'exit', 'quit', ou 'q' pour quitter.")
    print("-" * 80)

def process_query_with_extended_timeout(query: str, api=None, max_wait_time: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    """
    Traite une requête avec gestion de timeout étendu
    
    Args:
        query: Question de l'utilisateur
        api: Instance de OhadaQueryAPI (peut être None pour création à la demande)
        max_wait_time: Temps d'attente maximum en secondes
        
    Returns:
        Dictionnaire contenant la réponse et les informations de timing
    """
    # Import nécessaire seulement quand nécessaire (pour un démarrage plus rapide)
    try:
        # Import du module de requête
        from src.retrieval.ohada_hybrid_retriever import create_ohada_query_api
    except ImportError as e:
        logger.error(f"Erreur lors de l'importation des modules: {e}")
        return {
            "response": f"Erreur lors de l'importation des modules: {str(e)}",
            "elapsed_time": 0,
            "success": False
        }
    
    # Variable de résultat partagée pour la communication entre threads
    result = {
        "response": None,
        "done": False,
        "success": False,
        "search_time": 0,
        "generation_time": 0,
        "elapsed_time": 0,
        "error": None
    }
    
    # Indicateur pour l'annulation par l'utilisateur
    user_cancelled = {"value": False}
    
    # Fonction qui s'exécutera dans un thread séparé
    def process_thread():
        try:
            start_time = time.time()
            
            # Créer ou utiliser l'instance d'API fournie
            nonlocal api
            if api is None:
                logger.info("Création d'une nouvelle instance d'API")
                api = create_ohada_query_api(config_path=CONFIG_PATH)
            
            # Analyser l'intention pour déterminer si c'est une requête conversationnelle
            from src.generation.intent_classifier import LLMIntentAnalyzer
            
            # Initialiser l'analyseur d'intention
            intent_analyzer = LLMIntentAnalyzer(
                llm_client=api.llm_client,
                assistant_config=api.llm_config.get_assistant_personality()
            )
            
            # Analyser l'intention de la requête
            intent, metadata, direct_response = analyze_intent(query, intent_analyzer)
            
            # Si une réponse directe est disponible, l'utiliser
            if direct_response:
                logger.info(f"Réponse directe générée pour l'intention: {intent}")
                result["response"] = direct_response
                result["intent"] = intent
                result["intent_analysis"] = True
                result["elapsed_time"] = time.time() - start_time
                result["success"] = True
                result["done"] = True
                return
            
            # Sinon, exécuter la recherche de connaissances normalement
            query_result = api.search_ohada_knowledge(
                query=query,
                n_results=3,
                include_sources=True
            )
            
            # Extraire la réponse et les métriques de performance
            result["response"] = query_result.get("answer", "")
            result["search_time"] = query_result.get("performance", {}).get("search_time_seconds", 0)
            result["generation_time"] = query_result.get("performance", {}).get("generation_time_seconds", 0)
            result["elapsed_time"] = time.time() - start_time
            result["success"] = True
            result["done"] = True
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            result["response"] = f"Désolé, une erreur s'est produite lors du traitement de votre question: {str(e)}"
            result["error"] = error_details
            result["elapsed_time"] = time.time() - start_time
            result["done"] = True
            logger.error(f"Erreur dans le thread de traitement: {error_details}")
    
    # Créer et démarrer le thread
    thread = threading.Thread(target=process_thread)
    thread.daemon = True  # Le thread sera tué si le programme principal se termine
    thread.start()
    
    # Fonction pour gérer l'entrée utilisateur dans un thread séparé
    def input_thread():
        while not result["done"] and not user_cancelled["value"]:
            try:
                user_input = input("Appuyez sur 'C' pour annuler ou attendez la réponse complète: ")
                if user_input.lower() == 'c':
                    user_cancelled["value"] = True
                    print("Vous avez choisi d'annuler. Veuillez patienter pendant que nous finalisons...")
                    break
            except:
                # Ignorer les erreurs d'entrée
                time.sleep(1)
                continue
    
    # Attendre que le thread se termine avec des vérifications périodiques
    wait_interval = 5   # Vérifier toutes les 5 secondes
    elapsed = 0
    reminder_intervals = [30, 60, 90, 120]  # Secondes où rappeler à l'utilisateur qu'il peut annuler
    
    # Démarrer le thread d'entrée après le premier intervalle d'attente
    time.sleep(wait_interval)
    elapsed += wait_interval
    
    if not result["done"]:
        print(f"⏳ Traitement en cours ({elapsed}s)... Veuillez patienter.")
        input_thread = threading.Thread(target=input_thread)
        input_thread.daemon = True
        input_thread.start()
    
    # Continuer à attendre avec des mises à jour périodiques
    while not result["done"] and elapsed < max_wait_time and not user_cancelled["value"]:
        thread.join(wait_interval)
        elapsed += wait_interval
        if not result["done"]:
            print(f"⏳ Traitement en cours ({elapsed}s)... Veuillez patienter.")
            
            # À certains intervalles, rappeler à l'utilisateur qu'il peut annuler
            if elapsed in reminder_intervals:
                print("La génération prend plus de temps que prévu. Pour une réponse de qualité, veuillez patienter.")
                print("Vous pouvez appuyer sur 'C' pour annuler et obtenir une réponse partielle.")
    
    # Si l'utilisateur a annulé
    if user_cancelled["value"]:
        # Attendre un peu pour voir si le thread se termine quand même
        thread.join(5)
        
        if result["done"]:
            # Le thread s'est terminé malgré l'annulation
            print("La réponse complète vient d'être générée malgré l'annulation!")
        else:
            print("Génération d'une réponse partielle...")
            fallback_response = generate_fallback_response(query)
            
            return {
                "response": fallback_response,
                "elapsed_time": elapsed,
                "success": False,
                "cancelled": True
            }
    
    # Si le thread est toujours en cours d'exécution après max_wait_time
    if not result["done"]:
        print(f"\n⚠️ La génération a atteint le temps maximum autorisé de {max_wait_time//60} minutes.")
        print("Nous allons quand même continuer à attendre la réponse complète...")
        
        # Continuer à attendre indéfiniment avec des mises à jour toutes les 30 secondes
        extra_wait = 0
        extra_wait_limit = 300  # Maximum 5 minutes supplémentaires
        while not result["done"] and extra_wait < extra_wait_limit:
            thread.join(30)
            extra_wait += 30
            if not result["done"]:
                print(f"⏳ Toujours en attente... ({elapsed + extra_wait}s). Appuyez sur 'C' pour abandonner.")
        
        if not result["done"]:
            print(f"\n⚠️ Abandon après {(elapsed + extra_wait)//60} minutes d'attente.")
            fallback_response = generate_fallback_response(query)
            
            return {
                "response": fallback_response,
                "elapsed_time": elapsed + extra_wait,
                "success": False,
                "timeout": True
            }
    
    return result

def analyze_intent(query: str, intent_analyzer):
    """
    Analyse l'intention d'une requête et génère une réponse directe si nécessaire
    
    Args:
        query: Requête de l'utilisateur
        intent_analyzer: Analyseur d'intention
    
    Returns:
        Tuple (intention, métadonnées, réponse directe ou None)
    """
    # Analyser l'intention de la requête
    intent, metadata = intent_analyzer.analyze_intent(query)
    
    # Enrichir les métadonnées avec la requête originale pour référence future
    metadata["query"] = query
    
    # Générer une réponse directe si nécessaire
    direct_response = intent_analyzer.generate_response(intent, metadata)
    
    return intent, metadata, direct_response

def generate_fallback_response(query: str) -> str:
    """
    Génère une réponse de secours lorsque le processus principal est annulé ou expire.
    Utilise la même configuration que le système principal.
    
    Args:
        query: Question de l'utilisateur
        
    Returns:
        Une réponse simplifiée
    """
    try:
        # Import des modules nécessaires
        from src.config.ohada_config import LLMConfig
        from src.utils.ohada_clients import LLMClient
        
        # Charger la configuration des modèles
        llm_config = LLMConfig(CONFIG_PATH)
        
        # Initialiser le client LLM
        llm_client = LLMClient(llm_config)
        
        # Générer une réponse simplifiée
        prompt = f"Répondez brièvement à cette question sur le plan comptable OHADA (maximum 5 paragraphes): {query}"
        
        fallback_response = llm_client.generate_response(
            system_prompt="Vous êtes un expert-comptable spécialisé dans le plan comptable OHADA. Répondez de manière concise et précise.",
            user_prompt=prompt,
            max_tokens=500,
            temperature=0.3
        )
        
        if fallback_response:
            return f"⚠️ Réponse partielle :\n\n{fallback_response}"
        else:
            return "⚠️ Le temps de réponse a dépassé la limite. Veuillez poser une question plus spécifique pour obtenir une réponse plus rapide."
            
    except Exception as e:
        logger.error(f"Erreur lors de la génération de la réponse de secours: {e}")
        return f"⚠️ Le temps de réponse a dépassé la limite. Veuillez poser une question plus spécifique pour obtenir une réponse plus rapide.\n\nErreur: {str(e)}"

def check_provider_keys(config: Dict) -> Dict[str, bool]:
    """
    Vérifie quelles clés API sont disponibles pour chaque fournisseur
    
    Args:
        config: Configuration des modèles de langage
        
    Returns:
        Dictionnaire des fournisseurs avec leur statut de disponibilité
    """
    providers_status = {}
    
    if not config or "providers" not in config:
        return providers_status
    
    for provider_name, provider_config in config["providers"].items():
        # Ignorer les fournisseurs désactivés
        if provider_config.get("enabled") is False:
            providers_status[provider_name] = False
            continue
        
        # Vérifier si une clé API est nécessaire (certains modèles locaux pourraient ne pas en avoir besoin)
        api_key_env = provider_config.get("api_key_env")
        if not api_key_env:
            # Pour les fournisseurs sans clé API (comme les modèles locaux)
            providers_status[provider_name] = True
            continue
        
        # Vérifier si la clé API est définie
        api_key = os.getenv(api_key_env)
        providers_status[provider_name] = bool(api_key)
    
    return providers_status

def check_environment() -> bool:
    """
    Vérifie si les variables d'environnement nécessaires sont définies
    
    Returns:
        True si au moins une clé API requise est disponible
    """
    # Charger la configuration
    config = load_llm_config()
    if not config:
        logger.error("Impossible de charger la configuration des modèles")
        return False
    
    # Vérifier les clés API
    providers_status = check_provider_keys(config)
    
    if not providers_status:
        logger.error("Aucun fournisseur configuré!")
        return False
    
    # Vérifier les fournisseurs prioritaires pour les réponses
    response_providers = []
    if "provider_priority" in config:
        response_providers = config["provider_priority"]
    elif "default_provider" in config:
        response_providers = [config["default_provider"]]
    
    # Vérifier les fournisseurs prioritaires pour les embeddings
    embedding_providers = []
    if "embedding_provider_priority" in config:
        embedding_providers = config["embedding_provider_priority"]
    elif "default_embedding_provider" in config:
        embedding_providers = [config["default_embedding_provider"]]
    
    # Vérifier si au moins un fournisseur est disponible pour chaque fonction
    response_available = any(providers_status.get(p, False) for p in response_providers)
    embedding_available = any(providers_status.get(p, False) for p in embedding_providers)
    
    # Afficher les informations sur les fournisseurs disponibles
    print(f"\n=== Configuration des modèles ({ENVIRONMENT}) ===")
    print("Fournisseurs pour les réponses:")
    for p in response_providers:
        status = "✅ Disponible" if providers_status.get(p, False) else "❌ Non disponible"
        print(f"  - {p}: {status}")
    
    print("\nFournisseurs pour les embeddings:")
    for p in embedding_providers:
        status = "✅ Disponible" if providers_status.get(p, False) else "❌ Non disponible"
        print(f"  - {p}: {status}")
    
    print("\n" + "-" * 80)
    
    if not response_available:
        logger.error("❌ Aucun fournisseur disponible pour les réponses!")
    
    if not embedding_available:
        logger.error("❌ Aucun fournisseur disponible pour les embeddings!")
    
    return response_available and embedding_available

def main():
    """Fonction principale pour exécuter le système OHADA Expert Accounting"""
    print(f"\nInitialisation de l'Assistant Expert-Comptable OHADA ({ENVIRONMENT})...")
    
    # Vérifier les variables d'environnement et la configuration
    if not check_environment():
        print("❌ Erreur: Configuration invalide ou clés API manquantes.")
        print("Veuillez vérifier votre fichier de configuration et vos variables d'environnement.")
        print("Au moins un fournisseur de modèle doit être correctement configuré pour chaque fonction.")
        return
    
    print_welcome()
    
    # Précharger le modèle d'embedding au démarrage
    try:
        print("Préchargement du modèle d'embedding (cela peut prendre un moment)...")
        from src.vector_db.ohada_vector_db_structure import OhadaEmbedder
        # Charger le modèle en utilisant le constructeur (qui va maintenant utiliser un singleton)
        
        # Déterminer le modèle à utiliser selon l'environnement
        if ENVIRONMENT == "production":
            embedding_model = "Alibaba-NLP/gte-Qwen2-1.5B-instruct"
        else:
            embedding_model = "all-MiniLM-L6-v2"
            
        embedder = OhadaEmbedder(model_name=embedding_model)
        # Générer un petit embedding pour s'assurer que tout fonctionne
        _ = embedder.generate_embedding("Test de préchargement")
        print(f"Modèle d'embedding {embedding_model} préchargé avec succès.")
    except Exception as e:
        logger.error(f"Erreur lors du préchargement du modèle d'embedding: {e}")
        print(f"⚠️ Avertissement: Le préchargement du modèle d'embedding a échoué: {str(e)}")
        print("Le modèle sera chargé lors de la première requête.\n")
    
    # Créer l'instance d'API une seule fois (sera réutilisée)
    try:
        from src.retrieval.ohada_hybrid_retriever import create_ohada_query_api
        print("Initialisation de l'API de requête...")
        api = create_ohada_query_api(config_path=CONFIG_PATH)
        logger.info("API initialisée avec succès")
        print("API initialisée avec succès.\n")
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de l'API: {e}")
        print(f"⚠️ Avertissement: {str(e)}")
        print("L'API sera initialisée à la demande pour chaque requête.\n")
        api = None  # Sera créée à la demande dans chaque requête
    
    # Boucle d'interaction principale
    while True:
        # Obtenir la requête de l'utilisateur
        user_query = input("\n💬 Votre question (ou 'exit' pour quitter): ")
        
        # Vérifier si l'utilisateur veut quitter
        if user_query.lower() in ["exit", "quit", "q", "quitter"]:
            print("\nMerci d'avoir utilisé l'Assistant Expert-Comptable OHADA. À bientôt!")
            break
        
        if not user_query.strip():
            print("Veuillez entrer une question valide.")
            continue
        
        # Traiter la requête avec timeout étendu
        try:
            print("\n⏳ Recherche d'informations en cours...")
            start_time = time.time()
            
            # Traiter la requête avec gestion de timeout étendu
            result = process_query_with_extended_timeout(user_query, api=api)
            
            # Obtenir la réponse
            response = result.get("response", "")
            
            # Calculer le temps écoulé
            elapsed_time = result.get("elapsed_time", time.time() - start_time)
            
            # Afficher la réponse
            print("\n" + "-" * 80)
            
            # Si c'est une réponse basée sur l'intention, afficher l'intention détectée
            if result.get("intent_analysis", False):
                print(f"✅ Réponse (générée en {elapsed_time:.2f} secondes, intention: {result.get('intent', 'inconnue')}):")
            else:
                print(f"✅ Réponse (générée en {elapsed_time:.2f} secondes):")
                
            print("-" * 80 + "\n")
            print(response)
            print("\n" + "-" * 80)
            
            # Afficher l'erreur éventuelle
            if result.get("error") and not result.get("success", True):
                print("\n⚠️ Note: La réponse a été générée malgré une erreur sous-jacente.")
            
        except Exception as e:
            logger.error(f"Une erreur s'est produite: {e}")
            print(f"\n❌ Une erreur s'est produite: {str(e)}")
            print("Veuillez réessayer avec une autre question.")
            
            # Afficher l'erreur détaillée en environnement de développement
            if os.getenv("OHADA_ENV") == "development":
                import traceback
                traceback.print_exc()

if __name__ == "__main__":
    main()