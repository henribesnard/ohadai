import os
import json
import chromadb
import numpy as np
import re
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import torch

# Chargement des variables d'environnement
load_dotenv()

# Définir les modèles de données pour la structure simplifiée
class OhadaReference(BaseModel):
    """Modèle pour les références hiérarchiques aux éléments du plan comptable OHADA"""
    partie_num: int
    chapitre_num: Optional[int] = None
    chapitre_title: Optional[str] = None
    # Les sections et applications sont maintenant intégrées dans les chapitres

class OhadaDocument(BaseModel):
    """Modèle pour les documents du plan comptable OHADA"""
    id: str
    text: str
    metadata: Dict[str, Any]
    reference: OhadaReference
    # Ajout d'un champ pour le chemin du PDF source
    pdf_path: Optional[str] = None

class OhadaTOCEntry(BaseModel):
    """Entrée dans la table des matières OHADA"""
    type: str = Field(..., description="Type d'entrée: partie ou chapitre")
    numero: Union[int, str]
    titre: str
    page_debut: Optional[int] = None
    page_fin: Optional[int] = None
    parent_id: Optional[str] = None
    id: str = Field(..., description="Identifiant unique de l'entrée")

class OhadaEmbedder:
    """Gestionnaire d'embeddings léger pour les documents OHADA utilisant des modèles open source"""
    
    # Pattern Singleton pour éviter de recharger le modèle
    _instance = None
    _model_cache = {}
    
    def __new__(cls, model_name="all-MiniLM-L6-v2"):
        if cls._instance is None or cls._instance.model_name != model_name:
            cls._instance = super(OhadaEmbedder, cls).__new__(cls)
            cls._instance.model_name = model_name
            cls._instance._initialize_model()
        return cls._instance
        
    def _initialize_model(self):
        """Initialise le modèle d'embedding une seule fois"""
        self.embedding_dimension = 384  # Dimension par défaut pour all-MiniLM-L6-v2
        if self.model_name in self._model_cache:
            self.model = self._model_cache[self.model_name]
            print(f"Modèle d'embedding {self.model_name} récupéré du cache")
        else:
            print(f"Chargement du modèle d'embedding: {self.model_name}")
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            try:
                self.model = SentenceTransformer(self.model_name, device=self.device)
                self.embedding_dimension = self.model.get_sentence_embedding_dimension()
                print(f"Modèle chargé: dimension {self.embedding_dimension}")
                self._model_cache[self.model_name] = self.model
            except Exception as e:
                print(f"Erreur de chargement: {e}, utilisation du modèle de secours")
                fallback_model = "all-MiniLM-L6-v2"
                self.model = SentenceTransformer(fallback_model, device=self.device)
                self.embedding_dimension = self.model.get_sentence_embedding_dimension()
                self._model_cache[fallback_model] = self.model
                self.model_name = fallback_model
    
    def generate_embedding(self, text: str) -> List[float]:
        """Génère un embedding pour un texte
        
        Args:
            text: Texte à transformer en embedding
            
        Returns:
            Vecteur d'embedding
        """
        try:
            # Limiter la longueur du texte si nécessaire pour éviter les problèmes de mémoire
            max_length = 8192  # Ajuster selon les capacités de votre matériel
            if len(text.split()) > max_length:
                print(f"Texte tronqué de {len(text.split())} à {max_length} mots pour l'embedding")
                text = " ".join(text.split()[:max_length])
            
            embedding = self.model.encode(text, show_progress_bar=False)
            return embedding.tolist()
        except Exception as e:
            print(f"Erreur lors de la génération d'embedding: {e}")
            # Retourner un vecteur aléatoire en cas d'erreur
            return np.random.randn(self.embedding_dimension).tolist()
    
    def generate_embeddings(self, texts: List[str], batch_size: int = 8) -> List[List[float]]:
        """Génère des embeddings pour une liste de textes
        
        Args:
            texts: Liste des textes à transformer en embeddings
            batch_size: Taille des lots pour le traitement
            
        Returns:
            Liste des embeddings générés
        """
        try:
            # Limiter la longueur des textes si nécessaire
            processed_texts = []
            max_length = 8192
            for text in texts:
                if len(text.split()) > max_length:
                    processed_texts.append(" ".join(text.split()[:max_length]))
                else:
                    processed_texts.append(text)
            
            embeddings = self.model.encode(processed_texts, batch_size=batch_size, show_progress_bar=True)
            return embeddings.tolist()
        except Exception as e:
            print(f"Erreur lors de la génération des embeddings par lots: {e}")
            # Générer séquentiellement en cas d'erreur
            return [self.generate_embedding(text) for text in texts]
    
    def evaluate_embedding_quality(self, corpus: List[str], queries: List[str], relevant_docs: List[List[int]]):
        """Évalue la qualité des embeddings sur un corpus donné
        
        Args:
            corpus: Liste de documents
            queries: Liste de requêtes
            relevant_docs: Liste des indices des documents pertinents pour chaque requête
            
        Returns:
            Métriques d'évaluation (Precision, Recall, MAP)
        """
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np
        
        # Générer les embeddings pour le corpus et les requêtes
        corpus_embeddings = self.model.encode(corpus, show_progress_bar=True)
        query_embeddings = self.model.encode(queries, show_progress_bar=True)
        
        # Calculer les similarités
        results = []
        for query_emb in query_embeddings:
            similarities = cosine_similarity([query_emb], corpus_embeddings)[0]
            results.append(similarities)
        
        # Calculer les métriques
        precision_at_k = []
        recall_at_k = []
        map_scores = []
        
        k = 5  # Nombre de résultats à considérer
        
        for i, (similarity, rel_docs) in enumerate(zip(results, relevant_docs)):
            # Trier les documents par similarité
            sorted_indices = np.argsort(-similarity)
            
            # Précision@k
            precision = len(set(sorted_indices[:k]) & set(rel_docs)) / k
            precision_at_k.append(precision)
            
            # Rappel@k
            recall = len(set(sorted_indices[:k]) & set(rel_docs)) / len(rel_docs) if rel_docs else 0
            recall_at_k.append(recall)
            
            # MAP
            ap = 0.0
            relevant_count = 0
            for j, idx in enumerate(sorted_indices[:k]):
                if idx in rel_docs:
                    relevant_count += 1
                    ap += relevant_count / (j + 1)
            
            map_score = ap / len(rel_docs) if rel_docs else 0
            map_scores.append(map_score)
        
        metrics = {
            "Precision@5": sum(precision_at_k) / len(precision_at_k) if precision_at_k else 0,
            "Recall@5": sum(recall_at_k) / len(recall_at_k) if recall_at_k else 0,
            "MAP@5": sum(map_scores) / len(map_scores) if map_scores else 0
        }
        
        return metrics

