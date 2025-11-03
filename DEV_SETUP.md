# Configuration Développement - OHAD'AI

Guide simple pour lancer l'application en développement.

## 🎯 Configuration Actuelle (2025-11-02)

### Architecture
- **Backend local** (Python/Uvicorn) avec hot reload
- **Frontend local** (Vite) avec HMR
- **Services Docker** (PostgreSQL + Redis uniquement)

### Ports
- Frontend: **5175**
- Backend: **8000**
- PostgreSQL: **5434** (mappé depuis 5432)
- Redis: **6382** (mappé depuis 6379)

## 📋 Commandes de Lancement

### 1. Services Docker (PostgreSQL + Redis)

**Terminal 1:**
```bash
docker-compose -f docker-compose.dev.yml up postgres redis
```

### 2. Backend FastAPI

**Terminal 2 (PowerShell):**
```powershell
cd backend
$env:PYTHONPATH = $PWD
uvicorn src.api.ohada_api_server:app --host 0.0.0.0 --port 8000 --reload
```

**Ou avec le script:**
```powershell
cd backend
.\start.bat
```

### 3. Frontend Vite

**Terminal 3:**
```bash
cd frontend
npm run dev
```

## ⚙️ Configuration Backend (.env)

Le fichier `backend/.env` est chargé automatiquement:

```env
# Environnement
OHADA_ENV=test

# Base de données
DATABASE_URL=postgresql://ohada_user:changeme_in_production@localhost:5434/ohada

# API Keys
OPENAI_API_KEY=votre_clé_ici
DEEPSEEK_API_KEY=votre_clé_ici

# JWT
JWT_SECRET_KEY=dev_secret_key_change_in_production
```

## 🔥 Hot Reload

### Backend
- Uvicorn surveille les changements de fichiers Python
- Redémarrage automatique à chaque modification
- Flag: `--reload`

### Frontend
- Vite HMR (Hot Module Replacement)
- Rechargement instantané des composants modifiés
- Pas de rechargement complet de la page

## 🐛 Résolution de Problèmes

### Port 5175 occupé

Le port est configuré dans `frontend/vite.config.ts`:
```typescript
server: {
  port: 5175,
  // ...
}
```

### Backend ne démarre pas

Vérifier:
1. `PYTHONPATH` est défini: `$env:PYTHONPATH = $PWD`
2. Le fichier `backend/.env` existe
3. PostgreSQL est démarré: `docker ps`

### Frontend ne trouve pas l'API

Vérifier que le backend tourne sur le port 8000:
```bash
curl http://localhost:8000/health
```

## 📝 Notes

### Changements récents (2025-11-02)
- ✅ Port frontend changé de 3000 à **5175** (éviter conflits)
- ✅ Fichier `.env` créé pour backend (chargement automatique)
- ✅ Script `start.bat` ajouté pour Windows
- ✅ Hot reload activé sur backend et frontend
- ❌ Docker pour le code abandonné (trop lent, problèmes pywin32)

### Pourquoi pas Docker pour tout?
- Builds très longs (10+ minutes)
- Problèmes avec packages Windows (pywin32)
- Hot reload plus compliqué
- Développement local plus rapide et simple

## 🚀 Workflow Recommandé

1. **Démarrer services**: Docker Compose (PostgreSQL + Redis)
2. **Lancer backend**: Terminal dans `backend/`, uvicorn avec --reload
3. **Lancer frontend**: Terminal dans `frontend/`, npm run dev
4. **Coder**: Les changements se reflètent automatiquement
5. **Tester**: http://localhost:5175

## 🔄 Redémarrage Complet

Si besoin de tout redémarrer:

```bash
# Arrêter tout
taskkill /F /IM node.exe 2>nul
taskkill /F /IM python.exe 2>nul
docker-compose -f docker-compose.dev.yml down

# Relancer
docker-compose -f docker-compose.dev.yml up -d postgres redis
cd backend && .\start.bat
cd frontend && npm run dev
```

---

**Dernière mise à jour**: 2025-11-02
