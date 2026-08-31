import asyncio
from contextlib import asynccontextmanager
from urllib.error import URLError
from urllib.request import urlopen

from app.api.limiter import limiter
from app.api.routes.query import router as query_router
from app.api.routes.admin import router as admin_router
from app.api.routes.feedback import router as feedback_router
from app.core.config import settings
from app.database.postgres_connection import get_pool
from app.service.embedder import Embedder
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import os


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("API Starting...")
    app.state.pool = await get_pool()
    logger.info("DB Pool initiated")
    
    # Initialiser les tables si nécessaire
    await init_database(app.state.pool)
    
    app.state.embedder = Embedder()
    app.state.embedder.load()
    logger.info("Embedding model loaded")
    
    yield
    
    await app.state.pool.close()
    del app.state.embedder
    print("API Stopping...")


async def init_database(pool):
    """Initialise les tables si elles n'existent pas"""
    try:
        schema_path = os.path.join(os.path.dirname(__file__), "database", "schemas.sql")
        with open(schema_path, "r") as f:
            schema_sql = f.read()
        
        async with pool.acquire() as conn:
            # Exécuter le script SQL
            for statement in schema_sql.split(";"):
                if statement.strip():
                    await conn.execute(statement)
        
        logger.info("Database schema initialized")
    except Exception as e:
        logger.warning(f"Database initialization warning: {e}")


app = FastAPI(
    lifespan=lifespan,
    title="Maintenance Manual RAG API",
    description="RAG API for elevator maintenance manual with Smart PDF Processing, Cache, Feedback & Roles",
    version="2.0.0"
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, ex: Exception):
    logger.error(f"Unhandled error: {ex}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Adding access rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Adding middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://stage.enset.top",
        "https://stage.enset.top",
        "https://siop.stage.enset.top",
        "https://rag-web.stage.enset.top",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Adding routers
app.include_router(query_router)
app.include_router(admin_router)
app.include_router(feedback_router)


async def _check_database(app: FastAPI):
    checks = {}
    async with app.state.pool.acquire() as connection:
        await connection.fetchval("SELECT 1")
        checks["postgres_connection"] = {"ok": True}

        vector_exists = await connection.fetchval(
            "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')"
        )
        if not vector_exists:
            raise RuntimeError("pgvector extension is not installed.")
        checks["pgvector_extension"] = {"ok": True}

        documents_table_exists = await connection.fetchval(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'documents'
            )
            """
        )
        checks["documents_table"] = {"ok": documents_table_exists}

    return checks


async def _check_internet_connectivity():
    def _probe():
        with urlopen(
            settings.healthcheck_internet_url,
            timeout=settings.healthcheck_timeout_seconds,
        ) as response:
            status = getattr(response, "status", 200)
            if status >= 400:
                raise RuntimeError(f"Internet check returned HTTP {status}.")

    try:
        await asyncio.to_thread(_probe)
        return {"ok": True}
    except (URLError, TimeoutError, OSError) as exc:
        return {"ok": False, "error": str(exc)}


@app.get("/health")
@limiter.limit("10/minute")
async def health(request: Request):
    health_checks = {}
    global_status = "ok"
    http_status = 200

    internet_check = await _check_internet_connectivity()
    health_checks["internet_connectivity"] = internet_check
    if not internet_check["ok"]:
        global_status = "degraded"
        http_status = 503

    try:
        health_checks.update(await _check_database(request.app))
    except Exception as exc:
        health_checks["database"] = {"ok": False, "error": str(exc)}
        global_status = "degraded"
        http_status = 503

    embedder = getattr(request.app.state, "embedder", None)
    embedder_ready = embedder is not None and getattr(embedder, "model", None) is not None
    health_checks["embedder_model_loaded"] = {"ok": embedder_ready}
    if not embedder_ready:
        global_status = "degraded"
        http_status = 503

    # Vérifier Redis
    from app.service.cache import embedding_cache
    cache_stats = embedding_cache.get_stats()
    health_checks["redis_cache"] = {"ok": cache_stats.get("enabled", False)}
    if not cache_stats.get("enabled", False):
        global_status = "degraded"
        http_status = 503

    return JSONResponse(
        status_code=http_status,
        content={
            "status": global_status,
            "checks": health_checks,
        },
    )