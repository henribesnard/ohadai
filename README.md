# OHAD'AI Expert-Comptable

Système de gestion de connaissances OHADA avec interface web React + FastAPI.

## 🚀 Démarrage Rapide

### Prérequis

- Python 3.10+ avec environnement virtuel activé
- Node.js 20+
- Docker Desktop (pour PostgreSQL et Redis uniquement)

### Configuration Initiale

1. **Cloner le dépôt**
   ```bash
   git clone <url-du-repo>
   cd ohada
   ```

2. **Configuration Backend**

   Créer le fichier `backend/.env`:
   ```env
   # Environnement
   OHADA_ENV=test

   # Base de données
   DATABASE_URL=postgresql://ohada_user:changeme_in_production@localhost:5434/ohada

   # API Keys
   OPENAI_API_KEY=votre_clé_openai
   DEEPSEEK_API_KEY=votre_clé_deepseek

   # JWT
   JWT_SECRET_KEY=dev_secret_key_change_in_production
   ```

3. **Installer les dépendances**

   Backend:
   ```bash
   cd backend
   pip install -r ../requirements.txt
   ```

   Frontend:
   ```bash
   cd frontend
   npm install
   ```

### Lancement de l'application

**Terminal 1 - PostgreSQL et Redis:**
```bash
docker-compose -f docker-compose.dev.yml up postgres redis
```

**Terminal 2 - Backend (PowerShell):**
```powershell
cd backend
$env:PYTHONPATH = $PWD
uvicorn src.api.ohada_api_server:app --host 0.0.0.0 --port 8000 --reload
```

Ou avec le script batch:
```powershell
cd backend
.\start.bat
```

**Terminal 3 - Frontend:**
```bash
cd frontend
npm run dev
```

### Accès

- **Frontend**: http://localhost:5175
- **Backend API**: http://localhost:8000
- **Documentation API**: http://localhost:8000/docs

## 📁 Structure du Projet

```
ohada/
├── backend/
│   ├── src/
│   │   ├── api/              # Endpoints FastAPI
│   │   ├── auth/             # Gestion authentification JWT
│   │   ├── config/           # Configuration LLM et environnement
│   │   ├── db/               # Gestion base de données PostgreSQL
│   │   ├── generation/       # Génération de réponses avec LLM
│   │   ├── retrieval/        # Système de recherche hybride (BM25 + ChromaDB)
│   │   ├── utils/            # Utilitaires
│   │   └── vector_db/        # Interface ChromaDB
│   ├── scripts/              # Scripts d'import et maintenance
│   ├── .env                  # Variables d'environnement (à créer)
│   └── start.bat             # Script de lancement rapide
│
├── frontend/
│   ├── src/
│   │   ├── components/       # Composants React
│   │   ├── pages/            # Pages de l'application
│   │   ├── services/         # Services API
│   │   ├── store/            # State management (Zustand)
│   │   └── types/            # Types TypeScript
│   └── vite.config.ts        # Configuration Vite (port 5175)
│
├── docker-compose.dev.yml    # Services Docker (PostgreSQL, Redis)
└── requirements.txt          # Dépendances Python
```

## 🔧 Configuration

### Ports Utilisés

- **5175**: Frontend (Vite)
- **8000**: Backend (FastAPI)
- **5434**: PostgreSQL (mappé depuis 5432 dans Docker)
- **6382**: Redis (mappé depuis 6379 dans Docker)

### Variables d'Environnement

Le backend charge automatiquement les variables depuis `backend/.env` grâce à `python-dotenv`.

Variables importantes:
- `OHADA_ENV`: `test` ou `production` (détermine quelle config LLM charger)
- `DATABASE_URL`: URL de connexion PostgreSQL
- `OPENAI_API_KEY`: Clé API OpenAI (pour embeddings)
- `DEEPSEEK_API_KEY`: Clé API DeepSeek (pour génération de réponses)
- `JWT_SECRET_KEY`: Clé secrète pour JWT (changer en production!)

