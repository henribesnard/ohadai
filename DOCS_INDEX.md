# Index de la Documentation

Guide pour naviguer dans la documentation du projet OHAD'AI.

## 📖 Documentation Principale

### Pour Démarrer

| Document | Objectif | Audience |
|----------|----------|----------|
| **README.md** | Vue d'ensemble du projet, installation, architecture | Tout le monde |
| **DEV_SETUP.md** | Configuration développement local, commandes de lancement | Développeurs |
| **CHANGELOG.md** | Historique des changements récents | Développeurs |

### Architecture et Technique

| Document | Contenu | Statut |
|----------|---------|--------|
| **BACKEND_IMPROVEMENTS.md** | Architecture backend détaillée, design patterns | ✅ À jour |
| **FRONTEND_ROADMAP.md** | Roadmap et améliorations frontend prévues | ✅ À jour |
| **MIGRATION_GUIDE.md** | Guide de migration des données OHADA | ✅ À jour |
| **DOCUMENT_MANAGEMENT_SUMMARY.md** | Système de gestion documentaire | ✅ À jour |

### Analyses et Comparaisons

| Document | Contenu | Statut |
|----------|---------|--------|
| **EMBEDDING_MODELS_COMPARISON.md** | Comparaison des modèles d'embedding | ✅ À jour |
| **SOURCES_CITATION_COMPARISON.md** | Comparaison systèmes de citation | ✅ À jour |
| **VECTORISATION_SUMMARY.md** | Résumé du système de vectorisation | ✅ À jour |
| **COLLECTION_HIERARCHY_GUIDE.md** | Guide de la hiérarchie des collections | ✅ À jour |
| **MIGRATION_SUMMARY.md** | Résumé des migrations effectuées | ✅ À jour |

## ⚠️ Documentation Obsolète

### Fichiers Supprimés

| Document | Raison | Remplacé par |
|----------|--------|--------------|
| ~~QUICK_START.md~~ | Utilisait Docker pour tout le code | README.md + DEV_SETUP.md |
| ~~DOCKER_SETUP_GUIDE.md~~ | Configuration Docker complète non utilisée en dev | DEV_SETUP.md |

**Note**: Ces fichiers ont été **supprimés** le 2025-11-02 car ils contenaient des instructions obsolètes.

## 🎯 Guide de Navigation

### Je veux...

#### Démarrer le projet pour la première fois
→ Lire **README.md** puis **DEV_SETUP.md**

#### Comprendre l'architecture backend
→ Lire **BACKEND_IMPROVEMENTS.md**

#### Voir ce qui a changé récemment
→ Lire **CHANGELOG.md**

#### Migrer des données OHADA
→ Lire **MIGRATION_GUIDE.md** et **DOCUMENT_MANAGEMENT_SUMMARY.md**

#### Choisir un modèle d'embedding
→ Lire **EMBEDDING_MODELS_COMPARISON.md**

#### Configurer les citations de sources
→ Lire **SOURCES_CITATION_COMPARISON.md**

#### Comprendre la vectorisation
→ Lire **VECTORISATION_SUMMARY.md**

#### Organiser les collections ChromaDB
→ Lire **COLLECTION_HIERARCHY_GUIDE.md**

## 📂 Organisation des Fichiers

```
ohada/
├── README.md                              # 👈 Commencer ici
├── DEV_SETUP.md                           # Configuration développement
├── CHANGELOG.md                           # Changements récents
├── DOCS_INDEX.md                          # Ce fichier
│
├── BACKEND_IMPROVEMENTS.md                # Architecture backend
├── FRONTEND_ROADMAP.md                    # Roadmap frontend
├── MIGRATION_GUIDE.md                     # Migration de données
├── DOCUMENT_MANAGEMENT_SUMMARY.md         # Gestion documentaire
│
├── EMBEDDING_MODELS_COMPARISON.md         # Comparaison embeddings
├── SOURCES_CITATION_COMPARISON.md         # Comparaison citations
├── VECTORISATION_SUMMARY.md               # Vectorisation
├── COLLECTION_HIERARCHY_GUIDE.md          # Hiérarchie collections
├── MIGRATION_SUMMARY.md                   # Résumé migrations
│
```

## 🔄 Mise à Jour de la Documentation

### Qui met à jour quoi?

**README.md** - À mettre à jour lors de:
- Changements d'architecture majeurs
- Nouveaux prérequis
- Changements de structure du projet

**DEV_SETUP.md** - À mettre à jour lors de:
- Changements de ports
- Nouveaux fichiers de configuration
- Modifications du workflow de développement

**CHANGELOG.md** - À mettre à jour à chaque:
- Session de développement
- Modification de configuration
- Ajout/suppression de fonctionnalités

### Cycle de Vie d'un Document

1. **Création**: Nouveau document pour nouvelle fonctionnalité/système
2. **Maintenance**: Mises à jour régulières
3. **Stabilité**: Document complet et stable
4. **Obsolescence**: Marqué comme obsolète, conservé pour référence
5. **Archive**: (Futur) Déplacement vers dossier archive/

## 📝 Standards de Documentation

### Format Markdown

Tous les documents utilisent:
- Headers `#` pour structure
- Tables pour comparaisons
- Code blocks avec syntaxe highlighting
- Emojis pour navigation visuelle

### Structure Type

```markdown
# Titre Principal

Brève description

## Section 1
Contenu...

## Section 2
Contenu...

## Référence/Liens
Liens vers docs connexes

---
Dernière mise à jour: DATE
```

---

**Version**: 1.0
**Dernière mise à jour**: 2025-11-02