class OhadaVectorDB:
    """Gestionnaire de la base de connaissances vectorielle pour le plan comptable OHADA"""
    
    def __init__(self, persist_directory: str = "./data/vector_db", 
                 toc_file: str = "./plan_comptable/ohada_toc.json", 
                 embedding_model: str = "all-MiniLM-L6-v2"):
        """Initialise la base de connaissances vectorielle
        
        Args:
            persist_directory: Répertoire de persistance pour ChromaDB
            toc_file: Chemin vers le fichier JSON contenant la table des matières structurée
            embedding_model: Nom du modèle d'embedding à utiliser
        """
        self.persist_directory = persist_directory
        self.toc_file = toc_file
        
        # Initialiser l'embedder
        self.embedder = OhadaEmbedder(model_name=embedding_model)
        self.embedding_dimension = self.embedder.embedding_dimension
        
        # Créer le répertoire s'il n'existe pas
        os.makedirs(persist_directory, exist_ok=True)
        os.makedirs(os.path.dirname(toc_file), exist_ok=True)
        
        # Chargement de la table des matières si elle existe
        self.toc = self._load_toc()
        
        # Initialiser ChromaDB client
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Initialiser les collections
        self._init_collections()
    
    def _load_toc(self) -> Dict[str, Any]:
        """Charge la table des matières structurée depuis le fichier JSON"""
        if os.path.exists(self.toc_file):
            with open(self.toc_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # Structure vide par défaut
            return {
                "parties": [],
                "chapitres": [],
                "lookup": {}
            }
    
    def save_toc(self, toc_data: Dict[str, Any] = None):
        """Sauvegarde la table des matières dans un fichier JSON"""
        if toc_data:
            self.toc = toc_data
            
        with open(self.toc_file, 'w', encoding='utf-8') as f:
            json.dump(self.toc, f, ensure_ascii=False, indent=2)
    
    def _init_collections(self):
        """Initialise les collections basées sur la structure du plan comptable OHADA"""
        # Collection principale pour le plan comptable
        self.collections = {}
        self.collection_titles = {}  # Dictionnaire pour stocker les titres des collections
        
        try:
            # Essayer de récupérer la collection principale existante
            self.collections["plan_comptable"] = self.client.get_collection(
                name="syscohada_plan_comptable"
            )
            self.collection_titles["plan_comptable"] = "Structure et fonctionnement du plan comptable OHADA"
            print("Collection existante 'syscohada_plan_comptable' récupérée.")
        except Exception:
            # Créer une nouvelle collection si elle n'existe pas
            self.collections["plan_comptable"] = self.client.create_collection(
                name="syscohada_plan_comptable",
                metadata={"description": "Structure et fonctionnement du plan comptable OHADA"}
            )
            self.collection_titles["plan_comptable"] = "Structure et fonctionnement du plan comptable OHADA"
            print(f"Nouvelle collection 'syscohada_plan_comptable' créée.")
        
        # Collections par partie du plan comptable
        partie_titles = {
            1: "OPERATIONS COURANTES",
            2: "OPERATIONS ET PROBLEMES SPECIFIQUES",
            3: "PRESENTATION DES ETATS FINANCIERS ANNUELS",
            4: "COMPTES CONSOLIDES ET COMBINES"
        }
        
        for i in range(1, 5):
            collection_id = f"partie_{i}"
            title = f"Partie {i} du plan comptable OHADA: {partie_titles.get(i, '')}"
            
            try:
                # Essayer de récupérer des collections existantes
                self.collections[collection_id] = self.client.get_collection(
                    name=collection_id
                )
                self.collection_titles[collection_id] = title
                print(f"Collection existante '{collection_id}' récupérée.")
            except Exception:
                # Créer une nouvelle collection si elle n'existe pas
                self.collections[collection_id] = self.client.create_collection(
                    name=collection_id,
                    metadata={
                        "description": title,
                        "partie_num": i,
                        "partie_title": partie_titles.get(i, '')
                    }
                )
                self.collection_titles[collection_id] = title
                print(f"Nouvelle collection '{collection_id}' créée.")
        
        # Collection pour chapitres uniquement (plus de collection séparée pour sections)
        try:
            self.collections["chapitres"] = self.client.get_collection(
                name="chapitres"
            )
            self.collection_titles["chapitres"] = "Chapitres du plan comptable OHADA"
            print("Collection existante 'chapitres' récupérée.")
        except Exception:
            self.collections["chapitres"] = self.client.create_collection(
                name="chapitres",
                metadata={"description": "Chapitres du plan comptable OHADA (incluant sections et applications)"}
            )
            self.collection_titles["chapitres"] = "Chapitres du plan comptable OHADA"
            print(f"Nouvelle collection 'chapitres' créée.")
    
    def display_collection_titles(self):
        """Affiche les titres de toutes les collections"""
        print("\n=== TITRES DES COLLECTIONS ===")
        for collection_id, title in self.collection_titles.items():
            print(f"• {collection_id}: {title}")
            
            # Si c'est une partie, ajouter la liste des chapitres de cette partie
            if collection_id.startswith("partie_"):
                partie_num = int(collection_id.split("_")[1])
                chapitres = self.get_chapitres_by_partie(partie_num)
                if chapitres:
                    print(f"  Chapitres dans cette partie:")
                    for chapitre in chapitres:
                        print(f"    - Chapitre {chapitre['number']}: {chapitre['title']}")
                else:
                    print(f"  Aucun chapitre trouvé dans cette partie")
            
            # Ajouter des détails sur le nombre de documents dans la collection
            count = self.collections[collection_id].count()
            print(f"  Documents: {count}")
            print("")
    
    def get_chapitres_by_partie(self, partie_num: int) -> List[Dict[str, Any]]:
        """Récupère la liste des chapitres d'une partie depuis la table des matières
        
        Args:
            partie_num: Numéro de la partie
            
        Returns:
            Liste des chapitres
        """
        chapitres = []
        partie_id = f"partie_{partie_num}"
        
        # Récupérer les chapitres depuis la table des matières
        if self.toc and "chapitres" in self.toc:
            for chapitre in self.toc["chapitres"]:
                if chapitre.get("parent_id") == partie_id:
                    chapitres.append({
                        "number": chapitre.get("numero"),
                        "title": chapitre.get("titre"),
                        "id": chapitre.get("id")
                    })
        
        # Trier les chapitres par numéro
        chapitres.sort(key=lambda x: x["number"])
        
        return chapitres
    
    def add_document(self, collection_name: str, document: OhadaDocument, embedding: List[float] = None):
        """Ajoute un document à une collection
        
        Args:
            collection_name: Nom de la collection
            document: Document à ajouter
            embedding: Embedding du document (optionnel, généré automatiquement si non fourni)
        """
        # Vérifier que la collection existe
        if collection_name not in self.collections:
            raise ValueError(f"Collection {collection_name} non trouvée")
        
        # Générer l'embedding si non fourni
        if embedding is None:
            embedding = self.embedder.generate_embedding(document.text)
        
        # Vérifier la dimension de l'embedding
        if len(embedding) != self.embedding_dimension:
            print(f"Avertissement: Dimension de l'embedding ({len(embedding)}) ne correspond pas à la dimension attendue ({self.embedding_dimension})")
            # Régénérer l'embedding avec le bon modèle
            embedding = self.embedder.generate_embedding(document.text)
        
        # Ajouter le document
        self.collections[collection_name].add(
            ids=[document.id],
            documents=[document.text],
            metadatas=[document.metadata],
            embeddings=[embedding]
        )
    
    def query(self, 
             collection_name: str = "chapitres",  # Par défaut, chercher dans les chapitres
             query_text: str = None, 
             query_embedding: List[float] = None,
             filter_dict: Dict[str, Any] = None,
             n_results: int = 5):
        """Recherche dans une collection
        
        Args:
            collection_name: Nom de la collection à interroger
            query_text: Texte de la requête (optionnel si query_embedding est fourni)
            query_embedding: Embedding de la requête (prioritaire sur query_text)
            filter_dict: Filtres (optionnel)
            n_results: Nombre de résultats à retourner
            
        Returns:
            Résultats de la recherche
        """
        # Vérifier que la collection existe
        if collection_name not in self.collections:
            raise ValueError(f"Collection {collection_name} non trouvée")
        
        # Vérifier qu'au moins un des paramètres de requête est fourni
        if query_text is None and query_embedding is None:
            raise ValueError("Au moins un paramètre de requête (query_text ou query_embedding) doit être fourni")
        
        # Générer l'embedding de la requête si nécessaire
        if query_embedding is None and query_text is not None:
            query_embedding = self.embedder.generate_embedding(query_text)
        
        # Vérifier la dimension de l'embedding
        if query_embedding and len(query_embedding) != self.embedding_dimension:
            print(f"Avertissement: Dimension de l'embedding de requête ({len(query_embedding)}) ne correspond pas à la dimension attendue ({self.embedding_dimension})")
            # Régénérer l'embedding avec le bon modèle
            if query_text:
                query_embedding = self.embedder.generate_embedding(query_text)
        
        # Exécuter la requête
        results = self.collections[collection_name].query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=filter_dict,
            include=["documents", "metadatas", "distances"]
        )
        
        return results
    
    def get_document_by_id(self, collection_name: str, document_id: str):
        """Récupère un document par son ID
        
        Args:
            collection_name: Nom de la collection
            document_id: ID du document
            
        Returns:
            Document correspondant
        """
        if collection_name not in self.collections:
            raise ValueError(f"Collection {collection_name} non trouvée")
        
        return self.collections[collection_name].get(ids=[document_id])
    
    def get_collection_stats(self):
        """Retourne des statistiques sur les collections"""
        stats = {}
        for name, collection in self.collections.items():
            try:
                count = collection.count()
                stats[name] = {
                    "count": count,
                    "metadata": collection.metadata,
                    "title": self.collection_titles.get(name, "Sans titre")
                }
            except Exception as e:
                stats[name] = {"error": str(e)}
        return stats
    
    def delete_collection(self, collection_name: str):
        """Supprime une collection et son contenu
        
        Args:
            collection_name: Nom de la collection à supprimer
        """
        if collection_name in self.collections:
            try:
                self.client.delete_collection(name=collection_name)
                del self.collections[collection_name]
                if collection_name in self.collection_titles:
                    del self.collection_titles[collection_name]
                print(f"Collection '{collection_name}' supprimée avec succès")
            except Exception as e:
                print(f"Erreur lors de la suppression de la collection '{collection_name}': {e}")
        else:
            print(f"Collection '{collection_name}' non trouvée")
    
    def reset_database(self):
        """Réinitialise entièrement la base de données vectorielle"""
        # Supprimer toutes les collections
        for name in list(self.collections.keys()):
            self.delete_collection(name)
        
        # Réinitialiser les collections
        self._init_collections()
        
        print("Base de données vectorielle réinitialisée avec succès")
    
    def evaluate_search_quality(self, test_queries: List[Dict[str, Any]]):
        """Évalue la qualité de la recherche sur un ensemble de requêtes de test
        
        Args:
            test_queries: Liste de dictionnaires contenant:
                          - 'query': texte de la requête
                          - 'expected_ids': liste des IDs de documents attendus
                          - 'collection': (optionnel) collection à interroger
            
        Returns:
            Dictionnaire des métriques d'évaluation
        """
        results = []
        
        for query_info in test_queries:
            query_text = query_info['query']
            expected_ids = query_info['expected_ids']
            collection = query_info.get('collection', 'chapitres')
            
            # Effectuer la recherche
            search_results = self.query(
                collection_name=collection,
                query_text=query_text,
                n_results=10
            )
            
            # Récupérer les IDs des résultats
            result_ids = search_results['ids'][0]
            
            # Calculer les métriques
            # Precision@k: parmi les k premiers résultats, combien sont pertinents
            precision_5 = len(set(result_ids[:5]) & set(expected_ids)) / 5 if len(result_ids) >= 5 else 0
            
            # Recall@k: parmi tous les documents pertinents, combien sont dans les k premiers résultats
            recall_5 = len(set(result_ids[:5]) & set(expected_ids)) / len(expected_ids) if expected_ids else 0
            
            # MRR (Mean Reciprocal Rank): position du premier document pertinent
            mrr = 0
            for i, doc_id in enumerate(result_ids):
                if doc_id in expected_ids:
                    mrr = 1 / (i + 1)
                    break
            
            results.append({
                'query': query_text,
                'precision@5': precision_5,
                'recall@5': recall_5,
                'mrr': mrr
            })
        
        # Calculer les moyennes
        avg_precision = sum(r['precision@5'] for r in results) / len(results) if results else 0
        avg_recall = sum(r['recall@5'] for r in results) / len(results) if results else 0
        avg_mrr = sum(r['mrr'] for r in results) / len(results) if results else 0
        
        return {
            'avg_precision@5': avg_precision,
            'avg_recall@5': avg_recall,
            'avg_mrr': avg_mrr,
            'details': results
        }


