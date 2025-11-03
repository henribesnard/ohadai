# Changelog - Configuration Développement

## 2025-11-02 - Configuration Simplifiée

### ✅ Changements Effectués

#### Configuration
- Création de `backend/.env` pour les variables d'environnement
- Ajout de `python-dotenv` dans le backend pour chargement automatique du .env
- Création de `backend/start.bat` pour lancement rapide sous Windows
- Configuration du port frontend à **5175** dans `vite.config.ts` (au lieu de 3000)

#### Documentation
- ✅ Création de `README.md` - Documentation principale complète
- ✅ Création de `DEV_SETUP.md` - Guide de configuration développement
- ✅ Création de `CHANGELOG.md` - Ce fichier

#### Architecture
- ❌ **Abandon de Docker pour le code**: Trop lent, problèmes avec pywin32
- ✅ **Docker uniquement pour services**: PostgreSQL + Redis
- ✅ **Backend local**: Uvicorn avec hot reload (--reload)
- ✅ **Frontend local**: Vite avec HMR

### 📝 Configuration Actuelle

**Services Docker** (via docker-compose.dev.yml):
- PostgreSQL: port 5434
- Redis: port 6382

**Développement local**:
- Backend: port 8000 (Uvicorn avec --reload)
- Frontend: port 5175 (Vite avec HMR)

**Variables d'environnement** (backend/.env):
```env
OHADA_ENV=test
DATABASE_URL=postgresql://ohada_user:changeme_in_production@localhost:5434/ohada
OPENAI_API_KEY=...
DEEPSEEK_API_KEY=...
JWT_SECRET_KEY=dev_secret_key_change_in_production
```

### 🔧 Modifications de Code

**backend/src/api/ohada_api_server.py**:
- Ajout de `from dotenv import load_dotenv`
- Appel de `load_dotenv()` au démarrage
- Chargement automatique des variables depuis .env

**frontend/vite.config.ts**:
- Port changé de 3000 à 5175
- Configuration proxy vers backend:8000

### 🗑️ Documentation Supprimée

Les fichiers suivants ont été **supprimés** car obsolètes:
- ~~`QUICK_START.md`~~ - Utilisait Docker pour tout, remplacé par README.md et DEV_SETUP.md
- ~~`DOCKER_SETUP_GUIDE.md`~~ - Configuration Docker complète, plus utilisée en dev

**À conserver** (encore valides):
- `BACKEND_IMPROVEMENTS.md` - Architecture backend
- `FRONTEND_ROADMAP.md` - Roadmap frontend
- `MIGRATION_GUIDE.md` - Migration de données
- `DOCUMENT_MANAGEMENT_SUMMARY.md` - Gestion documentaire
- Autres fichiers de documentation technique

### 🚀 Commandes de Lancement

**Avant** (complexe):
```bash
docker-compose -f docker-compose.dev.yml up -d --build
# Attendre 10+ minutes pour le build...
```

**Maintenant** (simple):
```bash
# Terminal 1
docker-compose -f docker-compose.dev.yml up postgres redis

# Terminal 2
cd backend
.\start.bat

# Terminal 3
cd frontend
npm run dev
```

### 🎯 Avantages

1. **Démarrage rapide**: ~5 secondes au lieu de 10+ minutes
2. **Hot reload efficace**: Modifications visibles immédiatement
3. **Pas de problèmes de build**: Plus d'erreurs pywin32, UTF-16, etc.
4. **Debugging facile**: Logs directement dans les terminaux
5. **Configuration simple**: Fichier .env centralisé

### ⚠️ Points d'Attention

1. **Port 5175**: Le frontend utilise maintenant 5175 (pas 3000, 5173, ou 5174)
2. **PYTHONPATH**: Doit être défini pour le backend (automatique avec start.bat)
3. **Variables .env**: Le fichier backend/.env doit être créé manuellement
4. **Services Docker**: PostgreSQL et Redis doivent tourner via Docker

### 🔄 Migration depuis l'ancienne config

Si vous aviez l'ancienne configuration Docker complète:

1. Arrêter tous les conteneurs:
   ```bash
   docker-compose -f docker-compose.dev.yml down
   ```

2. Créer `backend/.env` avec les variables nécessaires

3. Relancer selon les nouvelles instructions (voir DEV_SETUP.md)

---

**Prochain changement prévu**: Aucun - Configuration stable
