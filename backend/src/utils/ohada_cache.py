"""
Module de gestion du cache pour le système OHADA Expert-Comptable.
Fournit des mécanismes de cache pour les embeddings, documents et autres données.
"""

import os
import pickle
import logging
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, TypeVar, Generic, Callable, Iterator

# Configuration du logging
logger = logging.getLogger("ohada_cache")

T = TypeVar('T')

class LRUCache(Generic[T]):
    """Cache LRU (Least Recently Used) générique"""
    
    def __init__(self, max_size: int = 100):
        """
        Initialise un cache LRU
        
        Args:
            max_size: Taille maximale du cache
        """
        self.cache = {}
        self.max_size = max_size
        self.access_order = []
    
    def get(self, key: Any) -> Optional[T]:
        """
        Récupère une valeur du cache
        
        Args:
            key: Clé à récupérer
            
        Returns:
            Valeur associée à la clé ou None si non trouvée
        """
        if key in self.cache:
            # Mettre à jour l'ordre d'accès
            self.access_order.remove(key)
            self.access_order.append(key)
            return self.cache[key]
        return None
    
    def put(self, key: Any, value: T) -> None:
        """
        Ajoute ou met à jour une valeur dans le cache
        
        Args:
            key: Clé à ajouter/mettre à jour
            value: Valeur à associer à la clé
        """
        if key in self.cache:
            # Mettre à jour la valeur et l'ordre d'accès
            self.cache[key] = value
            self.access_order.remove(key)
            self.access_order.append(key)
        else:
            # Ajouter nouvelle entrée
            if len(self.cache) >= self.max_size:
                # Supprimer l'entrée la moins récemment utilisée
                oldest_key = self.access_order.pop(0)
                del self.cache[oldest_key]
            
            self.cache[key] = value
            self.access_order.append(key)
    
    def clear(self) -> None:
        """Vide le cache"""
        self.cache.clear()
        self.access_order.clear()
    
    def __contains__(self, key: Any) -> bool:
        """Vérifie si une clé est dans le cache"""
        return key in self.cache
    
    def __len__(self) -> int:
        """Retourne la taille du cache"""
        return len(self.cache)
    
    def __iter__(self) -> Iterator[Any]:
        """Retourne un itérateur sur les clés du cache"""
        return iter(self.cache)
    
    def items(self):
        """Retourne les paires clé-valeur du cache"""
        return self.cache.items()
    
    def keys(self):
        """Retourne les clés du cache"""
        return self.cache.keys()
    
    def values(self):
        """Retourne les valeurs du cache"""
        return self.cache.values()

