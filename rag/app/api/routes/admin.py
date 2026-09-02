import asyncio
from importlib.metadata import metadata
import json
import uuid

from fastapi import APIRouter, Request, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import List, Optional
import os
import zipfile
import tempfile
import shutil
from pathlib import Path
from loguru import logger
from app.core.security import get_admin_api_key, clear_api_key_cache
from app.service.cache import embedding_cache
from app.core.config import settings
from app.tasks.ingestion_task import start_ingestion_task
import hashlib

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/upload")
async def upload_documents(
    request: Request,
    files: List[UploadFile] = File(...),
    brand: str = Form("unknown"),
    elevator_model: str = Form("unknown"),
    document_type: str = Form("maintenance_manual"),
    document_version: str = Form("unknown"),
    visibility: str = Form("public"),
    use_smart_pdf: bool = Form(True),
    use_vision_llm: bool = Form(True),
    skip_embedding: bool = Form(False),
    skip_db_insert: bool = Form(False),
    mode: str = Form("auto"),  # NOUVEAU : 'auto' ou 'manual'
    key_info: dict = Depends(get_admin_api_key)
):
    """
    Upload de documents pour ingestion.
    mode : 'auto' (tout enchaîné) ou 'manual' (génération des chunks seulement)
    """
    try:
        temp_dir = tempfile.mkdtemp()
        uploaded_files = []
        
        for file in files:
            file_path = os.path.join(temp_dir, file.filename)
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            
            if file.filename.endswith('.zip'):
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                os.remove(file_path)
            else:
                uploaded_files.append(file_path)
        
        # Ajouter les fichiers extraits du ZIP
        for root, _, files_in_dir in os.walk(temp_dir):
            for file_in_dir in files_in_dir:
                if file_in_dir.endswith(('.pdf', '.txt', '.md', '.markdown')):
                    uploaded_files.append(os.path.join(root, file_in_dir))
        
        if not uploaded_files:
            raise HTTPException(
                status_code=400,
                detail="No supported files found (PDF, TXT, MD)"
            )
        
        task_id = str(uuid.uuid4())
        async with request.app.state.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO ingestion_tasks (id, status, files, metadata, options, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
                """,
                task_id,
                "UPLOADED",
                json.dumps(uploaded_files),
                json.dumps({
                    "brand": brand,
                    "elevator_model": elevator_model,
                    "document_type": document_type,
                    "document_version": document_version,
                    "visibility": visibility,
                    "use_smart_pdf": use_smart_pdf,
                    "use_vision_llm": use_vision_llm,
                    "skip_embedding": skip_embedding,
                    "skip_db_insert": skip_db_insert
                }),
                json.dumps({"mode": mode})
            )

        # Lancer l'ingestion en arrière-plan
        asyncio.create_task(start_ingestion_task(task_id, uploaded_files, metadata, mode))

        return {
            "status": "success",
            "task_id": task_id,
            "files_count": len(uploaded_files),
            "message": f"Ingestion started in {mode} mode",
            "mode": mode
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de l'upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task/{task_id}")
async def get_task_status(
    task_id: str,
    request: Request,
    key_info: dict = Depends(get_admin_api_key)
):
    """Récupère le statut d'une tâche d'ingestion."""
    from app.tasks.ingestion_task import get_task_status_async
    status = await get_task_status_async(task_id)
    if status.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Task not found")
    return status


@router.post("/api-keys/generate")
async def generate_api_key(
    request: Request,
    role: str = Form("public"),
    user_id: Optional[int] = Form(None),
    description: Optional[str] = Form(None),
    key_info: dict = Depends(get_admin_api_key)
):
    """
    Génère une nouvelle clé API avec un rôle spécifique
    """
    if role not in ["admin", "employee", "public"]:
        raise HTTPException(
            status_code=400,
            detail="Role must be 'admin', 'employee', or 'public'"
        )
    
    # Générer une clé aléatoire
    import secrets
    api_key = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO api_keys (key_hash, role, user_id, description, is_active, created_at)
            VALUES ($1, $2, $3, $4, TRUE, NOW())
            """,
            key_hash,
            role,
            user_id,
            description
        )
    
    # Vider le cache des clés
    clear_api_key_cache()
    
    return {
        "api_key": api_key,
        "role": role,
        "description": description,
        "message": "Clé API générée avec succès. Conservez-la précieusement."
    }


