from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel, Field
from asyncpg import Connection
from loguru import logger
from typing import Optional
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
    score: int = Field(ge=1, le=5, description="Score de 1 (très mauvais) à 5 (très bon)")
    comment: Optional[str] = Field(None, max_length=1000)
    is_helpful: Optional[bool] = None


class FeedbackStatsRequest(BaseModel):
    question: str = Field(min_length=5, max_length=500)


@router.post("/submit")
@limiter.limit("10/minute")
async def submit_feedback(
    request: Request,
    feedback: FeedbackRequest,
    db_connection: Connection = Depends(get_connection),
    key_info: dict = Depends(get_api_key)
):
    """
    Soumettre un feedback sur une réponse
    """
    try:
        logger.info(f"Feedback reçu pour: {feedback.question[:50]}...")
        
        # Récupérer l'ID de la clé API
        api_key_id = key_info.get("api_key_id")
        
        # Insérer le feedback
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
        
        # Mettre à jour le score du document si un document_id est fourni
        if feedback.document_id:
            await update_feedback_score(db_connection, feedback.document_id, feedback.score)
        
        # Mettre à jour les patterns de questions
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
@limiter.limit("10/minute")
async def get_question_stats(
    request: Request,
    question: str,
    db_connection: Connection = Depends(get_connection),
    key_info: dict = Depends(get_api_key)
):
    """
    Statistiques pour une question spécifique
    """
    if key_info.get("role") not in ["admin", "employee"]:
        raise HTTPException(
            status_code=403,
            detail="Only admin and employees can view feedback stats"
        )
    
    stats = await feedback_analyzer.get_question_feedback_summary(db_connection, question)
    
    # Récupérer les feedbacks récents
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
@limiter.limit("5/minute")
async def get_top_questions(
    request: Request,
    db_connection: Connection = Depends(get_connection),
    key_info: dict = Depends(get_api_key),
    limit: int = 10,
    days_back: int = 30
):
    """
    Récupère les questions les plus posées
    """
    if key_info.get("role") not in ["admin", "employee"]:
        raise HTTPException(
            status_code=403,
            detail="Only admin and employees can view top questions"
        )
    
    rows = await db_connection.fetch(
        """
        SELECT 
            question_hash,
            question_text,
            frequency,
            avg_feedback_score,
            last_asked
        FROM question_patterns
        WHERE last_asked >= NOW() - INTERVAL '$1 days' * INTERVAL '1 day'
        ORDER BY frequency DESC
        LIMIT $2
        """,
        days_back,
        limit
    )
    
    return [dict(row) for row in rows]


@router.get("/low-performing-questions")
@limiter.limit("5/minute")
async def get_low_performing_questions(
    request: Request,
    db_connection: Connection = Depends(get_connection),
    key_info: dict = Depends(get_api_key),
    min_frequency: int = 3,
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
    
    questions = await feedback_analyzer.get_low_performance_questions(
        db_connection,
        min_frequency=min_frequency,
        max_avg_score=max_avg_score,
        days_back=days_back
    )
    
    return {
        "questions": questions,
        "count": len(questions),
        "filters": {
            "min_frequency": min_frequency,
            "max_avg_score": max_avg_score,
            "days_back": days_back
        }
    }