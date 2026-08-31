from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Postgres
    postgres_host: str
    postgres_port: int = 5432
    postgres_db: str
    postgres_user: str
    postgres_password: str
    
    # LLM
    google_api_key: str
    groq_api_key: str

    # Security
    api_key: str
    admin_api_key: str

    # NVIDIA API pour les embeddings
    nvidia_api_key: str  # RENDU OBLIGATOIRE
    embedding_model: str = "nvidia/nemotron-3-embed-1b"
    embedding_dim: int = 1024
    nvidia_api_url: str = "https://integrate.api.nvidia.com/v1/embeddings"
    
    max_tokens: int = 512
    top_k: int = 7
    min_similarity: float = 0.7
    healthcheck_internet_url: str = "https://www.google.com/generate_204"
    healthcheck_timeout_seconds: float = 3.0

    # Cache Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    cache_ttl_seconds: int = 3600
    enable_cache: bool = True

    # Smart PDF Processing
    enable_smart_pdf: bool = True
    enable_vision_llm: bool = True
    ocr_lang: str = "fra+ara"

    # Feedback
    enable_feedback: bool = True
    feedback_min_entries_for_reranking: int = 10

    class Config:
        env_file = "../.env"

settings = Settings()