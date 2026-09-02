import asyncio
import uuid
import json
import shutil
from typing import List, Dict, Any
from pathlib import Path
from loguru import logger
from app.core.config import settings
import sys
import asyncpg

sys.path.append('/app/data')
from ingest_documents_pipeline import build_chunks, enrich_chunks_with_embeddings, save_chunks_to_json, print_chunk_summary, IngestionJob
from write_embeddings_to_postgres import get_postgres_connection, insert_chunks_with_embeddings

# Stockage des tâches en mémoire (pour compatibilité avec l'existant)
tasks = {}


async def start_ingestion_task(task_id: str, files: List[str], metadata: Dict[str, Any], mode: str):
    """
    Point d'entrée pour l'ingestion d'une tâche.
    - Mode 'auto' : tout enchaîné (chunks -> embedding -> insertion)
    - Mode 'manual' : génère les chunks et s'arrête, attend validation
    """
    try:
        # 1. Mise à jour statut : UPLOADED -> GENERATING_CHUNKS
        await update_task_status(task_id, "GENERATING_CHUNKS", message="Extraction des chunks en cours")

        # Génération des chunks
        chunks = await generate_chunks_for_task(files, metadata)

        # Sauvegarder les chunks dans la tâche
        await save_chunks_to_task(task_id, chunks)

        if mode == "auto":
            # Mode auto : enchaîner directement
            await update_task_status(task_id, "EMBEDDING_IN_PROGRESS", message="Génération des embeddings")
            await run_embedding_phase(task_id, chunks, metadata)
        else:
            # Mode manuel : attendre validation
            await update_task_status(task_id, "CHUNKS_GENERATED", message="Chunks générés, en attente de validation")

    except Exception as e:
        logger.error(f"Erreur lors de l'ingestion de la tâche {task_id}: {e}")
        await update_task_status(task_id, "FAILED", error=str(e))


async def generate_chunks_for_task(files: List[str], metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Génère les chunks à partir des fichiers (utilise le pipeline existant)."""
    all_chunks = []
    for file_path in files:
        # Créer un job
        job = IngestionJob(
            path=Path(file_path),
            metadata=metadata.copy()
        )
        job.metadata["language"] = "english"
        job.metadata["embedding_model"] = settings.embedding_model

        chunks = build_chunks(
            job=job,
            chunk_size=1000,
            chunk_overlap=150,
            language="english",
            embedding_model=settings.embedding_model,
            use_smart_pdf=metadata.get("use_smart_pdf", settings.enable_smart_pdf),
            use_vision_llm=metadata.get("use_vision_llm", settings.enable_vision_llm)
        )
        all_chunks.extend(chunks)
    return all_chunks


async def save_chunks_to_task(task_id: str, chunks: List[Dict[str, Any]]):
    """Met à jour la table ingestion_tasks avec les chunks."""
    pool = get_pool()  # À définir : fonction pour récupérer le pool depuis app.state
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE ingestion_tasks
            SET chunks = $1, updated_at = NOW()
            WHERE id = $2
            """,
            json.dumps(chunks),
            task_id
        )


async def run_embedding_phase(task_id: str, chunks: List[Dict[str, Any]], metadata: Dict[str, Any]):
    """Exécute l'étape d'embedding et d'insertion."""
    try:
        # Vérifier si l'utilisateur a choisi de skip l'embedding
        if metadata.get("skip_embedding", False):
            await update_task_status(task_id, "COMPLETED", message="Embedding skipped (test mode)")
            return

        # Générer les embeddings
        enrich_chunks_with_embeddings(
            chunks=chunks,
            embedding_model=settings.embedding_model,
            max_tokens=settings.max_tokens,
            batch_size=8,
            skip_embedding=False
        )

        # Insertion en base
        if not metadata.get("skip_db_insert", False):
            conn = get_postgres_connection()
            try:
                inserted = insert_chunks_with_embeddings(conn, chunks)
                logger.info(f"Inserted {inserted} chunks for task {task_id}")
            finally:
                conn.close()

        # Mise à jour statut final
        await update_task_status(task_id, "COMPLETED", message="Ingestion terminée avec succès")

        # Notification (placeholder)
        logger.info(f"Notification : tâche {task_id} terminée")

    except Exception as e:
        logger.error(f"Erreur lors de l'embedding pour la tâche {task_id}: {e}")
        await update_task_status(task_id, "FAILED", error=str(e))


async def update_task_status(task_id: str, status: str, error: str = None, message: str = None):
    """Met à jour le statut d'une tâche dans la base."""
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE ingestion_tasks
            SET status = $1, updated_at = NOW(), error_message = $2
            WHERE id = $3
            """,
            status,
            error,
            task_id
        )
    # Si un message est fourni, on peut l'ajouter aux logs ou à une table de notifications


# Fonction utilitaire pour récupérer le pool (à adapter)
def get_pool():
    from app.database.postgres_connection import get_pool as _get_pool
    return _get_pool()