@router.get("/api-keys")
async def list_api_keys(
    request: Request,
    key_info: dict = Depends(get_admin_api_key)
):
    """
    Liste toutes les clés API
    """
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT 
                id,
                role,
                user_id,
                description,
                is_active,
                created_at,
                last_used
            FROM api_keys
            ORDER BY created_at DESC
            """
        )
    
    return [dict(row) for row in rows]


@router.post("/api-keys/{key_id}/toggle")
async def toggle_api_key(
    key_id: int,
    request: Request,
    key_info: dict = Depends(get_admin_api_key)
):
    """
    Active ou désactive une clé API
    """
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT is_active FROM api_keys WHERE id = $1",
            key_id
        )
        
        if not row:
            raise HTTPException(status_code=404, detail="API key not found")
        
        new_status = not row["is_active"]
        await conn.execute(
            "UPDATE api_keys SET is_active = $1 WHERE id = $2",
            new_status,
            key_id
        )
    
    clear_api_key_cache()
    
    return {
        "status": "success",
        "key_id": key_id,
        "is_active": new_status
    }


@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: int,
    request: Request,
    key_info: dict = Depends(get_admin_api_key)
):
    """
    Supprime une clé API
    """
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM api_keys WHERE id = $1",
            key_id
        )
        
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="API key not found")
    
    clear_api_key_cache()
    
    return {
        "status": "success",
        "message": "API key deleted"
    }


@router.get("/cache/stats")
async def cache_stats(key_info: dict = Depends(get_admin_api_key)):
    """Statistiques du cache d'embeddings"""
    return embedding_cache.get_stats()


@router.delete("/cache/clear")
async def clear_cache(key_info: dict = Depends(get_admin_api_key)):
    """Vider le cache d'embeddings"""
    if embedding_cache.clear_cache():
        return {"status": "success", "message": "Cache cleared"}
    else:
        raise HTTPException(status_code=500, detail="Failed to clear cache")


@router.get("/documents")
async def list_documents(
    request: Request,
    page: int = 1,
    limit: int = 50,
    key_info: dict = Depends(get_admin_api_key)
):
    """Liste des documents indexés"""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        offset = (page - 1) * limit
        rows = await conn.fetch(
            """
            SELECT DISTINCT 
                metadata->>'source_file' as source_file,
                metadata->>'brand' as brand,
                metadata->>'elevator_model' as model,
                metadata->>'document_type' as type,
                metadata->>'document_version' as version,
                metadata->>'visibility' as visibility,
                COUNT(*) OVER() as total_count
            FROM documents
            ORDER BY source_file
            LIMIT $1 OFFSET $2
            """,
            limit, offset
        )
        
        results = []
        total = 0
        for row in rows:
            total = row['total_count']
            results.append({
                "source_file": row['source_file'],
                "brand": row['brand'],
                "model": row['model'],
                "type": row['type'],
                "version": row['version'],
                "visibility": row['visibility']
            })
        
        return {
            "documents": results,
            "total": total,
            "page": page,
            "limit": limit
        }


@router.delete("/documents/{source_file}")
async def delete_document(
    source_file: str,
    request: Request,
    key_info: dict = Depends(get_admin_api_key)
):
    """Supprime un document et ses chunks"""
    import urllib.parse
    
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        decoded_source = urllib.parse.unquote(source_file)
        
        result = await conn.execute(
            "DELETE FROM documents WHERE metadata->>'source_file' = $1",
            decoded_source
        )
        
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {"status": "success", "message": f"Document {decoded_source} deleted"}