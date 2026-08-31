import hashlib
import json
import redis
from typing import Optional, Any
from app.core.config import settings
from loguru import logger


class EmbeddingCache:
    """Cache pour les embeddings des questions fréquentes"""
    
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
    
    def _get_answer_key(self, question: str) -> str:
        return f"answer:{hashlib.md5(question.encode('utf-8')).hexdigest()}"
    
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
    
    def get_answer(self, question: str) -> Optional[dict]:
        """Récupère une réponse en cache"""
        if not self._enabled or not self._client:
            return None
        
        try:
            key = self._get_answer_key(question)
            cached = self._client.get(key)
            if cached:
                logger.debug(f"Cache hit pour la réponse: {question[:50]}...")
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Erreur de lecture du cache réponse: {e}")
        return None
    
    def set_answer(self, question: str, answer: str, token_usage: int) -> bool:
        """Cache une réponse"""
        if not self._enabled or not self._client:
            return False
        
        try:
            key = self._get_answer_key(question)
            data = {
                "answer": answer,
                "token_usage": token_usage
            }
            self._client.setex(
                key,
                settings.cache_ttl_seconds,
                json.dumps(data)
            )
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
            return {
                "enabled": True,
                "cached_embeddings": len(embed_keys),
                "cached_answers": len(answer_keys),
                "total_cached": len(embed_keys) + len(answer_keys),
                "ttl_seconds": settings.cache_ttl_seconds
            }
        except Exception as e:
            return {"enabled": False, "error": str(e)}


# Instance globale
embedding_cache = EmbeddingCache()