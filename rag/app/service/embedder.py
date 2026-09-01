import requests
import json
import math
from typing import List, Union, Optional
from app.core.config import settings
from app.service.cache import embedding_cache
from loguru import logger


class NvidiaAPIEmbedder:
    """
    Embedder utilisant l'API NVIDIA NIM
    - Récupère 2048 dimensions, garde les 1024 premières
    - Normalise les vecteurs pour la similarité cosinus
    """
    
    def __init__(self):
        self.api_key = settings.nvidia_api_key
        self.api_url = settings.nvidia_api_url
        self.model = settings.embedding_model
        self.dim = 1024  # Dimension finale (1024 premières dimensions)
        self.full_dim = 2048  # Dimension complète du modèle
        
        if not self.api_key:
            raise ValueError("NVIDIA_API_KEY is required")
        
        logger.info(f"✅ NVIDIA API Embedder initialized with model: {self.model}")
        logger.info(f"📊 Using first 1024 dimensions (full: {self.full_dim})")
    
    def load(self):
        logger.info("✅ NVIDIA API ready (no local model)")
        pass

    def embed(self, text: Union[str, List[str]], use_cache: bool = True) -> Union[List[float], List[List[float]]]:
        """Embed un texte via l'API NVIDIA, retourne 1024 dimensions normalisées"""
        if use_cache and isinstance(text, str):
            cached = embedding_cache.get_embedding(text)
            if cached is not None:
                return cached
        
        is_single = isinstance(text, str)
        texts = [text] if is_single else text
        
        try:
            full_embeddings = self._call_nvidia_api(texts)
            
            # Prendre les 1024 premières dimensions et normaliser
            embeddings = []
            for emb in full_embeddings:
                sliced = emb[:1024]
                # Normalisation L2
                norm = math.sqrt(sum(x * x for x in sliced))
                if norm > 0:
                    sliced = [x / norm for x in sliced]
                embeddings.append(sliced)
            
        except Exception as e:
            logger.error(f"❌ NVIDIA API embedding failed: {e}")
            raise
        
        result = embeddings[0] if is_single else embeddings
        if use_cache and is_single:
            embedding_cache.set_embedding(text, result)
        
        return result
    
    def _call_nvidia_api(self, texts: List[str]) -> List[List[float]]:
        """Appelle l'API NVIDIA NIM pour générer les embeddings complets (2048)"""
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
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                embeddings = [item["embedding"] for item in data.get("data", [])]
                logger.debug(f"✅ Generated {len(embeddings)} embeddings (2048 dims)")
                return embeddings
            else:
                raise Exception(f"API error: {response.status_code} - {response.text}")
                
        except requests.exceptions.Timeout:
            raise Exception("NVIDIA API timeout")
        except requests.exceptions.RequestException as e:
            raise Exception(f"NVIDIA API request failed: {e}")
    
    def get_embedding_dim(self) -> int:
        return self.dim


Embedder = NvidiaAPIEmbedder