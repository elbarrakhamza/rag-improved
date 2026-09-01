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
    
    if role != "public":
        # Pour admin/employee: RECHERCHER DANS LES DEUX
        logger.info(f"🔍 Admin: recherche dans documents publics ET privés")
        
        # 1. Recherche dans les documents publics
        query_public = """
            SELECT  
                content,
                metadata,
                1 - (embedding <=> $1::vector) AS similarity,
                feedback_score,
                feedback_count
            FROM documents
            WHERE 1 - (embedding <=> $1::vector) >= $2
            AND (metadata->>'visibility' = 'public' OR metadata->>'visibility' IS NULL)
            ORDER BY similarity DESC
            LIMIT $3
        """
        
        public_rows = await db_con.fetch(
            query_public,
            embedding,
            settings.min_similarity,
            top_k
        )
        
        # 2. Recherche dans les documents privés
        query_private = """
            SELECT  
                content,
                metadata,
                1 - (embedding <=> $1::vector) AS similarity,
                feedback_score,
                feedback_count
            FROM documents
            WHERE 1 - (embedding <=> $1::vector) >= $2
            AND metadata->>'visibility' = 'private'
            ORDER BY similarity DESC
            LIMIT $3
        """
        
        private_rows = await db_con.fetch(
            query_private,
            embedding,
            settings.min_similarity,
            top_k
        )
        
        # 3. Combiner les résultats
        results = []
        
        # Ajouter les résultats publics
        for row in public_rows:
            results.append({
                "content": row["content"],
                "metadata": json.loads(row["metadata"]),
                "similarity": float(row["similarity"]),
                "feedback_score": float(row.get("feedback_score") or 0),
                "feedback_count": int(row.get("feedback_count") or 0)
            })
        
        # Ajouter les résultats privés
        for row in private_rows:
            results.append({
                "content": row["content"],
                "metadata": json.loads(row["metadata"]),
                "similarity": float(row["similarity"]),
                "feedback_score": float(row.get("feedback_score") or 0),
                "feedback_count": int(row.get("feedback_count") or 0)
            })
        
        # Trier par similarité décroissante
        results.sort(key=lambda x: x["similarity"], reverse=True)
        
        # Limiter au nombre demandé
        results = results[:top_k]
        
        if len(results) > 0:
            visibilities = [r["metadata"].get("visibility", "public") for r in results]
            sources = [r["metadata"].get("source_file", "unknown") for r in results]
            logger.info(f"✅ {len(results)} résultats combinés pour admin")
            logger.info(f"   Visibilités: {set(visibilities)}")
            logger.info(f"   Sources: {set(sources)}")
        else:
            logger.info(f"⚠️ Aucun résultat trouvé (similarité > {settings.min_similarity})")
        
        return results
        
    else:
        # Pour public: seulement les documents publics
        logger.info(f"🔍 Public: recherche dans les documents publics uniquement")
        
        query = """
            SELECT  
                content,
                metadata,
                1 - (embedding <=> $1::vector) AS similarity,
                feedback_score,
                feedback_count
            FROM documents
            WHERE 1 - (embedding <=> $1::vector) >= $2
            AND (metadata->>'visibility' = 'public' OR metadata->>'visibility' IS NULL)
            ORDER BY similarity DESC
            LIMIT $3
        """
        
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
        
        logger.info(f"✅ {len(results)} résultats publics trouvés")
        return results


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