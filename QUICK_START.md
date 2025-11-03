# 🚀 Guide de Démarrage Rapide - OHAD'AI

Guide pour lancer l'application OHAD'AI Expert-Comptable en mode développement.

---

## 📋 Prérequis

### Option Docker (Recommandée) ✅
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installé
- Les clés API dans le fichier `.env` (voir section Configuration)

### Option Manuelle
- Python 3.10+
- Node.js 20+
- PostgreSQL 15+ (optionnel)
- Redis 7+ (optionnel)

---

## 🐳 Option 1 : Lancement avec Docker (RECOMMANDÉ)

### 1. Configuration des variables d'environnement

Créez un fichier `.env` à la racine du projet avec vos clés API :

```env
# Clés API (obligatoires)
OPENAI_API_KEY=votre_clé_openai
DEEPSEEK_API_KEY=votre_clé_deepseek

# JWT Secret (généré automatiquement si absent)
JWT_SECRET_KEY=votre_secret_jwt

# Google OAuth (optionnel)
GOOGLE_CLIENT_ID=votre_client_id_google
```

**Ou copiez le fichier exemple :**
```bash
copy .env.example .env
# Puis éditez .env avec vos vraies clés
```

### 2. Lancer tous les services

```bash
# Démarrer tous les services (backend + frontend + postgres + redis)
docker-compose -f docker-compose.dev.yml up --build

# Ou en arrière-plan (mode détaché)
docker-compose -f docker-compose.dev.yml up -d --build
```

### 3. Accéder à l'application

- **Frontend** : http://localhost:3000
- **Backend API** : http://localhost:8000
- **API Docs** : http://localhost:8000/docs
- **PostgreSQL** : localhost:5434
- **Redis** : localhost:6382

### 4. Arrêter les services

```bash
# Arrêter tous les services
docker-compose -f docker-compose.dev.yml down

# Arrêter et supprimer les volumes (attention : supprime la base de données)
docker-compose -f docker-compose.dev.yml down -v
```

### 5. Voir les logs

```bash
# Tous les services
docker-compose -f docker-compose.dev.yml logs -f

# Un service spécifique
docker-compose -f docker-compose.dev.yml logs -f backend
docker-compose -f docker-compose.dev.yml logs -f frontend
```

---

## 🔧 Option 2 : Lancement Manuel (Développement)

### 1. Backend

**Terminal 1 - Backend Python :**

```bash
# Aller dans le dossier backend
cd backend

# Créer un environnement virtuel (première fois seulement)
python -m venv venv

# Activer l'environnement virtuel
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# Installer les dépendances (première fois seulement)
pip install -r ../requirements.txt

# Configurer l'environnement
set PYTHONPATH=%CD%           # Windows
export PYTHONPATH=$(pwd)      # Linux/Mac

set OHADA_ENV=test            # Windows
export OHADA_ENV=test         # Linux/Mac

# Lancer le serveur backend
python -m uvicorn src.api.ohada_api_server:app --host 0.0.0.0 --port 8000 --reload
```

**Backend accessible sur** : http://localhost:8000

### 2. Frontend

**Terminal 2 - Frontend React :**

```bash
# Aller dans le dossier frontend
cd frontend

# Installer les dépendances (première fois seulement)
npm install

# Lancer le serveur de développement
npm run dev
```

**Frontend accessible sur** : http://localhost:3000

---

## 📊 Architecture des Services

```
┌─────────────────────────────────────────────────────┐
│                    UTILISATEUR                      │
│              http://localhost:3000                  │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│                   FRONTEND                          │
│           React + TypeScript + Vite                 │
│               Port: 3000                            │
└────────────────────┬────────────────────────────────┘
                     │ HTTP Requests
┌────────────────────▼────────────────────────────────┐
│                   BACKEND                           │
│        FastAPI + BGE-M3 + DeepSeek                  │
│               Port: 8000                            │
└─────┬──────────────┬──────────────┬─────────────────┘
      │              │              │
      ▼              ▼              ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│PostgreSQL│  │  Redis   │  │ChromaDB  │
│Port: 5434│  │Port: 6382│  │  Local   │
└──────────┘  └──────────┘  └──────────┘
```

---

## 🧪 Tester l'API Backend

### Avec curl

```bash
# Status de l'API
curl http://localhost:8000/status

# Poser une question
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"Comment calculer l'amortissement linéaire?\", \"n_results\": 5}"
```

### Avec l'interface Swagger

Ouvrez http://localhost:8000/docs dans votre navigateur pour tester l'API interactivement.

---

## 🔍 Vérification du Workflow

### 1. Vérifier que BGE-M3 est chargé

```bash
# Regarder les logs du backend
docker-compose -f docker-compose.dev.yml logs backend | grep "bge-m3"
```

Vous devriez voir :
```
✅ Embedder local BAAI/bge-m3 préchargé avec succès (dim: 1024)
```

### 2. Vérifier ChromaDB

```bash
# Les collections devraient être créées dans backend/chroma_db/
ls backend/chroma_db/
```

### 3. Tester une requête complète

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"Quels sont les principes comptables OHADA?\", \"n_results\": 5}" \
  | python -m json.tool