class DiskCache:
    """Cache persistant sur disque"""
    
    def __init__(self, cache_dir: str, prefix: str = ""):
        """
        Initialise un cache sur disque
        
        Args:
            cache_dir: Répertoire pour le cache
            prefix: Préfixe pour les fichiers de cache
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.prefix = prefix
        self._keys_cache = None
    
    def get_path(self, key: str) -> Path:
        """
        Obtient le chemin du fichier de cache pour une clé
        
        Args:
            key: Clé à convertir en chemin
            
        Returns:
            Chemin complet du fichier de cache
        """
        # Hasher la clé pour éviter les problèmes de caractères spéciaux
        import hashlib
        hashed_key = hashlib.md5(str(key).encode()).hexdigest()
        return self.cache_dir / f"{self.prefix}_{hashed_key}.cache"
    
    def get(self, key: str, max_age: int = None) -> Optional[Any]:
        """
        Récupère une valeur du cache
        
        Args:
            key: Clé à récupérer
            max_age: Âge maximum en secondes (None pour pas de limite)
            
        Returns:
            Valeur associée à la clé ou None si non trouvée ou expirée
        """
        path = self.get_path(key)
        if not path.exists():
            return None
        
        # Vérifier l'âge du fichier si demandé
        if max_age is not None:
            file_age = time.time() - path.stat().st_mtime
            if file_age > max_age:
                logger.info(f"Cache expiré pour {key} (âge: {file_age:.1f}s)")
                return None
        
        try:
            with open(path, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            logger.error(f"Erreur lors de la lecture du cache pour {key}: {e}")
            return None
    
    def put(self, key: str, value: Any) -> None:
        """
        Ajoute ou met à jour une valeur dans le cache
        
        Args:
            key: Clé à ajouter/mettre à jour
            value: Valeur à associer à la clé
        """
        path = self.get_path(key)
        try:
            with open(path, 'wb') as f:
                pickle.dump(value, f)
            # Réinitialiser le cache des clés
            self._keys_cache = None
        except Exception as e:
            logger.error(f"Erreur lors de l'écriture du cache pour {key}: {e}")
    
    def keys(self) -> List[str]:
        """
        Récupère toutes les clés du cache
        
        Returns:
            Liste des clés
        """
        if self._keys_cache is not None:
            return self._keys_cache
        
        keys = []
        prefix_len = len(self.prefix) + 1  # +1 pour le underscore
        suffix_len = len(".cache")
        
        for path in self.cache_dir.glob(f"{self.prefix}_*.cache"):
            # Extraire la partie hashée du nom de fichier
            hashed_key = path.name[prefix_len:-suffix_len]
            keys.append(hashed_key)
        
        self._keys_cache = keys
        return keys
    
    def __contains__(self, key: str) -> bool:
        """Vérifie si une clé est dans le cache"""
        return self.get_path(key).exists()

class EmbeddingCache:
    """Cache spécialisé pour les embeddings"""
    
    def __init__(self, memory_cache_size: int = 100, disk_cache_dir: str = "./data/embedding_cache"):
        """
        Initialise un cache d'embeddings
        
        Args:
            memory_cache_size: Taille maximale du cache en mémoire
            disk_cache_dir: Répertoire pour le cache sur disque
        """
        self.memory_cache = LRUCache[List[float]](max_size=memory_cache_size)
        self.disk_cache = DiskCache(disk_cache_dir, prefix="embedding")
    
    def get(self, text: str) -> Optional[List[float]]:
        """
        Récupère un embedding du cache
        
        Args:
            text: Texte dont l'embedding est recherché
            
        Returns:
            Embedding ou None si non trouvé
        """
        # Utiliser un hash du texte comme clé
        text_hash = hash(text)
        
        # D'abord chercher en mémoire
        embedding = self.memory_cache.get(text_hash)
        if embedding is not None:
            return embedding
        
        # Sinon chercher sur disque
        embedding = self.disk_cache.get(text_hash)
        if embedding is not None:
            # Mettre aussi en cache mémoire
            self.memory_cache.put(text_hash, embedding)
            return embedding
        
        return None
    
    def put(self, text: str, embedding: List[float]) -> None:
        """
        Ajoute ou met à jour un embedding dans le cache
        
        Args:
            text: Texte associé à l'embedding
            embedding: Vecteur d'embedding
        """
        text_hash = hash(text)
        
        # Mettre en cache mémoire
        self.memory_cache.put(text_hash, embedding)
        
        # Mettre en cache disque
        self.disk_cache.put(text_hash, embedding)
    
    # Méthodes pour rendre la classe compatible avec l'API de dictionnaire
    def __getitem__(self, key: Any) -> List[float]:
        """Permet d'accéder aux éléments comme un dictionnaire"""
        result = self.memory_cache.get(key)
        if result is None:
            result = self.disk_cache.get(key)
            if result is None:
                raise KeyError(key)
            self.memory_cache.put(key, result)
        return result
    
    def __setitem__(self, key: Any, value: List[float]) -> None:
        """Permet de définir des éléments comme un dictionnaire"""
        self.memory_cache.put(key, value)
        self.disk_cache.put(key, value)
    
    def __contains__(self, key: Any) -> bool:
        """Permet d'utiliser 'in' pour vérifier si une clé existe"""
        return self.memory_cache.get(key) is not None or self.disk_cache.get(key) is not None
    
    def __iter__(self) -> Iterator[Any]:
        """Rend l'objet itérable en retournant un itérateur sur les clés en mémoire"""
        return iter(self.memory_cache.cache)
    
    def __len__(self) -> int:
        """Retourne la taille du cache en mémoire"""
        return len(self.memory_cache)
    
    def clear(self) -> None:
        """Vide le cache en mémoire"""
        self.memory_cache.clear()

def memoize(max_size: int = 100):
    """
    Décorateur pour mettre en cache les résultats d'une fonction
    
    Args:
        max_size: Taille maximale du cache
        
    Returns:
        Fonction décorée
    """
    def decorator(func):
        cache = LRUCache(max_size=max_size)
        
        def wrapper(*args, **kwargs):
            # Créer une clé de cache combinant tous les arguments
            key = (args, frozenset(kwargs.items()))
            result = cache.get(key)
            if result is None:
                result = func(*args, **kwargs)
                cache.put(key, result)
            return result
        
        return wrapper
    
    return decorator