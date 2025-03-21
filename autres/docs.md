# lancer le serveur API fastAPI
python ohada.py server --port 8080 --reload

# Lancer l'interface Streamlit
python ohada.py app

# Initialise ou réinitialise la base de données
python ohada.py init --reset --model "all-MiniLM-L6-v2"

# Ingère des documents dans la base de données
python ohada.py ingest --docx-dir "./documents" --partie 2

# tester une requête en ligne de commande 
python ohada.py query "Comment fonctionne l'amortissement dégressif dans le SYSCOHADA?"

# Construit la table des matières à partir des fichiers Word
python ohada.py build-toc