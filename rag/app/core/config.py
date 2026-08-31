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
    admin_api_key: str  # NOUVEAU: clé admin séparée

    # Model
    embedding_model: str = "BAAI/bge-m3"
    max_tokens: int = 512
    top_k: int = 7
    min_similarity: float = 0.7
    mock_embedding_dim: int = 1024
    skip_embedder_load: bool = False
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
    nvidia_api_key: Optional[str] = None

    # Feedback
    enable_feedback: bool = True
    feedback_min_entries_for_reranking: int = 10

    class Config:
        env_file = "../.env"

settings = Settings()