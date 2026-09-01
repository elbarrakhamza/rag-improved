import hashlib
import json
import redis
from typing import Optional, Any
from app.core.config import settings
from loguru import logger


class EmbeddingCache:
    """Cache pour les embeddings et les réponses des questions fréquentes"""
    
    def __init__(self):
        self._client = None
        self._enabled = settings.enable_cache
        
        if self._enabled:
            try:
                self._client = redis.Redis(
                    host=settings.redis_host,
                    port=settings.redis_port,
                    db=settings.redis_db,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2
                )
                self._client.ping()
                logger.info(f"Redis cache connecté sur {settings.redis_host}:{settings.redis_port}")
            except Exception as e:
                logger.warning(f"Impossible de se connecter à Redis: {e}. Cache désactivé.")
                self._enabled = False
                self._client = None
    
    def _get_embedding_key(self, question: str) -> str:
        return f"embed:{hashlib.md5(question.encode('utf-8')).hexdigest()}"
    
    def _get_answer_key(self, question: str, role: str = "public") -> str:
        """
        Clé de cache avec le rôle pour isoler les réponses par permission.
        Les réponses sont mises en cache avec le rôle le plus restrictif.
        """
        # Si la réponse provient de documents publics, elle est accessible à tous
        # Mais on ne sait pas à l'avance si la réponse est publique ou non
        # On utilise donc un cache séparé par rôle, mais avec un mécanisme de fallback
        return f"answer:{hashlib.md5(question.encode('utf-8')).hexdigest()}:{role}"
    
    def _get_public_answer_key(self, question: str) -> str:
        """Clé pour le cache public (accessible à tous)"""
        return f"answer:{hashlib.md5(question.encode('utf-8')).hexdigest()}:public"
    
    def get_embedding(self, question: str) -> Optional[list]:
        if not self._enabled or not self._client:
            return None
        
        try:
            key = self._get_embedding_key(question)
            cached = self._client.get(key)
            if cached:
                logger.debug(f"Cache hit pour l'embedding: {question[:50]}...")
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Erreur de lecture du cache: {e}")
        return None
    
    def set_embedding(self, question: str, embedding: list) -> bool:
        if not self._enabled or not self._client:
            return False
        
        try:
            key = self._get_embedding_key(question)
            self._client.setex(
                key,
                settings.cache_ttl_seconds,
                json.dumps(embedding)
            )
            return True
        except Exception as e:
            logger.warning(f"Erreur d'écriture du cache: {e}")
            return False
    
    def get_answer(self, question: str, role: str = "public", is_public_doc: bool = False) -> Optional[dict]:
        """
        Récupère une réponse en cache.
        - Si is_public_doc = True: cherche d'abord dans le cache public, puis dans le cache du rôle
        - Si is_public_doc = False: cherche seulement dans le cache du rôle
        """
        if not self._enabled or not self._client:
            return None
        
        try:
            # 1. Si le document est public, chercher d'abord dans le cache public
            if is_public_doc:
                public_key = self._get_public_answer_key(question)
                cached = self._client.get(public_key)
                if cached:
                    data = json.loads(cached)
                    data["cached"] = True
                    data["cache_type"] = "public"
                    logger.debug(f"Cache hit public pour: {question[:50]}...")
                    return data
            
            # 2. Chercher dans le cache du rôle spécifique
            key = self._get_answer_key(question, role)
            cached = self._client.get(key)
            if cached:
                data = json.loads(cached)
                data["cached"] = True
                data["cache_type"] = "role"
                logger.debug(f"Cache hit pour le rôle {role}: {question[:50]}...")
                return data
                
        except Exception as e:
            logger.warning(f"Erreur de lecture du cache réponse: {e}")
        return None
    
    def set_answer(self, question: str, answer: str, token_usage: int, 
                   role: str = "public", sources: list = None, 
                   is_public_doc: bool = False) -> bool:
        """
        Cache une réponse.
        - Si is_public_doc = True: stocke dans le cache public ET dans le cache du rôle
        - Si is_public_doc = False: stocke seulement dans le cache du rôle
        """
        if not self._enabled or not self._client:
            return False
        
        try:
            data = {
                "answer": answer,
                "token_usage": token_usage,
                "sources": sources or []
            }
            
            # 1. Stocker dans le cache du rôle
            key = self._get_answer_key(question, role)
            self._client.setex(
                key,
                settings.cache_ttl_seconds,
                json.dumps(data)
            )
            
            # 2. Si c'est un document public, stocker aussi dans le cache public
            if is_public_doc:
                public_key = self._get_public_answer_key(question)
                self._client.setex(
                    public_key,
                    settings.cache_ttl_seconds,
                    json.dumps(data)
                )
                logger.debug(f"Réponse mise en cache public et rôle {role}: {question[:50]}...")
            else:
                logger.debug(f"Réponse mise en cache pour le rôle {role}: {question[:50]}...")
            
            return True
        except Exception as e:
            logger.warning(f"Erreur d'écriture du cache réponse: {e}")
            return False
    
    def clear_cache(self) -> bool:
        if not self._enabled or not self._client:
            return False
        
        try:
            keys = self._client.keys("*")
            if keys:
                self._client.delete(*keys)
            logger.info(f"Cache vidé: {len(keys)} clés supprimées")
            return True
        except Exception as e:
            logger.warning(f"Erreur lors du vidage du cache: {e}")
            return False
    
    def get_stats(self) -> dict:
        if not self._enabled or not self._client:
            return {"enabled": False}
        
        try:
            embed_keys = self._client.keys("embed:*")
            answer_keys = self._client.keys("answer:*")
            public_keys = self._client.keys("answer:*:public")
            return {
                "enabled": True,
                "cached_embeddings": len(embed_keys),
                "cached_answers": len(answer_keys),
                "cached_public_answers": len(public_keys),
                "total_cached": len(embed_keys) + len(answer_keys),
                "ttl_seconds": settings.cache_ttl_seconds
            }
        except Exception as e:
            return {"enabled": False, "error": str(e)}


# Instance globale
embedding_cache = EmbeddingCache()