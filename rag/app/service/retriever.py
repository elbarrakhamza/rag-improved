from asyncpg import Connection
from app.core.config import settings
from typing import Optional, List, Dict, Any
import json
from loguru import logger


async def retrive(
    db_con: Connection,
    embedding: str,
    top_k: int = None,
    role: str = "public",
    boost_high_feedback: bool = True
) -> List[Dict[str, Any]]:
    """
    Recherche les chunks pertinents avec filtrage par rôle
    """
    top_k = top_k if top_k is not None else settings.top_k
    
    # Filtrer par visibilité selon le rôle
    # admin et employee: voient tout (public + private)
    # public: voient seulement les documents publics
    if role == "public":
        visibility_filter = "AND (metadata->>'visibility' = 'public' OR metadata->>'visibility' IS NULL)"
    else:
        # Pour admin et employee: pas de filtre (voient tout)
        visibility_filter = ""
    
    query = f"""
        SELECT  
            content,
            metadata,
            1 - (embedding <=> $1::vector) AS similarity,
            feedback_score,
            feedback_count
        FROM documents
        WHERE 1 - (embedding <=> $1::vector) >= $2
        {visibility_filter}
        ORDER BY similarity DESC
        LIMIT $3
    """
    
    try:
        rows = await db_con.fetch(
            query,
            embedding,
            settings.min_similarity,
            top_k
        )
        
        results = []
        for row in rows:
            results.append({
                "content": row["content"],
                "metadata": json.loads(row["metadata"]),
                "similarity": float(row["similarity"]),
                "feedback_score": float(row.get("feedback_score") or 0),
                "feedback_count": int(row.get("feedback_count") or 0)
            })
        
        # Si le rôle est admin/employee et que les résultats sont insuffisants,
        # faire une recherche sans filtre de visibilité (pour voir les docs publics aussi)
        if role != "public" and len(results) < top_k:
            logger.info(f"🔍 Recherche complémentaire pour admin/employee: {len(results)} résultats trouvés, recherche de plus de résultats")
            
            # Deuxième requête sans filtre (tout voir)
            query_no_filter = f"""
                SELECT  
                    content,
                    metadata,
                    1 - (embedding <=> $1::vector) AS similarity,
                    feedback_score,
                    feedback_count
                FROM documents
                WHERE 1 - (embedding <=> $1::vector) >= $2
                ORDER BY similarity DESC
                LIMIT $3
            """
            
            extra_rows = await db_con.fetch(
                query_no_filter,
                embedding,
                settings.min_similarity,
                top_k * 2  # Récupérer plus de résultats
            )
            
            # Ajouter les résultats manquants
            existing_content = {r["content"] for r in results}
            for row in extra_rows:
                row_dict = {
                    "content": row["content"],
                    "metadata": json.loads(row["metadata"]),
                    "similarity": float(row["similarity"]),
                    "feedback_score": float(row.get("feedback_score") or 0),
                    "feedback_count": int(row.get("feedback_count") or 0)
                }
                if row_dict["content"] not in existing_content:
                    results.append(row_dict)
                    existing_content.add(row_dict["content"])
                    if len(results) >= top_k:
                        break
        
        logger.info(f"🔍 Recherche: {len(results)} résultats pour le rôle {role}")
        if len(results) > 0:
            visibilities = [r["metadata"].get("visibility", "public") for r in results]
            logger.info(f"   Visibilités trouvées: {set(visibilities)}")
        
        return results[:top_k]  # Limiter au nombre demandé
        
    except Exception as e:
        logger.error(f"Erreur lors de la recherche: {e}")
        return []


async def update_feedback_score(
    db_con: Connection,
    document_id: int,
    score: int
) -> None:
    """Met à jour le feedback score d'un document"""
    if score < 1 or score > 5:
        raise ValueError("Score must be between 1 and 5")
    
    await db_con.execute(
        """
        UPDATE documents
        SET 
            feedback_score = (feedback_score * feedback_count + $1) / (feedback_count + 1),
            feedback_count = feedback_count + 1
        WHERE id = $2
        """,
        score,
        document_id
    )


async def get_top_documents_by_feedback(
    db_con: Connection,
    limit: int = 10,
    min_feedback: int = 3
) -> List[Dict[str, Any]]:
    """Récupère les documents les mieux notés"""
    rows = await db_con.fetch(
        """
        SELECT 
            id,
            content,
            metadata,
            feedback_score,
            feedback_count
        FROM documents
        WHERE feedback_count >= $1
        ORDER BY feedback_score DESC
        LIMIT $2
        """,
        min_feedback,
        limit
    )
    
    results = []
    for row in rows:
        results.append({
            "id": row["id"],
            "content": row["content"],
            "metadata": json.loads(row["metadata"]),
            "feedback_score": float(row["feedback_score"]),
            "feedback_count": row["feedback_count"]
        })
    
    return results