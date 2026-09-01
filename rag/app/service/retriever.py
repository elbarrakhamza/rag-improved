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
    - Public: voit seulement les documents publics
    - Admin/Employee: voit TOUS les documents (publics + privés)
    """
    top_k = top_k if top_k is not None else settings.top_k
    
    # Pour admin/employee: voir tous les documents, mais prioriser les privés
    if role != "public":
        # 1. Récupérer les documents privés (priorité)
        query_private = f"""
            SELECT  
                content,
                metadata,
                1 - (embedding <=> $1::vector) AS similarity,
                feedback_score,
                feedback_count
            FROM documents
            WHERE 1 - (embedding <=> $1::vector) >= $2
            AND (metadata->>'visibility' = 'private')
            ORDER BY similarity DESC
            LIMIT $3
        """
        
        private_rows = await db_con.fetch(
            query_private,
            embedding,
            settings.min_similarity,
            top_k
        )
        
        results = []
        for row in private_rows:
            results.append({
                "content": row["content"],
                "metadata": json.loads(row["metadata"]),
                "similarity": float(row["similarity"]),
                "feedback_score": float(row.get("feedback_score") or 0),
                "feedback_count": int(row.get("feedback_count") or 0)
            })
        
        logger.info(f"🔍 {len(results)} résultats privés trouvés")
        
        # 2. Si pas assez de résultats privés, chercher dans les documents publics
        if len(results) < top_k:
            remaining = top_k - len(results)
            logger.info(f"🔍 Recherche de {remaining} documents publics supplémentaires...")
            
            query_public = f"""
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
                remaining
            )
            
            for row in public_rows:
                results.append({
                    "content": row["content"],
                    "metadata": json.loads(row["metadata"]),
                    "similarity": float(row["similarity"]),
                    "feedback_score": float(row.get("feedback_score") or 0),
                    "feedback_count": int(row.get("feedback_count") or 0)
                })
            
            logger.info(f"🔍 {len(public_rows)} résultats publics ajoutés")
        
        # 3. Si toujours pas assez, chercher dans tous les documents (sans filtre)
        if len(results) < top_k:
            remaining = top_k - len(results)
            logger.info(f"🔍 Recherche de {remaining} documents supplémentaires (sans filtre)...")
            
            query_all = f"""
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
            
            all_rows = await db_con.fetch(
                query_all,
                embedding,
                settings.min_similarity,
                remaining
            )
            
            # Éviter les doublons
            existing_content = {r["content"] for r in results}
            for row in all_rows:
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
            
            logger.info(f"🔍 {len(all_rows)} résultats supplémentaires ajoutés")
        
        # Trier par similarité décroissante
        results.sort(key=lambda x: x["similarity"], reverse=True)
        results = results[:top_k]
        
        logger.info(f"✅ {len(results)} résultats totaux pour admin/employee")
        
    else:
        # Pour public: voir seulement les documents publics
        query_public = f"""
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
            query_public,
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
        
        logger.info(f"🔍 {len(results)} résultats publics trouvés")
    
    # Log des visibilités trouvées
    if len(results) > 0:
        visibilities = [r["metadata"].get("visibility", "public") for r in results]
        logger.info(f"   Visibilités trouvées: {set(visibilities)}")
    
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