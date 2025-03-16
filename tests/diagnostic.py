import os
import chromadb
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv()

# Initialisation
client = chromadb.PersistentClient(path="./data/vector_db")
collection = client.get_collection("syscohada_plan_comptable")  # Correction ici
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Générer l'embedding pour la requête
response = openai_client.embeddings.create(
    model="text-embedding-3-small",
    input=["structure des comptes"],
    dimensions=1536
)
query_embedding = response.data[0].embedding

# Rechercher sans filtres
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=10,
    include=["documents", "metadatas", "distances"]
)

# Analyser les résultats
print(f"Nombre de résultats: {len(results['ids'][0])}")
for i in range(len(results['ids'][0])):
    doc_id = results['ids'][0][i]
    metadata = results['metadatas'][0][i]
    distance = results['distances'][0][i]
    text = results['documents'][0][i][:200]
    print(f"ID: {doc_id}, Distance: {distance}")
    print(f"Metadata: {metadata}")
    print(f"Texte: {text}...")
    print()

# Rechercher les documents du chapitre 1
try:
    chapitre1_docs = collection.get(
        where={"$and": [{"chapitre": 1}, {"partie": 1}]},
        include=["metadatas", "documents"]
    )
    print(f"Documents du chapitre 1, partie 1: {len(chapitre1_docs['ids'])}")
    
    # Afficher quelques exemples
    for i in range(min(3, len(chapitre1_docs['ids']))):
        print(f"\nDocument {i+1} (ID: {chapitre1_docs['ids'][i]}):")
        print(f"Métadonnées: {chapitre1_docs['metadatas'][i]}")
        print(f"Extrait: {chapitre1_docs['documents'][i][:200]}...")
except Exception as e:
    print(f"Erreur lors de la recherche de documents du chapitre 1: {e}")