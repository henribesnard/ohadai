Recommandations pour l'optimisation de l'API OHADA Expert-Comptable pour le traitement simultané de requêtes
Basé sur la structure actuelle du projet, voici mes recommandations pour permettre le traitement simultané de plusieurs demandes sans écrire de code spécifique.
Fichiers à modifier

src/api/ohada_api_server.py

Modifier la section de démarrage du serveur pour utiliser plusieurs workers
Ajuster les configurations de timeout pour les requêtes
Implémenter un mécanisme de gestion des files d'attente pour les requêtes


src/db/db_manager.py

Mettre à jour la gestion des connexions pour utiliser un pool de connexions
Optimiser les opérations de base de données pour les accès concurrents


src/vector_db/ohada_vector_db_structure.py

Améliorer la gestion du singleton OhadaEmbedder pour une utilisation multiprocess sécurisée
Optimiser le chargement des modèles d'embedding pour une meilleure réutilisation


src/utils/ohada_cache.py

Adapter le cache pour supporter un accès concurrent
Mettre en place un mécanisme de cache distribué


src/retrieval/ohada_hybrid_retriever.py

Optimiser les recherches parallèles pour qu'elles fonctionnent efficacement dans un environnement multiprocessus



Fichiers à ajouter

gunicorn_config.py

Fichier de configuration pour Gunicorn contenant les paramètres optimaux pour la gestion des workers


src/utils/connection_pool.py

Implémentation d'un pool de connexions pour la base de données


src/utils/rate_limiter.py

Mise en place d'un limiteur de taux de requêtes


src/config/concurrency_config.yaml

Configuration des paramètres de concurrence (nombre de workers, taille des pools, etc.)



Librairies et frameworks à installer

Gunicorn

Serveur WSGI de production pour gérer plusieurs processus workers
Installation: pip install gunicorn


Uvicorn avec support Gunicorn

S'assurer que Uvicorn est installé avec support pour Gunicorn
Installation: pip install uvicorn[standard]


Redis (optionnel mais recommandé)

Pour un cache distribué entre les workers
Installation: pip install redis
Nécessite également l'installation du serveur Redis


Slowapi

Pour implémenter le rate limiting dans FastAPI
Installation: pip install slowapi


SQLAlchemy (optionnel)

Pour une gestion plus robuste des connexions à la base de données
Installation: pip install sqlalchemy


Psycopg2 ou autre (optionnel)

Si vous décidez de migrer de SQLite vers une base de données plus robuste comme PostgreSQL
Installation: pip install psycopg2-binary



Documentation des modifications à apporter
Configuration du serveur
Le point le plus important est de configurer Uvicorn/Gunicorn correctement:

Pour des tests en développement, configurez Uvicorn pour utiliser des threads:
Copieruvicorn src.api.ohada_api_server:app --host 0.0.0.0 --port 8000 --workers 4

Pour la production, utilisez Gunicorn:
Copiergunicorn -c gunicorn_config.py src.api.ohada_api_server:app


Base de données
SQLite n'est pas idéal pour les accès concurrents multiples. Vous avez deux options:

Implémenter un mécanisme de verrouillage plus sophistiqué pour SQLite
Migrer vers une base de données plus robuste comme PostgreSQL ou MySQL

Gestion des ressources partagées
Assurez-vous que les ressources partagées (comme les modèles d'embedding) sont:

Initialisées une seule fois par worker
Correctement libérées lorsqu'elles ne sont plus nécessaires
Mises en cache de manière efficace pour éviter les rechargements

Surveillance et logging
Mettez en place un système de surveillance pour:

Suivre l'utilisation des ressources (CPU, mémoire)
Surveiller les temps de réponse des requêtes
Détecter et résoudre les goulots d'étranglement
Configurer des alertes en cas de problèmes

Ces modifications vous permettront de gérer efficacement les requêtes simultanées sans compromettre les performances ou la stabilité du système.