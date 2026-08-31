import asyncio
import uuid
import json
from typing import List, Dict, Any
from pathlib import Path
from loguru import logger
from app.core.config import settings

# Import des fonctions d'ingestion
import sys
sys.path.append('/app/data')
from ingest_documents_pipeline import (
    build_chunks, 
    enrich_chunks_with_embeddings,
    save_chunks_to_json,
    print_chunk_summary
)
from write_embeddings_to_postgres import get_postgres_connection, insert_chunks_with_embeddings

# Stockage des tâches en mémoire (pour le prototype)
# En production, utiliser Redis ou une base de données
tasks = {}


def start_ingestion(files: List[str], metadata: Dict[str, Any], temp_dir: str) -> str:
    """Démarre une tâche d'ingestion asynchrone"""
    task_id = str(uuid.uuid4())
    
    tasks[task_id] = {
        "status": "running",
        "progress": 0,
        "total": len(files),
        "message": "Initialisation...",
        "mode": "test" if metadata.get("skip_embedding", False) else "production"
    }
    
    # Lancer la tâche en arrière-plan
    asyncio.create_task(run_ingestion(task_id, files, metadata, temp_dir))
    
    return task_id


async def run_ingestion(task_id: str, files: List[str], metadata: Dict[str, Any], temp_dir: str):
    """Exécute l'ingestion des fichiers"""
    skip_embedding = metadata.get("skip_embedding", False)
    skip_db_insert = metadata.get("skip_db_insert", False)
    
    try:
        all_chunks = []
        total = len(files)
        
        for idx, file_path in enumerate(files):
            tasks[task_id]["message"] = f"Traitement de {Path(file_path).name}..."
            tasks[task_id]["progress"] = idx
            
            # Vérifier si on utilise le smart PDF
            use_smart = metadata.get("use_smart_pdf", settings.enable_smart_pdf)
            use_vision = metadata.get("use_vision_llm", settings.enable_vision_llm)
            
            # Créer un job temporaire pour build_chunks
            from ingest_documents_pipeline import IngestionJob
            from pathlib import Path
            
            job = IngestionJob(
                path=Path(file_path),
                metadata=metadata.copy()
            )
            
            # Ajouter la langue et le modèle d'embedding
            job.metadata["language"] = metadata.get("language", "english")
            job.metadata["embedding_model"] = settings.embedding_model
            
            # Générer les chunks
            chunks = build_chunks(
                job=job,
                chunk_size=1000,
                chunk_overlap=150,
                language=metadata.get("language", "english"),
                embedding_model=settings.embedding_model,
                use_smart_pdf=use_smart,
                use_vision_llm=use_vision
            )
            
            if chunks:
                all_chunks.extend(chunks)
                tasks[task_id]["message"] = f"{len(chunks)} chunks extraits de {Path(file_path).name}"
                tasks[task_id]["progress"] = idx + 1
        
        # Afficher le résumé
        print_chunk_summary(all_chunks, skip_embedding=skip_embedding)
        
        # Sauvegarder en JSON pour inspection (toujours)
        json_output = f"/app/uploads/chunks_{task_id}.json"
        save_chunks_to_json(all_chunks, json_output)
        tasks[task_id]["chunks_file"] = json_output
        
        # Générer les embeddings (sauf si skip)
        if not skip_embedding:
            tasks[task_id]["message"] = "Génération des embeddings..."
            enrich_chunks_with_embeddings(
                chunks=all_chunks,
                embedding_model=settings.embedding_model,
                max_tokens=settings.max_tokens,
                batch_size=8,
                skip_embedding=False
            )
        else:
            # Mode test: embeddings factices
            tasks[task_id]["message"] = "Mode test - embeddings factices..."
            enrich_chunks_with_embeddings(
                chunks=all_chunks,
                embedding_model=settings.embedding_model,
                max_tokens=settings.max_tokens,
                batch_size=8,
                skip_embedding=True
            )
        
        # Insertion en base de données (sauf si skip)
        if not skip_db_insert and not skip_embedding:
            tasks[task_id]["message"] = "Insertion dans la base de données..."
            conn = get_postgres_connection()
            try:
                inserted = insert_chunks_with_embeddings(conn, all_chunks)
                tasks[task_id]["chunks_inserted"] = inserted
            finally:
                conn.close()
        else:
            tasks[task_id]["message"] = f"Insertion DB SKIPPÉE (mode test)"
            tasks[task_id]["chunks_inserted"] = 0
        
        # Nettoyer le répertoire temporaire
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["progress"] = total
        tasks[task_id]["message"] = f"Succès: {len(all_chunks)} chunks générés"
        tasks[task_id]["chunks_count"] = len(all_chunks)
        tasks[task_id]["mode"] = "test" if skip_embedding else "production"
        
        logger.info(f"Tâche {task_id} terminée: {len(all_chunks)} chunks, mode={'test' if skip_embedding else 'production'}")
        
    except Exception as e:
        logger.error(f"Erreur dans la tâche {task_id}: {e}")
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["message"] = str(e)


def get_task_status(task_id: str) -> Dict[str, Any]:
    """Récupère le statut d'une tâche"""
    return tasks.get(task_id, {"status": "not_found"})