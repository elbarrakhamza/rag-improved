from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel, Field
from asyncpg import Connection
from loguru import logger
from typing import Optional, List, Dict, Any
from app.core.security import get_api_key
from app.api.dependices import get_connection
from app.service.retriever import update_feedback_score
from app.service.feedback_analyzer import feedback_analyzer
from app.api.limiter import limiter

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackRequest(BaseModel):
    question: str = Field(min_length=5, max_length=500)
    answer: Optional[str] = Field(None, max_length=5000)
    document_id: Optional[int] = None
    chunk_id: Optional[int] = None
    score: int = Field(ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=1000)
    is_helpful: Optional[bool] = None


@router.post("/submit")
@limiter.limit("100/minute")
async def submit_feedback(
    request: Request,
    feedback: FeedbackRequest,
    db_connection: Connection = Depends(get_connection),
    key_info: dict = Depends(get_api_key)
):
    """Soumettre un feedback sur une réponse"""
    try:
        logger.info(f"Feedback reçu pour: {feedback.question[:50]}...")
        
        api_key_id = key_info.get("api_key_id")
        
        result = await db_connection.fetchrow(
            """
            INSERT INTO feedback (
                question, answer, document_id, chunk_id, score, comment,
                api_key_id, user_ip, is_helpful, created_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
            RETURNING id
            """,
            feedback.question,
            feedback.answer,
            feedback.document_id,
            feedback.chunk_id,
            feedback.score,
            feedback.comment,
            api_key_id,
            request.client.host if request.client else None,
            feedback.is_helpful
        )
        
        feedback_id = result["id"]
        
        if feedback.document_id:
            await update_feedback_score(db_connection, feedback.document_id, feedback.score)
        
        await feedback_analyzer.record_question_pattern(
            db_connection,
            feedback.question,
            feedback.score
        )
        
        logger.info(f"Feedback {feedback_id} enregistré avec succès")
        
        return {
            "status": "success",
            "feedback_id": feedback_id,
            "message": "Feedback enregistré avec succès"
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de l'enregistrement du feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/question")
@limiter.limit("100/minute")
async def get_question_stats(
    request: Request,
    question: str,
    db_connection: Connection = Depends(get_connection),
    key_info: dict = Depends(get_api_key)
):
    """Statistiques pour une question spécifique"""
    if key_info.get("role") not in ["admin", "employee"]:
        raise HTTPException(
            status_code=403,
            detail="Only admin and employees can view feedback stats"
        )
    
    stats = await feedback_analyzer.get_question_feedback_summary(db_connection, question)
    
    rows = await db_connection.fetch(
        """
        SELECT 
            score,
            comment,
            created_at
        FROM feedback
        WHERE question ILIKE $1
        ORDER BY created_at DESC
        LIMIT 10
        """,
        f"%{question}%"
    )
    
    recent_feedback = [dict(row) for row in rows]
    
    return {
        "question": question,
        "stats": stats,
        "recent_feedback": recent_feedback
    }


@router.get("/top-questions")
@limiter.limit("100/minute")
async def get_top_questions(
    request: Request,
    db_connection: Connection = Depends(get_connection),
    key_info: dict = Depends(get_api_key),
    limit: int = 10,
    days_back: int = 30
):
    """
    Récupère les questions les plus posées (sans filtre de date pour simplifier)
    """
    try:
        # Version simplifiée - on ignore le filtre de date
        rows = await db_connection.fetch(
            """
            SELECT 
                question_hash,
                question_text,
                frequency,
                avg_feedback_score,
                last_asked
            FROM question_patterns
            ORDER BY frequency DESC
            LIMIT $1
            """,
            limit
        )
        
        return [dict(row) for row in rows]
        
    except Exception as e:
        logger.error(f"Erreur get_top_questions: {e}")
        # En cas d'erreur, retourner un tableau vide
        return []


@router.get("/low-performing-questions")
@limiter.limit("100/minute")
async def get_low_performing_questions(
    request: Request,
    db_connection: Connection = Depends(get_connection),
    key_info: dict = Depends(get_api_key),
    min_frequency: int = 2,
    max_avg_score: float = 3.0,
    days_back: int = 30
):
    """
    Récupère les questions qui ont des mauvais feedbacks (à améliorer)
    """
    if key_info.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admin can view low performing questions"
        )
    
    try:
        # Version simplifiée - on ignore le filtre de date
        rows = await db_connection.fetch(
            """
            SELECT 
                question_hash,
                question_text,
                frequency,
                avg_feedback_score,
                last_asked
            FROM question_patterns
            WHERE 
                frequency >= $1
                AND avg_feedback_score <= $2
            ORDER BY avg_feedback_score ASC, frequency DESC
            LIMIT 20
            """,
            min_frequency,
            max_avg_score
        )
        
        return {
            "questions": [dict(row) for row in rows],
            "count": len(rows),
            "filters": {
                "min_frequency": min_frequency,
                "max_avg_score": max_avg_score,
                "days_back": days_back
            }
        }
        
    except Exception as e:
        logger.error(f"Erreur get_low_performing_questions: {e}")
        return {"questions": [], "count": 0, "filters": {}}