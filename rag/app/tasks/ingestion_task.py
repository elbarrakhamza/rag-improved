import asyncio
import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

from loguru import logger

from app.core.config import settings
from app.database.postgres_connection import get_pool

sys.path.append("/app/data")

from ingest_documents_pipeline import (
    build_chunks,
    enrich_chunks_with_embeddings,
    IngestionJob,
)

from write_embeddings_to_postgres import (
    get_postgres_connection,
    insert_chunks_with_embeddings,
)


# ============================================================
# DATABASE - TASK STATUS
# ============================================================

async def update_task_status(
    task_id: str,
    status: str,
    error: Optional[str] = None,
    message: Optional[str] = None,
):
    """
    Met à jour le statut d'une tâche dans PostgreSQL.
    Cette fonction est asynchrone et ne bloque pas FastAPI.
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE ingestion_tasks
                SET
                    status = $1,
                    updated_at = NOW(),
                    error_message = $2
                WHERE id = $3
                """,
                status,
                error,
                task_id,
            )
        if message:
            logger.info(f"📋 Tâche {task_id} : {message}")
    except Exception as e:
        logger.exception(f"❌ Impossible de mettre à jour le statut de la tâche {task_id}: {e}")


# ============================================================
# DATABASE - SAVE CHUNKS
# ============================================================

async def save_chunks_to_task(
    task_id: str,
    chunks: List[Dict[str, Any]],
):
    """
    Stocke les chunks dans la tâche (en JSONB).
    json.dumps() est exécuté dans un thread pour éviter de bloquer l'event loop.
    """
    try:
        pool = await get_pool()
        # json.dumps est CPU-bound → on le déporte dans un thread
        chunks_json = await asyncio.to_thread(json.dumps, chunks)
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE ingestion_tasks
                SET
                    chunks = $1::jsonb,
                    updated_at = NOW()
                WHERE id = $2
                """,
                chunks_json,
                task_id,
            )
        logger.info(f"💾 Chunks sauvegardés pour la tâche {task_id}")
    except Exception as e:
        logger.exception(f"❌ Erreur sauvegarde chunks pour {task_id}: {e}")
        raise


# ============================================================
# GÉNÉRATION DES CHUNKS
# ============================================================

async def generate_chunks_for_task(
    files: List[str],
    metadata: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Génère les chunks à partir des fichiers.
    build_chunks() est synchrone et potentiellement très lourd.
    On l'exécute avec asyncio.to_thread() pour ne PAS bloquer l'event loop.
    """
    all_chunks: List[Dict[str, Any]] = []

    # Vérification du type de metadata
    if not isinstance(metadata, dict):
        logger.error(f"❌ metadata n'est pas un dictionnaire: {type(metadata)}")
        try:
            metadata = dict(metadata)
        except Exception:
            metadata = {}

    for index, file_path in enumerate(files, start=1):
        logger.info(f"📄 Traitement fichier {index}/{len(files)} : {file_path}")

        job_metadata = metadata.copy()
        job = IngestionJob(
            path=Path(file_path),
            metadata=job_metadata,
        )
        job.metadata["language"] = "english"
        job.metadata["embedding_model"] = settings.embedding_model

        # 🔥 OPÉRATION LOURDE : build_chunks() est synchrone
        chunks = await asyncio.to_thread(
            build_chunks,
            job=job,
            chunk_size=1000,
            chunk_overlap=150,
            language="english",
            embedding_model=settings.embedding_model,
            use_smart_pdf=metadata.get("use_smart_pdf", settings.enable_smart_pdf),
            use_vision_llm=metadata.get("use_vision_llm", settings.enable_vision_llm),
        )

        if chunks is None:
            chunks = []
        if not isinstance(chunks, list):
            raise ValueError(f"build_chunks() doit retourner une liste, mais retourne {type(chunks)}")

        all_chunks.extend(chunks)
        logger.info(f"✅ Fichier {index}/{len(files)} terminé : {len(chunks)} chunks")
        logger.info(f"📦 Total actuel : {len(all_chunks)} chunks")

    return all_chunks


# ============================================================
# SYNCHRONOUS POSTGRES INSERT (pour être appelé dans un thread)
# ============================================================

def insert_chunks_sync(chunks: List[Dict[str, Any]]) -> int:
    """
    Fonction synchrone utilisée dans un thread.
    On isole la connexion PostgreSQL synchrone ici afin de pouvoir appeler
    toute cette opération avec asyncio.to_thread().
    """
    conn = get_postgres_connection()
    try:
        return insert_chunks_with_embeddings(conn, chunks)
    finally:
        conn.close()


# ============================================================
# EMBEDDING PHASE
# ============================================================

