from src.vector_db.ohada_vector_db_structure import OhadaVectorDB
import json

def explore_vector_db_collections():
    """Explore et affiche le contenu de toutes les collections dans la base vectorielle"""
    
    # Initialiser la base vectorielle
    vector_db = OhadaVectorDB()
    
    # Récupérer les statistiques
    stats = vector_db.get_collection_stats()
    print("\n=== STATISTIQUES DES COLLECTIONS ===")
    for collection_name, data in stats.items():
        if "error" in data:
            print(f"  - {collection_name}: ERREUR - {data['error']}")
        else:
            print(f"  - {collection_name}: {data.get('count', 'N/A')} documents, Titre: {data.get('title', 'N/A')}")
    
    # Explorer chaque collection
    for collection_name, collection in vector_db.collections.items():
        print(f"\n\n{'=' * 50}")
        print(f"COLLECTION: {collection_name}")
        print(f"TITRE: {vector_db.collection_titles.get(collection_name, 'Non défini')}")
        print(f"{'=' * 50}")
        
        try:
            # Récupérer tous les documents avec leurs métadonnées
            results = collection.get(include=["documents", "metadatas"])
            
            if not results or "ids" not in results or not results["ids"]:
                print("Collection vide ou inaccessible")
                continue
            
            total_docs = len(results["ids"])
            print(f"Nombre total de documents: {total_docs}")
            
            # Limiter l'affichage pour éviter une sortie trop volumineuse
            display_limit = min(10, total_docs)
            print(f"\nAffichage des {display_limit} premiers documents:")
            
            for i in range(display_limit):
                doc_id = results["ids"][i]
                metadata = results["metadatas"][i]
                
                print(f"\n--- Document {i+1}/{display_limit} (ID: {doc_id}) ---")
                
                # Afficher le titre s'il existe
                if "title" in metadata:
                    print(f"Titre: {metadata['title']}")
                else:
                    print("Titre: NON DÉFINI")
                
                # Afficher les métadonnées principales pour l'organisation
                if "partie" in metadata:
                    print(f"Partie: {metadata['partie']}")
                if "chapitre" in metadata:
                    print(f"Chapitre: {metadata['chapitre']}")
                if "document_type" in metadata:
                    print(f"Type: {metadata['document_type']}")
                if "parent_id" in metadata:
                    print(f"Parent ID: {metadata['parent_id']}")
                
                # Afficher un aperçu du texte (limité pour éviter une sortie trop longue)
                doc_text = results["documents"][i]
                text_preview = doc_text[:200] + "..." if len(doc_text) > 200 else doc_text
                print(f"Aperçu du texte: {text_preview}")
                
                # Afficher toutes les autres métadonnées
                print("Autres métadonnées:")
                for key, value in metadata.items():
                    if key not in ["title", "partie", "chapitre", "document_type", "parent_id", "docx_path"]:
                        print(f"  - {key}: {value}")
            
            if total_docs > display_limit:
                print(f"\n... et {total_docs - display_limit} autres documents non affichés")
            
            # Analyse de cohérence
            print("\n--- Analyse de cohérence ---")
            
            # Vérifier la présence des champs importants
            missing_title = sum(1 for i in range(total_docs) if "title" not in results["metadatas"][i])
            missing_partie = sum(1 for i in range(total_docs) if "partie" not in results["metadatas"][i])
            missing_chapitre = sum(1 for i in range(total_docs) if "chapitre" not in results["metadatas"][i] 
                                  and results["metadatas"][i].get("document_type") == "chapitre")
            
            print(f"Documents sans titre: {missing_title} ({missing_title/total_docs*100:.1f}%)")
            print(f"Documents sans partie définie: {missing_partie} ({missing_partie/total_docs*100:.1f}%)")
            print(f"Chapitres sans numéro de chapitre: {missing_chapitre}")
            
            # Vérifier la structure hiérarchique (si applicable)
            if collection_name == "chapitres" or collection_name.startswith("partie_"):
                # Compter les documents par partie
                parties = {}
                for i in range(total_docs):
                    partie = results["metadatas"][i].get("partie")
                    if partie:
                        parties[partie] = parties.get(partie, 0) + 1
                
                print("\nDistribution par partie:")
                for partie, count in sorted(parties.items()):
                    print(f"  - Partie {partie}: {count} documents")
            
        except Exception as e:
            print(f"Erreur lors de l'exploration de la collection {collection_name}: {e}")
    
    # Vérifier la cohérence de la table des matières
    print("\n\n=== COHÉRENCE DE LA TABLE DES MATIÈRES ===")
    
    # Vérifier que tous les chapitres de la TOC sont dans la collection
    if "chapitres" in vector_db.collections and "chapitres" in vector_db.toc:
        toc_ids = {chapitre.get("id") for chapitre in vector_db.toc["chapitres"] if "id" in chapitre}
        
        # Récupérer les IDs des documents dans la collection
        collection_results = vector_db.collections["chapitres"].get(include=[])
        if collection_results and "ids" in collection_results:
            collection_ids = set(collection_results["ids"])
            
            # Comparer les ensembles
            missing_in_collection = toc_ids - collection_ids
            missing_in_toc = collection_ids - toc_ids
            
            print(f"Chapitres dans la TOC: {len(toc_ids)}")
            print(f"Chapitres dans la collection: {len(collection_ids)}")
            print(f"Chapitres dans la TOC mais absents de la collection: {len(missing_in_collection)}")
            print(f"Chapitres dans la collection mais absents de la TOC: {len(missing_in_toc)}")
            
            if missing_in_collection:
                print("\nExemples de chapitres manquants dans la collection:")
                for id in list(missing_in_collection)[:5]:
                    print(f"  - {id}")
            
            if missing_in_toc:
                print("\nExemples de chapitres manquants dans la TOC:")
                for id in list(missing_in_toc)[:5]:
                    print(f"  - {id}")

if __name__ == "__main__":
    explore_vector_db_collections()