### Hot Reload

- **Backend**: Uvicorn redémarre automatiquement à chaque modification de fichier Python (grâce au flag `--reload`)
- **Frontend**: Vite recharge automatiquement les modules modifiés (HMR - Hot Module Replacement)

## 🏗️ Architecture

### Backend (FastAPI)

- **API REST** avec authentification JWT
- **Recherche hybride**: BM25 (lexical) + ChromaDB (sémantique)
- **Base vectorielle**: ChromaDB pour les embeddings
- **Base relationnelle**: PostgreSQL pour les données structurées
- **LLM**: OpenAI (embeddings) + DeepSeek (réponses)

### Frontend (React + TypeScript)

- **Framework**: React 19 + TypeScript
- **Build**: Vite
- **UI**: TailwindCSS + Radix UI
- **State**: Zustand
- **Routing**: React Router
- **HTTP**: Axios + React Query

### Base de Données

**PostgreSQL** stocke:
- Documents OHADA (structure hiérarchique)
- Métadonnées enrichies
- Utilisateurs et sessions
- Conversations

**ChromaDB** stocke:
- Embeddings vectoriels des documents
- Index pour recherche sémantique

## 📚 Fonctionnalités

### Authentification
- Inscription / Connexion avec JWT
- Gestion de session
- Protection des routes

### Recherche
- Recherche hybride (lexicale + sémantique)
- Filtrage par métadonnées
- Citations avec sources OHADA

### Conversations
- Historique des conversations
- Création/suppression de conversations
- Messages avec contexte

### Documents
- Import de documents OHADA
- Structure hiérarchique (Acte, Partie, Chapitre, Section, Article)
- Métadonnées enrichies automatiquement

## 🛠️ Développement

### Commandes Utiles

**Backend:**
```bash
# Tests
pytest

# Format code
black src/

# Linter
pylint src/
```

**Frontend:**
```bash
# Build production
npm run build

# Preview production
npm run preview

# Linter
npm run lint
```

### Ajout de Dépendances

**Python:**
```bash
pip install nouvelle_dependance
pip freeze > requirements.txt
```

**Node:**
```bash
npm install nouvelle_dependance
```

## 🐛 Dépannage

### Port déjà utilisé

Si le port 5175 ou 8000 est occupé:
```bash
# Windows
taskkill /F /IM node.exe
taskkill /F /IM python.exe
```

### PostgreSQL ne démarre pas

```bash
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.dev.yml up postgres redis
```

### Backend ne trouve pas les modules

Vérifier que `PYTHONPATH` est bien défini:
```powershell
$env:PYTHONPATH = "C:\Users\...\ohada\backend"
```

### Variables d'environnement non chargées

Vérifier que le fichier `backend/.env` existe et contient les bonnes valeurs.

## 📝 Documentation Complémentaire

| Fichier | Description |
|---------|-------------|
| `BACKEND_IMPROVEMENTS.md` | Architecture backend détaillée |
| `FRONTEND_ROADMAP.md` | Roadmap et améliorations frontend |
| `MIGRATION_GUIDE.md` | Guide de migration des données |
| `DEV_SETUP.md` | Ce guide (configuration développement) |

## 🔐 Sécurité

⚠️ **Important pour la production:**

1. Changer `JWT_SECRET_KEY` dans `.env`
2. Utiliser des mots de passe forts pour PostgreSQL
3. Activer HTTPS
4. Configurer CORS correctement
5. Ne jamais commiter le fichier `.env`

## 📞 Support

Pour toute question ou problème:
1. Vérifier les logs (backend + frontend)
2. Consulter la documentation API: http://localhost:8000/docs
3. Vérifier les variables d'environnement

---

**Version**: 2.0
**Dernière mise à jour**: 2025-11-02
**Environnement**: Développement local
