# Dockerfile pour OHADA Expert-Comptable
# Supporte les environnements de production et test

# Étape 1: Image de base avec Python
FROM python:3.10-slim

# Étape 2: Métadonnées
LABEL maintainer="OHADA Expert-Comptable Team"
LABEL version="1.0"
LABEL description="Assistant Expert-Comptable OHADA avec APIs conversationnelles"

# Étape 3: Variables d'environnement
ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    OHADA_ENV=production \
    HOST=0.0.0.0 \
    PORT=8000 \
    OHADA_CONFIG_PATH=/app/src/config \
    OHADA_DB_PATH=/app/data/ohada_users.db

# Étape 4: Répertoire de travail
WORKDIR /app

# Étape 5: Installation des dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Option avancée pour les modèles locaux (nécessite plus de mémoire)
ARG INSTALL_LOCAL_MODELS=false
ARG OHADA_ENV=production
RUN if [ "$INSTALL_LOCAL_MODELS" = "true" ] ; then \
    pip install --no-cache-dir sentence-transformers && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    if [ "$OHADA_ENV" = "production" ] ; then \
        echo "Préchargement du modèle d'embedding de production..." && \
        python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('Alibaba-NLP/gte-Qwen2-1.5B-instruct')" ; \
    else \
        echo "Préchargement du modèle d'embedding de test..." && \
        python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')" ; \
    fi \
    fi

# Étape 6: Copie des fichiers du projet
COPY src/ /app/src/
COPY *.sh /app/
RUN chmod +x /app/start.sh

# Étape 7: Création des répertoires nécessaires
RUN mkdir -p /app/data /app/data/vector_db /app/data/history /app/data/embedding_cache

# Étape 8: Expose le port
EXPOSE ${PORT}

# Étape 9: Commande de démarrage
CMD ["/app/start.sh"]