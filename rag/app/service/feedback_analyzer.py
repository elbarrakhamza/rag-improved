import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from asyncpg import Connection
from loguru import logger


class FeedbackAnalyzer:
    """Analyse et utilise les feedbacks pour améliorer la pertinence"""
    
    @staticmethod
    async def record_question_pattern(
        db_con: Connection,
        question: str,
        feedback_score: Optional[float] = None
    ) -> None:
        """
        Enregistre un pattern de question pour analyse future
        """
        question_hash = hashlib.sha256(question.lower().encode()).hexdigest()
        
        if feedback_score is not None:
            # Mise à jour avec feedback
            await db_con.execute(
                """
                INSERT INTO question_patterns (question_hash, question_text, frequency, avg_feedback_score, last_asked)
                VALUES ($1, $2, 1, $3, NOW())
                ON CONFLICT (question_hash) DO UPDATE SET
                    frequency = question_patterns.frequency + 1,
                    avg_feedback_score = (question_patterns.avg_feedback_score * question_patterns.frequency + $3) / (question_patterns.frequency + 1),
                    last_asked = NOW()
                """,
                question_hash,
                question[:500],
                feedback_score
            )
        else:
            # Simple incrément
            await db_con.execute(
                """
                INSERT INTO question_patterns (question_hash, question_text, frequency, last_asked)
                VALUES ($1, $2, 1, NOW())
                ON CONFLICT (question_hash) DO UPDATE SET
                    frequency = question_patterns.frequency + 1,
                    last_asked = NOW()
                """,
                question_hash,
                question[:500]
            )
    
    @staticmethod
    async def get_low_performance_questions(
        db_con: Connection,
        min_frequency: int = 3,
        max_avg_score: float = 3.0,
        days_back: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Récupère les questions qui ont des mauvais feedbacks
        """
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        rows = await db_con.fetch(
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
                AND last_asked >= $3
            ORDER BY avg_feedback_score ASC, frequency DESC
            LIMIT 20
            """,
            min_frequency,
            max_avg_score,
            cutoff_date
        )
        
        return [dict(row) for row in rows]
    
    @staticmethod
    async def get_question_feedback_summary(
        db_con: Connection,
        question: str
    ) -> Dict[str, Any]:
        """
        Résumé des feedbacks pour une question
        """
        question_hash = hashlib.sha256(question.lower().encode()).hexdigest()
        
        row = await db_con.fetchrow(
            """
            SELECT 
                frequency,
                avg_feedback_score,
                last_asked,
                COUNT(*) OVER() as total_questions
            FROM question_patterns
            WHERE question_hash = $1
            """,
            question_hash
        )
        
        if row:
            return {
                "frequency": row["frequency"],
                "avg_feedback_score": float(row["avg_feedback_score"]) if row["avg_feedback_score"] else None,
                "last_asked": row["last_asked"],
                "total_questions": row["total_questions"]
            }
        
        return {
            "frequency": 0,
            "avg_feedback_score": None,
            "last_asked": None,
            "total_questions": 0
        }


feedback_analyzer = FeedbackAnalyzer()