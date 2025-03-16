#!/usr/bin/env python
"""
Point d'entrée principal pour le système OHADA Expert-Comptable.
Ce script permet de lancer le serveur API ou d'autres composants du système.
"""

import os
import sys
import argparse
import logging
import uvicorn
from dotenv import load_dotenv
from pathlib import Path

# Configurer le logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ohada.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("ohada")

# Charger les variables d'environnement
load_dotenv()

def verify_environment():
    """
    Vérifie que l'environnement est correctement configuré.
    """
    # Vérifier les variables d'environnement nécessaires
    required_vars = [
        'OPENAI_API_KEY',  # Pour OpenAI (GPT-4, etc.)
        'DEEPSEEK_API_KEY'  # Pour DeepSeek (optionnel)
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if 'OPENAI_API_KEY' in missing_vars:
        logger.warning("Variable d'environnement OPENAI_API_KEY non définie. Certaines fonctionnalités pourraient ne pas fonctionner.")
    
    # Vérifier l'existence des répertoires nécessaires
    data_dir = Path("./data")
    vector_db_dir = data_dir / "vector_db"
    history_dir = data_dir / "history"
    
    for directory in [data_dir, vector_db_dir, history_dir]:
        if not directory.exists():
            logger.info(f"Création du répertoire: {directory}")
            directory.mkdir(parents=True, exist_ok=True)
    
    # Vérifier que le fichier de configuration LLM existe
    config_dir = Path("./src/config")
    llm_config_file = config_dir / "llm_config.yaml"
    
    if not llm_config_file.exists():
        logger.warning(f"Fichier de configuration {llm_config_file} non trouvé. Utilisation des valeurs par défaut.")

def run_api_server(host="0.0.0.0", port=8000, reload=False):
    """
    Lance le serveur API FastAPI.
    
    Args:
        host: Hôte sur lequel écouter
        port: Port sur lequel écouter
        reload: Activer le rechargement automatique
    """
    logger.info(f"Démarrage du serveur API sur {host}:{port}")
    uvicorn.run("src.api.ohada_api_server:app", host=host, port=port, reload=reload)

def run_streamlit_app():
    """
    Lance l'application Streamlit.
    """
    logger.info("Démarrage de l'application Streamlit")
    os.system("streamlit run src/ohada_app.py")

def init_database(reset=False, model=None):
    """
    Initialise ou réinitialise la base de données vectorielle.
    
    Args:
        reset: Si True, réinitialise complètement la base de données
        model: Modèle d'embedding à utiliser
    """
    from src.vector_db.ohada_vector_db_structure import OhadaVectorDB
    
    logger.info("Initialisation de la base de données vectorielle")
    
    # Paramètres du modèle d'embedding
    embedding_model = model or "all-MiniLM-L6-v2"
    logger.info(f"Utilisation du modèle d'embedding: {embedding_model}")
    
    # Initialiser la base de données
    vector_db = OhadaVectorDB(embedding_model=embedding_model)
    
    if reset:
        logger.warning("Réinitialisation de la base de données vectorielle")
        confirmation = input("Êtes-vous sûr de vouloir réinitialiser la base de données? (y/n): ")
        if confirmation.lower() == 'y':
            vector_db.reset_database()
            logger.info("Base de données réinitialisée avec succès")
        else:
            logger.info("Réinitialisation annulée")
    
    # Afficher les statistiques
    stats = vector_db.get_collection_stats()
    logger.info("Statistiques de la base de données:")
    for collection, data in stats.items():
        if "error" in data:
            logger.error(f"  - {collection}: ERREUR - {data['error']}")
        else:
            logger.info(f"  - {collection}: {data.get('count', 'N/A')} documents")
    
    return vector_db

def ingest_documents(docx_dir=None, reset=False, model=None, partie=None):
    """
    Ingère des documents Word dans la base de données vectorielle.
    
    Args:
        docx_dir: Répertoire contenant les fichiers Word
        reset: Si True, réinitialise la base de données avant l'ingestion
        model: Modèle d'embedding à utiliser
        partie: Numéro de partie à traiter (optionnel)
    """
    from src.vector_db.ohada_document_ingestor import ingest_ohada_docx
    
    # Vérifier le répertoire de documents
    if not docx_dir:
        docx_dir = "./plan_comptable/chapitres_word"
        
    if not os.path.exists(docx_dir):
        logger.error(f"Répertoire de documents {docx_dir} non trouvé")
        return False
        
    # Initialiser la base de données
    vector_db = init_database(reset=reset, model=model)
    
    # Ingérer les documents
    if partie:
        logger.info(f"Ingestion des documents de la partie {partie}")
        partie_dir = os.path.join(docx_dir, f"partie_{partie}")
        if os.path.exists(partie_dir):
            ingest_ohada_docx(partie_dir, vector_db)
        else:
            logger.error(f"Répertoire de la partie {partie} non trouvé: {partie_dir}")
            return False
    else:
        logger.info(f"Ingestion des documents du répertoire: {docx_dir}")
        ingest_ohada_docx(docx_dir, vector_db)
    
    return True

def test_query(query, n_results=5, include_sources=True, partie=None, chapitre=None):
    """
    Teste une requête sur la base de connaissances OHADA.
    
    Args:
        query: Requête à tester
        n_results: Nombre de résultats à retourner
        include_sources: Inclure les sources dans la réponse
        partie: Numéro de partie (optionnel)
        chapitre: Numéro de chapitre (optionnel)
    """
    from src.retrieval.ohada_hybrid_retriever import create_ohada_query_api
    
    logger.info(f"Test de requête: {query}")
    
    # Créer l'API
    retriever = create_ohada_query_api()
    
    # Exécuter la requête
    result = retriever.search_ohada_knowledge(
        query=query,
        partie=partie,
        chapitre=chapitre,
        n_results=n_results,
        include_sources=include_sources
    )
    
    # Afficher les performances
    performance = result.get("performance", {})
    logger.info(f"Requête exécutée en {performance.get('total_time_seconds', 0):.2f} secondes")
    
    # Afficher la réponse
    print("\n=== RÉPONSE ===\n")
    print(result["answer"])
    
    # Afficher les sources
    if include_sources and "sources" in result:
        print("\n=== SOURCES ===\n")
        for i, source in enumerate(result["sources"], 1):
            print(f"Source {i} (score: {source['relevance_score']:.2f}):")
            if "title" in source["metadata"]:
                print(f"Titre: {source['metadata']['title']}")
            print(f"Type: {source['metadata'].get('document_type', 'Non spécifié')}")
            if "partie" in source["metadata"]:
                print(f"Partie: {source['metadata']['partie']}")
            if "chapitre" in source["metadata"]:
                print(f"Chapitre: {source['metadata']['chapitre']}")
            print(f"Extrait: {source['preview']}")
            print()
    
    return result

def build_toc(docx_dir=None, toc_file=None):
    """
    Construit une table des matières à partir des fichiers Word.
    
    Args:
        docx_dir: Répertoire contenant les fichiers Word
        toc_file: Chemin du fichier de sortie pour la table des matières
    """
    from src.vector_db.ohada_document_ingestor import build_toc_from_docx
    
    # Vérifier le répertoire de documents
    if not docx_dir:
        docx_dir = "./plan_comptable/chapitres_word"
        
    if not toc_file:
        toc_file = "./plan_comptable/ohada_toc.json"
    
    if not os.path.exists(docx_dir):
        logger.error(f"Répertoire de documents {docx_dir} non trouvé")
        return False
        
    # Construire la table des matières
    logger.info(f"Construction de la table des matières à partir de {docx_dir}")
    toc = build_toc_from_docx(docx_dir, toc_file)
    
    return toc is not None

def main():
    """
    Fonction principale pour le point d'entrée.
    """
    # Définir le parser d'arguments
    parser = argparse.ArgumentParser(
        description="Point d'entrée principal pour le système OHADA Expert-Comptable",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    # Sous-commandes
    subparsers = parser.add_subparsers(dest="command", help="Commande à exécuter")
    
    # Commande: server
    server_parser = subparsers.add_parser("server", help="Lancer le serveur API")
    server_parser.add_argument("--host", default="0.0.0.0", help="Hôte sur lequel écouter")
    server_parser.add_argument("--port", type=int, default=8000, help="Port sur lequel écouter")
    server_parser.add_argument("--reload", action="store_true", help="Activer le rechargement automatique")
    
    # Commande: app
    app_parser = subparsers.add_parser("app", help="Lancer l'application Streamlit")
    
    # Commande: init
    init_parser = subparsers.add_parser("init", help="Initialiser la base de données")
    init_parser.add_argument("--reset", action="store_true", help="Réinitialiser la base de données")
    init_parser.add_argument("--model", default="all-MiniLM-L6-v2", 
                          help="Modèle d'embedding à utiliser")
    
    # Commande: ingest
    ingest_parser = subparsers.add_parser("ingest", help="Ingérer des documents")
    ingest_parser.add_argument("--docx-dir", default="./plan_comptable/chapitres_word", 
                            help="Répertoire contenant les fichiers Word")
    ingest_parser.add_argument("--reset", action="store_true", 
                            help="Réinitialiser la base de données avant l'ingestion")
    ingest_parser.add_argument("--model", default="all-MiniLM-L6-v2", 
                            help="Modèle d'embedding à utiliser")
    ingest_parser.add_argument("--partie", type=int, choices=[1, 2, 3, 4], 
                            help="Traiter uniquement une partie spécifique (1-4)")
    
    # Commande: query
    query_parser = subparsers.add_parser("query", help="Tester une requête")
    query_parser.add_argument("query", help="Requête à tester")
    query_parser.add_argument("--n-results", type=int, default=5, 
                           help="Nombre de résultats à retourner")
    query_parser.add_argument("--no-sources", action="store_true", 
                           help="Ne pas inclure les sources dans la réponse")
    query_parser.add_argument("--partie", type=int, choices=[1, 2, 3, 4],
                           help="Filtrer par numéro de partie (1-4)")
    query_parser.add_argument("--chapitre", type=int,
                           help="Filtrer par numéro de chapitre")
    
    # Commande: build-toc
    toc_parser = subparsers.add_parser("build-toc", help="Construire la table des matières")
    toc_parser.add_argument("--docx-dir", default="./plan_comptable/chapitres_word", 
                         help="Répertoire contenant les fichiers Word")
    toc_parser.add_argument("--toc-file", default="./plan_comptable/ohada_toc.json", 
                         help="Chemin du fichier de sortie pour la table des matières")
    
    # Analyser les arguments
    args = parser.parse_args()
    
    # Vérifier l'environnement
    verify_environment()
    
    # Exécuter la commande appropriée
    if args.command == "server":
        run_api_server(host=args.host, port=args.port, reload=args.reload)
    elif args.command == "app":
        run_streamlit_app()
    elif args.command == "init":
        init_database(reset=args.reset, model=args.model)
    elif args.command == "ingest":
        ingest_documents(docx_dir=args.docx_dir, reset=args.reset, 
                       model=args.model, partie=args.partie)
    elif args.command == "query":
        test_query(args.query, n_results=args.n_results, 
                 include_sources=not args.no_sources, 
                 partie=args.partie, chapitre=args.chapitre)
    elif args.command == "build-toc":
        build_toc(docx_dir=args.docx_dir, toc_file=args.toc_file)
    else:
        # Afficher l'aide si aucune commande n'est spécifiée
        parser.print_help()

if __name__ == "__main__":
    main()