```

La réponse devrait contenir :
- `answer` : La réponse générée
- `sources` : Liste des 5 sources avec métadonnées
- `search_time` : Temps de recherche
- `model_used` : Modèle LLM utilisé (deepseek-chat)

---

## ⚙️ Variables d'Environnement

### Backend (`.env` ou `backend/.env`)

| Variable | Description | Valeur par défaut |
|----------|-------------|-------------------|
| `OHADA_ENV` | Environnement (test/production) | `test` |
| `OPENAI_API_KEY` | Clé API OpenAI | - |
| `DEEPSEEK_API_KEY` | Clé API DeepSeek | - |
| `JWT_SECRET_KEY` | Secret pour JWT | Auto-généré |
| `DATABASE_URL` | URL PostgreSQL | `postgresql://ohada_user:...` |
| `HOST` | Host du serveur | `0.0.0.0` |
| `PORT` | Port du serveur | `8000` |

### Frontend (`.env.development`)

| Variable | Description | Valeur |
|----------|-------------|--------|
| `VITE_API_URL` | URL du backend | `http://localhost:8000` (local)<br>`http://backend:8000` (Docker) |
| `VITE_APP_NAME` | Nom de l'application | `OHAD'AI Expert-Comptable` |
| `VITE_ENABLE_AUTH` | Activer l'authentification | `true` |

---

## 🛠️ Commandes Utiles

### Docker

```bash
# Rebuild un service spécifique
docker-compose -f docker-compose.dev.yml build backend

# Redémarrer un service
docker-compose -f docker-compose.dev.yml restart backend

# Accéder au shell d'un conteneur
docker-compose -f docker-compose.dev.yml exec backend bash
docker-compose -f docker-compose.dev.yml exec frontend sh

# Voir les conteneurs en cours
docker-compose -f docker-compose.dev.yml ps

# Nettoyer tout (ATTENTION: supprime les données)
docker-compose -f docker-compose.dev.yml down -v --rmi all
```

### Backend

```bash
# Nettoyer le cache Python
cd backend
find . -type d -name __pycache__ -exec rm -rf {} +  # Linux/Mac
FOR /d /r . %d in (__pycache__) DO @IF EXIST "%d" rd /s /q "%d"  # Windows

# Lancer les tests
pytest

# Créer une migration de base de données
alembic revision --autogenerate -m "Description"

# Appliquer les migrations
alembic upgrade head
```

### Frontend

```bash
# Installer une nouvelle dépendance
cd frontend
npm install package-name

# Build de production
npm run build

# Preview du build
npm run preview

# Linter
npm run lint
```

---

## 🐛 Dépannage

### Problème : Le backend ne démarre pas

**Vérifier les logs :**
```bash
docker-compose -f docker-compose.dev.yml logs backend
```

**Solutions courantes :**
- Vérifier que les clés API sont dans `.env`
- Vérifier que PostgreSQL et Redis sont démarrés
- Nettoyer et rebuild : `docker-compose -f docker-compose.dev.yml up --build --force-recreate`

### Problème : Le frontend ne peut pas se connecter au backend

**En mode Docker :**
- Vérifier que `VITE_API_URL=http://backend:8000` dans `docker-compose.dev.yml`

**En mode Manuel :**
- Vérifier que `VITE_API_URL=http://localhost:8000` dans `frontend/.env.development`
- Vérifier que le backend tourne sur le port 8000

### Problème : ChromaDB vide ou collections manquantes

**Importer les documents :**
```bash
# Dans le conteneur backend
docker-compose -f docker-compose.dev.yml exec backend python scripts/import_all_documents.py

# Ou en local
cd backend
python scripts/import_all_documents.py
```

### Problème : Hot reload ne fonctionne pas

**Docker :**
- Les volumes sont configurés, vérifier `docker-compose.dev.yml`
- Essayer de redémarrer : `docker-compose -f docker-compose.dev.yml restart`

**Manuel :**
- Backend : `--reload` devrait être dans la commande uvicorn
- Frontend : Vite detecte les changements automatiquement

---

## 📚 Documentation Supplémentaire

- [Architecture Review](./ARCHITECTURE_REVIEW.md) - Revue complète de l'architecture
- [Migration Guide](./MIGRATION_GUIDE.md) - Guide de migration
- [Backend Improvements](./BACKEND_IMPROVEMENTS.md) - Améliorations du backend
- [Frontend Roadmap](./FRONTEND_ROADMAP.md) - Roadmap du frontend
- [Dev Setup](./DEV_SETUP.md) - Configuration détaillée du développement

---

## 🎯 Checklist de Premier Lancement

- [ ] Docker Desktop installé et lancé
- [ ] Fichier `.env` créé avec les clés API
- [ ] `docker-compose -f docker-compose.dev.yml up --build` exécuté
- [ ] Attendre ~30 secondes (chargement de BGE-M3)
- [ ] Frontend accessible sur http://localhost:3000
- [ ] Backend accessible sur http://localhost:8000
- [ ] Tester une question via l'interface ou l'API
- [ ] Vérifier que les sources s'affichent

---

**Bon développement ! 🚀**
