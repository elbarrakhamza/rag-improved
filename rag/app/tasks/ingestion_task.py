import asyncio
import json
import shutil
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger
from app.core.config import settings
from app.database.postgres_connection import get_pool

sys.path.append('/app/data')
from ingest_documents_pipeline import build_chunks, enrich_chunks_with_embeddings, save_chunks_to_json, print_chunk_summary, IngestionJob
from write_embeddings_to_postgres import get_postgres_connection, insert_chunks_with_embeddings


async def update_task_status(task_id: str, status: str, error: str = None, message: str = None):
    """Met à jour le statut d'une tâche dans la base de données."""
    pool = await get_pool()  # ← important : await
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
    if message:
        logger.info(f"Tâche {task_id} : {message}")


async def save_chunks_to_task(task_id: str, chunks: List[Dict[str, Any]]):
    pool = await get_pool()
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


async def generate_chunks_for_task(files: List[str], metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    all_chunks = []
    for file_path in files:
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


async def run_embedding_phase(task_id: str, chunks: List[Dict[str, Any]], metadata: Dict[str, Any]):
    try:
        if metadata.get("skip_embedding", False):
            await update_task_status(task_id, "COMPLETED", message="Embedding skipped (test mode)")
            return

        enrich_chunks_with_embeddings(
            chunks=chunks,
            embedding_model=settings.embedding_model,
            max_tokens=settings.max_tokens,
            batch_size=8,
            skip_embedding=False
        )

        if not metadata.get("skip_db_insert", False):
            conn = get_postgres_connection()
            try:
                inserted = insert_chunks_with_embeddings(conn, chunks)
                logger.info(f"Inserted {inserted} chunks for task {task_id}")
            finally:
                conn.close()

        await update_task_status(task_id, "COMPLETED", message="Ingestion terminée avec succès")

    except Exception as e:
        logger.error(f"Erreur lors de l'embedding pour la tâche {task_id}: {e}")
        await update_task_status(task_id, "FAILED", error=str(e))


async def start_ingestion_task(task_id: str, files: List[str], metadata: Dict[str, Any], mode: str):
    try:
        await update_task_status(task_id, "GENERATING_CHUNKS", message="Extraction des chunks en cours")
        chunks = await generate_chunks_for_task(files, metadata)
        await save_chunks_to_task(task_id, chunks)

        if mode == "auto":
            await update_task_status(task_id, "EMBEDDING_IN_PROGRESS", message="Génération des embeddings")
            await run_embedding_phase(task_id, chunks, metadata)
        else:
            await update_task_status(task_id, "CHUNKS_GENERATED", message="Chunks générés, en attente de validation")

    except Exception as e:
        logger.error(f"Erreur lors de l'ingestion de la tâche {task_id}: {e}")
        await update_task_status(task_id, "FAILED", error=str(e))


async def get_task_status_async(task_id: str) -> Dict[str, Any]:
    """Récupère le statut d'une tâche depuis la base."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT status, files, metadata, options, chunks, created_at, updated_at, error_message FROM ingestion_tasks WHERE id = $1",
            task_id
        )
    if row is None:
        return {"status": "not_found"}
    return dict(row)


# Cache mémoire pour compatibilité avec l'ancien système (optionnel)
tasks_memory = {}


def get_task_status_memory(task_id: str) -> Dict[str, Any]:
    return tasks_memory.get(task_id, {"status": "not_found"})