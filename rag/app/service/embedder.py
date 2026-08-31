import requests
import json
from typing import List, Union, Optional
from app.core.config import settings
from app.service.cache import embedding_cache
from loguru import logger


class NvidiaAPIEmbedder:
    """
    Embedder utilisant UNIQUEMENT l'API NVIDIA NIM
    - Aucun modèle local
    - Aucune dépendance lourde (sentence-transformers, torch, FlagEmbedding)
    """
    
    def __init__(self):
        self.api_key = settings.nvidia_api_key
        self.api_url = settings.nvidia_api_url
        self.model = settings.embedding_model
        self.dim = settings.embedding_dim
        
        if not self.api_key:
            raise ValueError(
                "NVIDIA_API_KEY is required. Please set it in your .env file.\n"
                "Get your API key from: https://build.nvidia.com/nvidia/nemotron-3-embed-1b"
            )
        
        logger.info(f"✅ NVIDIA API Embedder initialized with model: {self.model}")
    
    def load(self):
        """Rien à charger - tout est via API"""
        logger.info("✅ NVIDIA API ready (no local model)")
        pass

    def embed(self, text: Union[str, List[str]], use_cache: bool = True) -> Union[List[float], List[List[float]]]:
        """
        Embed un texte ou une liste de textes via l'API NVIDIA
        """
        # Gérer le cache pour les requêtes uniques
        if use_cache and isinstance(text, str):
            cached = embedding_cache.get_embedding(text)
            if cached is not None:
                return cached
        
        # Déterminer si c'est une liste ou un texte unique
        is_single = isinstance(text, str)
        texts = [text] if is_single else text
        
        # Appel à l'API NVIDIA
        try:
            embeddings = self._call_nvidia_api(texts)
        except Exception as e:
            logger.error(f"❌ NVIDIA API embedding failed: {e}")
            raise
        
        # Mettre en cache si c'est une requête unique
        result = embeddings[0] if is_single else embeddings
        if use_cache and is_single:
            embedding_cache.set_embedding(text, result)
        
        return result
    
    def _call_nvidia_api(self, texts: List[str]) -> List[List[float]]:
        """
        Appelle l'API NVIDIA NIM pour générer les embeddings
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        payload = {
            "input": texts,
            "model": self.model,
            "encoding_format": "float"
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60  # Timeout plus long pour les batchs
            )
            
            if response.status_code == 200:
                data = response.json()
                # Extraire les embeddings dans l'ordre
                embeddings = [item["embedding"] for item in data.get("data", [])]
                
                if len(embeddings) != len(texts):
                    logger.warning(
                        f"API returned {len(embeddings)} embeddings for {len(texts)} texts"
                    )
                
                logger.debug(f"✅ Generated {len(embeddings)} embeddings via NVIDIA API")
                return embeddings
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"❌ NVIDIA API error: {error_msg}")
                raise Exception(f"NVIDIA API error: {error_msg}")
                
        except requests.exceptions.Timeout:
            logger.error("❌ NVIDIA API timeout after 60 seconds")
            raise Exception("NVIDIA API timeout")
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ NVIDIA API request failed: {e}")
            raise
    
    def get_embedding_dim(self) -> int:
        """Retourne la dimension des embeddings"""
        return self.dim


# Alias pour compatibilité avec le code existant
Embedder = NvidiaAPIEmbedder