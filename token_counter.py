import os
import csv
import tiktoken
from pathlib import Path
import pandas as pd
import argparse
from tqdm import tqdm

def count_tokens(text, model="cl100k_base"):
    """
    Compte le nombre de tokens dans un texte en utilisant un encodeur tiktoken
    
    Args:
        text: Le texte à analyser
        model: Le modèle d'encodage à utiliser (cl100k_base pour text-embedding-ada-002)
        
    Returns:
        Le nombre de tokens
    """
    encoder = tiktoken.get_encoding(model)
    tokens = encoder.encode(text)
    return len(tokens)

def extract_text_from_file(file_path):
    """
    Extrait le texte d'un fichier selon son extension
    
    Args:
        file_path: Chemin vers le fichier
        
    Returns:
        Le texte du document ou une chaîne vide en cas d'erreur
    """
    try:
        extension = file_path.suffix.lower()
        
        # Fichiers texte, markdown, etc.
        if extension in ['.txt', '.md', '.html', '.csv', '.json', '.yml', '.yaml']:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
                
        # Fichiers PDF
        elif extension == '.pdf':
            try:
                from PyPDF2 import PdfReader
                reader = PdfReader(file_path)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text
            except ImportError:
                print("PyPDF2 non installé. Utilisez 'pip install PyPDF2' pour l'installer.")
                return ""
                
        # Fichiers Word
        elif extension in ['.doc', '.docx']:
            try:
                import docx
                doc = docx.Document(file_path)
                text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
                return text
            except ImportError:
                print("python-docx non installé. Utilisez 'pip install python-docx' pour l'installer.")
                return ""
        
        # Autres types de fichiers non supportés
        else:
            print(f"Type de fichier non supporté: {extension}")
            return ""
            
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier {file_path}: {e}")
        return ""

def scan_knowledge_base(base_dir, output_file, extensions=['.txt', '.md', '.pdf', '.doc', '.docx', '.html']):
    """
    Parcourt la base de connaissances et calcule le nombre de tokens pour chaque document
    
    Args:
        base_dir: Répertoire de base de la base de connaissances
        output_file: Fichier CSV de sortie
        extensions: Liste des extensions de fichiers à analyser
    """
    base_path = Path(base_dir)
    results = []
    
    # Trouver tous les fichiers avec les extensions spécifiées
    files_to_process = []
    for ext in extensions:
        files_to_process.extend(base_path.glob(f"**/*{ext}"))
    
    print(f"Analyse de {len(files_to_process)} fichiers...")
    
    # Analyser chaque fichier
    for file_path in tqdm(files_to_process):
        # Obtenir le chemin relatif par rapport au dossier de base
        relative_path = file_path.relative_to(base_path)
        
        # Extraire le texte du fichier
        text = extract_text_from_file(file_path)
        
        if text:
            # Calculer le nombre de tokens et la taille du texte
            token_count = count_tokens(text)
            word_count = len(text.split())
            char_count = len(text)
            
            # Calculer le nombre approximatif de pages (300 mots par page)
            page_count = round(word_count / 300, 1)
            
            # Ajouter les résultats
            results.append({
                'file_path': str(relative_path),
                'token_count': token_count,
                'word_count': word_count,
                'character_count': char_count,
                'estimated_pages': page_count,
                'directory': str(relative_path.parent),
                'filename': file_path.name
            })
    
    # Convertir en DataFrame pandas pour faciliter le tri et l'export
    if results:
        df = pd.DataFrame(results)
        
        # Trier par nombre de tokens (décroissant)
        df_sorted = df.sort_values('token_count', ascending=False)
        
        # Enregistrer au format CSV
        df_sorted.to_csv(output_file, index=False)
        
        # Afficher un résumé
        print(f"\nAnalyse terminée. {len(results)} fichiers analysés.")
        print(f"Résultats enregistrés dans {output_file}")
        
        # Afficher quelques statistiques
        print("\nTop 5 des documents les plus volumineux:")
        for i, row in df_sorted.head(5).iterrows():
            print(f"- {row['file_path']}: {row['token_count']} tokens ({row['estimated_pages']} pages)")
        
        print("\nRépartition par taille:")
        print(f"- Documents courts (<5 000 tokens): {len(df[df['token_count'] < 5000])}")
        print(f"- Documents moyens (5 000 - 8 000 tokens): {len(df[(df['token_count'] >= 5000) & (df['token_count'] < 8000)])}")
        print(f"- Documents longs (>8 000 tokens): {len(df[df['token_count'] >= 8000])}")
        
        # Générer un fichier supplémentaire avec des recommandations de découpage
        generate_chunking_recommendations(df_sorted, output_file.replace('.csv', '_recommendations.csv'))
        
    else:
        print("Aucun fichier analysé ou tous les fichiers étaient vides.")

def generate_chunking_recommendations(df, output_file):
    """
    Génère des recommandations de découpage basées sur l'analyse des tokens
    
    Args:
        df: DataFrame contenant les résultats de l'analyse
        output_file: Fichier CSV de sortie pour les recommandations
    """
    recommendations = []
    
    for _, row in df.iterrows():
        if row['token_count'] < 5000:
            chunking_strategy = "Conserver intact"
            priority = "Faible"
        elif row['token_count'] < 8000:
            chunking_strategy = "Découpage par sections principales"
            priority = "Moyenne"
        else:
            chunking_strategy = "Découpage fin nécessaire"
            priority = "Haute"
        
        recommendations.append({
            'file_path': row['file_path'],
            'token_count': row['token_count'],
            'estimated_pages': row['estimated_pages'],
            'chunking_strategy': chunking_strategy,
            'priority': priority,
            'estimated_chunks': max(1, round(row['token_count'] / 4000))  # ~4000 tokens par chunk avec chevauchement
        })
    
    # Créer un DataFrame et l'enregistrer
    df_recommendations = pd.DataFrame(recommendations)
    df_recommendations.to_csv(output_file, index=False)
    
    print(f"\nRecommandations de découpage enregistrées dans {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyse de tokens pour la base de connaissances OHADA")
    parser.add_argument("--base-dir", default="./base_connaissances", help="Répertoire de base de la base de connaissances")
    parser.add_argument("--output", default="tokens_analysis.csv", help="Fichier CSV de sortie")
    parser.add_argument("--extensions", default=".txt,.md,.pdf,.doc,.docx,.html", help="Extensions de fichiers à analyser (séparées par des virgules)")
    
    args = parser.parse_args()
    
    # Convertir la chaîne d'extensions en liste
    extensions_list = args.extensions.split(",")
    
    # Exécuter l'analyse
    scan_knowledge_base(args.base_dir, args.output, extensions_list)