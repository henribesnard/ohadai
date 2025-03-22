#!/bin/bash
# Script de démarrage pour l'API OHADA Expert-Comptable
# Supporte à la fois les environnements de test et de production

# Définition des couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction pour afficher les messages avec horodatage
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

# Fonction pour afficher les erreurs
error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERREUR:${NC} $1"
}

# Fonction pour afficher les avertissements
warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] ATTENTION:${NC} $1"
}

# Fonction pour afficher les succès
success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] SUCCÈS:${NC} $1"
}

# Paramètres par défaut
ENV=${OHADA_ENV:-"test"}
HOST=${HOST:-"0.0.0.0"}
PORT=${PORT:-"8000"}
CONFIG_PATH=${OHADA_CONFIG_PATH:-"./src/config"}
RELOAD=${RELOAD:-"false"}
DB_PATH=${OHADA_DB_PATH:-"./data/ohada_users.db"}

# Traitement des arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --env|-e)
            ENV="$2"
            shift 2
            ;;
        --port|-p)
            PORT="$2"
            shift 2
            ;;
        --host|-h)
            HOST="$2"
            shift 2
            ;;
        --config|-c)
            CONFIG_PATH="$2"
            shift 2
            ;;
        --reload|-r)
            RELOAD="true"
            shift
            ;;
        --db)
            DB_PATH="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --env, -e ENV        Environnement (test ou production, défaut: test)"
            echo "  --port, -p PORT      Port d'écoute (défaut: 8000)"
            echo "  --host, -h HOST      Hôte d'écoute (défaut: 0.0.0.0)"
            echo "  --config, -c PATH    Chemin de configuration (défaut: ./src/config)"
            echo "  --reload, -r         Activer le rechargement automatique (défaut: désactivé)"
            echo "  --db PATH            Chemin de la base de données SQLite (défaut: ./data/ohada_users.db)"
            echo "  --help               Afficher cette aide"
            exit 0
            ;;
        *)
            error "Option inconnue: $1"
            exit 1
            ;;
    esac
done

# Valider l'environnement
if [[ "$ENV" != "test" && "$ENV" != "production" ]]; then
    error "Environnement invalide: $ENV. Utilisez 'test' ou 'production'."
    exit 1
fi

# Exporter les variables d'environnement
export OHADA_ENV="$ENV"
export HOST="$HOST"
export PORT="$PORT"
export OHADA_CONFIG_PATH="$CONFIG_PATH"
export RELOAD="$RELOAD"
export OHADA_DB_PATH="$DB_PATH"

# Afficher les paramètres de démarrage
log "Démarrage de l'API OHADA Expert-Comptable..."
log "----------------------------------------"
log "Environnement: $ENV"
log "Hôte: $HOST"
log "Port: $PORT"
log "Chemin de configuration: $CONFIG_PATH"
log "Rechargement automatique: $RELOAD"
log "Base de données: $DB_PATH"
log "----------------------------------------"

# Vérifier l'existence du répertoire de configuration
if [ ! -d "$CONFIG_PATH" ]; then
    warning "Le répertoire de configuration '$CONFIG_PATH' n'existe pas. Utilisation des configurations par défaut."
fi

# Vérifier que le répertoire data existe
if [ ! -d "./data" ]; then
    log "Création du répertoire data..."
    mkdir -p ./data
fi

# Créer le répertoire contenant la base de données s'il n'existe pas
DB_DIR=$(dirname "$DB_PATH")
if [ ! -d "$DB_DIR" ]; then
    log "Création du répertoire $DB_DIR..."
    mkdir -p "$DB_DIR"
fi

# En mode production, vérifier si le modèle d'embedding est disponible
if [ "$ENV" == "production" ]; then
    # Vérifier si un fichier de configuration existe pour la production
    if [ ! -f "$CONFIG_PATH/llm_config_production.yaml" ]; then
        warning "Fichier de configuration de production non trouvé: $CONFIG_PATH/llm_config_production.yaml"
        warning "Utilisation de la configuration par défaut."
    else
        success "Configuration de production trouvée."
    fi
    
    # Vérifier si le modèle d'embedding est disponible (optionnel, nécessite python)
    if command -v python3 &>/dev/null; then
        log "Vérification du modèle d'embedding..."
        if python3 -c "import torch; from transformers import AutoTokenizer, AutoModel; print('Modèle disponible!')" &>/dev/null; then
            success "Les dépendances pour le modèle d'embedding sont disponibles."
        else
            warning "Les dépendances pour le modèle d'embedding ne sont pas disponibles."
            warning "Il est recommandé d'installer les dépendances avec 'pip install -r requirements.txt'."
        fi
    fi
fi

# Démarrer le serveur API avec Uvicorn
if [ "$RELOAD" == "true" ]; then
    log "Démarrage du serveur avec rechargement automatique..."
    python -m uvicorn src.api.ohada_api_server:app --host "$HOST" --port "$PORT" --reload
else
    log "Démarrage du serveur..."
    python -m uvicorn src.api.ohada_api_server:app --host "$HOST" --port "$PORT"
fi