async def run_embedding_phase(
    task_id: str,
    chunks: List[Dict[str, Any]],
    metadata: Dict[str, Any],
):
    """
    Génération des embeddings + insertion PostgreSQL.
    Toutes les opérations synchrones lourdes sont exécutées dans des threads.
    """
    try:
        # Vérification des chunks
        if isinstance(chunks, str):
            chunks = await asyncio.to_thread(json.loads, chunks)
        if not isinstance(chunks, list):
            raise ValueError("Chunks must be a list")

        logger.info(f"🧠 Tâche {task_id}: {len(chunks)} chunks à traiter")

        # Skip embedding ?
        if metadata.get("skip_embedding", False):
            logger.info(f"⏭️ Embedding ignoré pour {task_id}")
            await update_task_status(task_id, "COMPLETED", message="Embedding skipped (test mode)")
            return

        await update_task_status(
            task_id,
            "EMBEDDING_IN_PROGRESS",
            message=f"Génération des embeddings pour {len(chunks)} chunks",
        )

        logger.info(f"🧠 Génération embeddings pour {task_id}...")

        # 🔥 OPÉRATION LOURDE : enrich_chunks_with_embeddings() est synchrone
        await asyncio.to_thread(
            enrich_chunks_with_embeddings,
            chunks=chunks,
            embedding_model=settings.embedding_model,
            max_tokens=settings.max_tokens,
            batch_size=8,
            skip_embedding=False,
        )

        logger.info(f"✅ Embeddings terminés pour {task_id}")

        # Insertion en base de données
        if not metadata.get("skip_db_insert", False):
            await update_task_status(
                task_id,
                "DB_INSERT_IN_PROGRESS",
                message="Insertion des chunks dans PostgreSQL",
            )

            logger.info(f"💾 Insertion PostgreSQL pour {task_id}...")

            # 🔥 Toute la connexion + insertion est exécutée dans un thread
            inserted = await asyncio.to_thread(insert_chunks_sync, chunks)

            logger.info(f"✅ {inserted} chunks insérés pour {task_id}")

        # Terminé
        await update_task_status(task_id, "COMPLETED", message="Ingestion terminée avec succès")
        logger.info(f"🎉 Tâche {task_id} terminée")

    except Exception as e:
        logger.exception(f"❌ Erreur lors de l'embedding pour la tâche {task_id}: {e}")
        await update_task_status(task_id, "FAILED", error=str(e))


# ============================================================
# MAIN INGESTION TASK
# ============================================================

async def start_ingestion_task(
    task_id: str,
    files: List[str],
    metadata: Dict[str, Any],
    mode: str,
):
    """
    Point d'entrée principal de l'ingestion.
    Cette fonction est lancée avec asyncio.create_task() depuis FastAPI.
    Les opérations lourdes sont déportées dans des threads avec asyncio.to_thread().
    """
    try:
        logger.info(f"🚀 Démarrage tâche {task_id}, mode={mode}")
        logger.debug(f"📦 metadata reçu: {metadata} (type={type(metadata)})")

        if not isinstance(metadata, dict):
            logger.error(f"❌ metadata invalide: {type(metadata)}")
            try:
                metadata = dict(metadata)
            except Exception:
                await update_task_status(task_id, "FAILED", error="metadata must be a dictionary")
                return

        await update_task_status(
            task_id,
            "GENERATING_CHUNKS",
            message="Extraction et génération des chunks en cours",
        )

        # 🔥 build_chunks() est exécuté dans un thread via generate_chunks_for_task
        chunks = await generate_chunks_for_task(files, metadata)

        logger.info(f"📦 {len(chunks)} chunks générés pour {task_id}")

        # Sauvegarde des chunks (json.dumps dans un thread)
        await save_chunks_to_task(task_id, chunks)

        if mode == "auto":
            await run_embedding_phase(task_id, chunks, metadata)
        else:
            await update_task_status(
                task_id,
                "CHUNKS_GENERATED",
                message="Chunks générés, en attente de validation",
            )
            logger.info(f"⏸️ Tâche {task_id} en attente de validation")

    except asyncio.CancelledError:
        logger.warning(f"⚠️ Tâche {task_id} annulée")
        await update_task_status(task_id, "CANCELLED", error="Task cancelled")
        raise
    except Exception as e:
        logger.exception(f"❌ Erreur ingestion tâche {task_id}: {e}")
        await update_task_status(task_id, "FAILED", error=str(e))


# ============================================================
# GET TASK STATUS (ASYNC)
# ============================================================

async def get_task_status_async(task_id: str) -> Dict[str, Any]:
    """Récupère le statut d'une tâche depuis PostgreSQL."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    status,
                    files,
                    metadata,
                    options,
                    chunks,
                    created_at,
                    updated_at,
                    error_message
                FROM ingestion_tasks
                WHERE id = $1
                """,
                task_id,
            )
        if row is None:
            return {"status": "not_found"}
        return dict(row)
    except Exception as e:
        logger.exception(f"❌ Erreur récupération tâche {task_id}: {e}")
        return {"status": "error", "error": str(e)}


# ============================================================
# MEMORY CACHE – COMPATIBILITY (optionnel)
# ============================================================

tasks_memory: Dict[str, Any] = {}

def get_task_status_memory(task_id: str) -> Dict[str, Any]:
    return tasks_memory.get(task_id, {"status": "not_found"})