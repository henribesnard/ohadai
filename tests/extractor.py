import os
import logging
from pathlib import Path
import argparse

# Import des modules
from ohada_pdf_splitter import split_ohada_plan_comptable
from ohada_chapter_splitter import split_by_structure
from ohada_pdf_to_markdown import convert_pdf_files_to_markdown

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ohada_main")

def process_ohada_document(pdf_path, output_dir, toc_json_path=None, use_api=True, steps=None):
    """
    Traite le plan comptable OHADA en exécutant toutes les étapes
    
    Args:
        pdf_path: Chemin vers le PDF du plan comptable
        output_dir: Répertoire de sortie
        toc_json_path: Chemin vers le fichier JSON de la table des matières (si None, toutes les étapes sont exécutées)
        use_api: Utiliser l'API OpenAI pour la conversion Markdown
        steps: Liste des étapes à exécuter (toutes si None)
    """
    # Créer les répertoires de sortie
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    parties_dir = output_dir / "parties"
    elements_dir = output_dir / "elements"
    markdown_dir = output_dir / "markdown"
    
    # Fichier TOC
    toc_file = Path(toc_json_path) if toc_json_path else output_dir / "ohada_toc.json"
    
    # Exécuter les étapes selon les besoins
    all_steps = ["split", "chapters", "markdown"]
    steps_to_run = steps if steps else all_steps
    
    results = {}
    
    # Vérifier si nous avons un fichier TOC valide
    if not toc_json_path:
        if not os.path.exists(toc_file):
            logger.error(f"Aucun fichier de table des matières trouvé: {toc_file}")
            logger.error("Veuillez fournir un fichier JSON de table des matières valide avec --toc-json-path")
            return None
    
    # Étape 1: Diviser en parties
    if "split" in steps_to_run:
        logger.info("Étape 1: Division du PDF en parties")
        results["parties"] = split_ohada_plan_comptable(pdf_path, parties_dir, toc_file)
        logger.info(f"  - {len(results['parties'])} parties créées")
    
    # Étape 2: Diviser en chapitres et sections
    if "chapters" in steps_to_run:
        logger.info("Étape 2: Division en chapitres, sections et applications")
        if not os.path.exists(toc_file):
            logger.error(f"Le fichier TOC n'existe pas: {toc_file}")
            logger.error("Veuillez fournir un fichier JSON de table des matières valide avec --toc-json-path")
            return None
        
        results["elements"] = split_by_structure(parties_dir, toc_file, elements_dir)
        logger.info(f"  - {len(results['elements'])} éléments créés")
    
    # Étape 3: Convertir en Markdown avec GPT-4o
    if "markdown" in steps_to_run:
        logger.info("Étape 3: Conversion en Markdown avec GPT-4o")
        if not os.path.exists(toc_file):
            logger.error(f"Le fichier TOC n'existe pas: {toc_file}")
            logger.error("Veuillez fournir un fichier JSON de table des matières valide avec --toc-json-path")
            return None
        
        results["markdown"] = convert_pdf_files_to_markdown(elements_dir, toc_file, markdown_dir, use_api)
        logger.info(f"  - {len(results['markdown'])} fichiers Markdown créés")
    
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Processeur du plan comptable OHADA")
    parser.add_argument("pdf_path", help="Chemin vers le PDF du plan comptable OHADA")
    parser.add_argument("--output-dir", "-o", default="./extracted_ohada",
                        help="Répertoire de sortie")
    parser.add_argument("--toc-json-path", "-t", 
                        help="Chemin vers le fichier JSON de la table des matières (si fourni, l'étape d'extraction est ignorée)")
    parser.add_argument("--no-api", action="store_true",
                        help="Ne pas utiliser l'API OpenAI (conversion basique)")
    parser.add_argument("--steps", nargs="+", choices=["split", "chapters", "markdown"],
                        help="Étapes à exécuter (toutes par défaut)")
    
    args = parser.parse_args()
    
    results = process_ohada_document(
        args.pdf_path,
        args.output_dir,
        toc_json_path=args.toc_json_path,
        use_api=not args.no_api,
        steps=args.steps
    )
    
    if results:
        print("\nTraitement terminé avec succès!")
        print(f"Les fichiers sont disponibles dans le répertoire: {args.output_dir}")
    else:
        print("\nTraitement interrompu en raison d'erreurs.")