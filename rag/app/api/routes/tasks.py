from fastapi import APIRouter, Request, Depends, HTTPException
from typing import List, Dict, Any, Optional
from asyncpg import Connection
from loguru import logger
import json
from app.core.security import get_admin_api_key
from app.api.dependices import get_connection
from app.api.limiter import limiter

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/")  # ← slash final important
@limiter.limit("20/minute")
async def list_tasks(
    request: Request,
    db_connection: Connection = Depends(get_connection),
    key_info: dict = Depends(get_admin_api_key),
    limit: int = 20,
    offset: int = 0
):
    rows = await db_connection.fetch(
        """
        SELECT 
            id,
            status,
            files,
            metadata,
            options,
            created_at,
            updated_at,
            error_message
        FROM ingestion_tasks
        ORDER BY created_at DESC
        LIMIT $1 OFFSET $2
        """,
        limit, offset
    )
    return [dict(row) for row in rows]


@router.get("/{task_id}")
@limiter.limit("20/minute")
async def get_task(
    task_id: str,
    request: Request,
    db_connection: Connection = Depends(get_connection),
    key_info: dict = Depends(get_admin_api_key)
):
    row = await db_connection.fetchrow(
        "SELECT * FROM ingestion_tasks WHERE id = $1",
        task_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    return dict(row)


@router.get("/{task_id}/chunks")
@limiter.limit("20/minute")
async def get_task_chunks(
    task_id: str,
    request: Request,
    db_connection: Connection = Depends(get_connection),
    key_info: dict = Depends(get_admin_api_key)
):
    row = await db_connection.fetchrow("SELECT chunks FROM ingestion_tasks WHERE id = $1", task_id)
    if not row: raise HTTPException(404, "Task not found")
    chunks = row["chunks"]
    if chunks is None: raise HTTPException(404, "No chunks available")
    return chunks


@router.put("/{task_id}/chunks")
@limiter.limit("10/minute")
async def update_task_chunks(
    task_id: str,
    chunks: List[Dict[str, Any]],
    request: Request,
    db_connection: Connection = Depends(get_connection),
    key_info: dict = Depends(get_admin_api_key)
):
    row = await db_connection.fetchrow(
        "SELECT status FROM ingestion_tasks WHERE id = $1",
        task_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    status = row["status"]
    if status not in ("CHUNKS_GENERATED", "CHUNKS_MODIFIED"):
        raise HTTPException(
            status_code=400,
            detail=f"Chunks cannot be modified in current status: {status}"
        )
    await db_connection.execute(
        """
        UPDATE ingestion_tasks
        SET chunks = $1, status = 'CHUNKS_MODIFIED', updated_at = NOW()
        WHERE id = $2
        """,
        json.dumps(chunks),
        task_id
    )
    return {"status": "success", "message": "Chunks updated"}


@router.post("/{task_id}/validate")
@limiter.limit("10/minute")
async def validate_task(
    task_id: str,
    request: Request,
    db_connection: Connection = Depends(get_connection),
    key_info: dict = Depends(get_admin_api_key)
):
    row = await db_connection.fetchrow(
        "SELECT status, options, chunks, metadata, files FROM ingestion_tasks WHERE id = $1",
        task_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    status = row["status"]
    if status not in ("CHUNKS_GENERATED", "CHUNKS_MODIFIED"):
        raise HTTPException(
            status_code=400,
            detail=f"Task cannot be validated in current status: {status}"
        )

    await db_connection.execute(
        """
        UPDATE ingestion_tasks
        SET status = 'EMBEDDING_IN_PROGRESS', updated_at = NOW()
        WHERE id = $1
        """,
        task_id
    )

    from app.tasks.ingestion_task import run_embedding_phase
    import asyncio
    asyncio.create_task(run_embedding_phase(task_id, row["chunks"], row["metadata"]))

    return {"status": "success", "message": "Embedding started"}


@router.post("/{task_id}/cancel")
@limiter.limit("10/minute")
async def cancel_task(
    task_id: str,
    request: Request,
    db_connection: Connection = Depends(get_connection),
    key_info: dict = Depends(get_admin_api_key)
):
    await db_connection.execute(
        """
        UPDATE ingestion_tasks
        SET status = 'CANCELLED', updated_at = NOW()
        WHERE id = $1
        """,
        task_id
    )
    return {"status": "success", "message": "Task cancelled"}


@router.post("/{task_id}/retry")
@limiter.limit("10/minute")
async def retry_task(
    task_id: str,
    request: Request,
    db_connection: Connection = Depends(get_connection),
    key_info: dict = Depends(get_admin_api_key)
):
    row = await db_connection.fetchrow(
        "SELECT status FROM ingestion_tasks WHERE id = $1",
        task_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    if row["status"] != "FAILED":
        raise HTTPException(status_code=400, detail="Only failed tasks can be retried")

    await db_connection.execute(
        """
        UPDATE ingestion_tasks
        SET status = 'CHUNKS_GENERATED', error_message = NULL, updated_at = NOW()
        WHERE id = $1
        """,
        task_id
    )
    return {"status": "success", "message": "Task retried"}