class OhadaMetadataBuilder:
    """Générateur de métadonnées pour les documents OHADA"""
    
    @staticmethod
    def build_metadata_from_pdf_path(pdf_path: str, toc_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Construit les métadonnées à partir du chemin d'un fichier PDF
        
        Args:
            pdf_path: Chemin vers le fichier PDF
            toc_data: Données de la table des matières
            
        Returns:
            Métadonnées structurées
        """
        metadata = {}
        
        # Extraire les informations du nom de fichier
        file_name = os.path.basename(pdf_path)
        dir_name = os.path.dirname(pdf_path)
        
        # Déterminer la partie
        partie_match = re.search(r'partie_(\d+)', dir_name)
        if partie_match:
            metadata["partie"] = int(partie_match.group(1))
        
        # Déterminer le chapitre
        chapitre_match = re.search(r'chapitre_(\d+)', file_name)
        if chapitre_match:
            metadata["chapitre"] = int(chapitre_match.group(1))
        
        # Générer un ID
        if "partie" in metadata and "chapitre" in metadata:
            metadata["id"] = f"partie_{metadata['partie']}_chapitre_{metadata['chapitre']}"
            metadata["document_type"] = "chapitre"
            metadata["parent_id"] = f"partie_{metadata['partie']}"
        
        # Rechercher des informations supplémentaires dans la table des matières si disponible
        if toc_data and "lookup" in toc_data and metadata.get("id") in toc_data["lookup"]:
            toc_entry = toc_data["lookup"][metadata["id"]]
            metadata["title"] = toc_entry.get("title", f"Chapitre {metadata.get('chapitre', '')}")
            metadata["page_debut"] = toc_entry.get("start_page")  # Utiliser start_page au lieu de page_debut
            metadata["page_fin"] = toc_entry.get("end_page")     # Utiliser end_page au lieu de page_fin
        else:
            metadata["title"] = f"Chapitre {metadata.get('chapitre', '')}"
        
        return metadata
    
    @staticmethod
    def build_reference_from_metadata(metadata: Dict[str, Any]) -> OhadaReference:
        """Construit une référence hiérarchique à partir des métadonnées
        
        Args:
            metadata: Métadonnées du document
            
        Returns:
            Référence hiérarchique
        """
        return OhadaReference(
            partie_num=metadata.get("partie", 1),
            chapitre_num=metadata.get("chapitre"),
            chapitre_title=metadata.get("title")
        )


# Exemple d'utilisation
if __name__ == "__main__":
    import re
    import argparse
    import shutil
    
    parser = argparse.ArgumentParser(description="Gestionnaire de la base de données vectorielle OHADA")
    parser.add_argument("--reset", action="store_true", help="Réinitialiser la base de données vectorielle")
    parser.add_argument("--model", default="all-MiniLM-L6-v2", 
                      help="Modèle d'embedding à utiliser")
    parser.add_argument("--test", action="store_true", help="Tester la qualité des embeddings")
    parser.add_argument("--toc-file", default="./plan_comptable/ohada_toc.json", 
                      help="Chemin vers le fichier JSON de la table des matières")
    
    args = parser.parse_args()
    
    # Initialiser la base vectorielle
    vector_db = OhadaVectorDB(embedding_model=args.model, toc_file=args.toc_file)
    
    # Réinitialiser la base si demandé
    if args.reset:
        response = input("Êtes-vous sûr de vouloir réinitialiser la base de données vectorielle? (y/n): ")
        if response.lower() == 'y':
            vector_db.reset_database()
    
    # Test de qualité des embeddings si demandé
    if args.test:
        test_corpus = [
            "Les comptes de la classe 1 enregistrent les ressources durables.",
            "Les comptes de la classe 2 enregistrent les immobilisations.",
            "Les comptes de la classe 3 enregistrent les stocks.",
            "Les comptes de la classe 4 enregistrent les tiers.",
            "Les comptes de la classe 5 enregistrent les opérations de trésorerie."
        ]
        
        test_queries = [
            "Quels comptes utilisés pour les ressources durables?",
            "Comment enregistrer les immobilisations?",
            "Où sont les stocks dans le plan comptable?"
        ]
        
        # Définir les documents pertinents pour chaque requête
        relevant_docs = [
            [0],  # La première requête devrait trouver le premier document
            [1],  # La deuxième requête devrait trouver le deuxième document
            [2]   # La troisième requête devrait trouver le troisième document
        ]
        
        metrics = vector_db.embedder.evaluate_embedding_quality(test_corpus, test_queries, relevant_docs)
        print("\nÉvaluation de la qualité des embeddings:")
        for metric, value in metrics.items():
            print(f"  - {metric}: {value:.4f}")
    
    # Afficher les statistiques des collections
    stats = vector_db.get_collection_stats()
    print("\nStatistiques des collections:")
    for collection, data in stats.items():
        if "error" in data:
            print(f"  - {collection}: ERREUR - {data['error']}")
        else:
            print(f"  - {collection}: {data.get('count', 'N/A')} documents")
    
    # Afficher les titres des collections
    vector_db.display_collection_titles()