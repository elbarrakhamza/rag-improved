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
        """Enregistre un pattern de question pour analyse future"""
        try:
            question_hash = hashlib.sha256(question.lower().encode()).hexdigest()
            
            if feedback_score is not None:
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
        except Exception as e:
            logger.warning(f"Could not record question pattern: {e}")
    
    @staticmethod
    async def get_low_performance_questions(
        db_con: Connection,
        min_frequency: int = 3,
        max_avg_score: float = 3.0,
        days_back: int = 30
    ) -> List[Dict[str, Any]]:
        try:
            # CORRECTION: Syntaxe INTERVAL PostgreSQL correcte
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
                    AND last_asked >= NOW() - ($3 || ' days')::INTERVAL
                ORDER BY avg_feedback_score ASC, frequency DESC
                LIMIT 20
                """,
                min_frequency,
                max_avg_score,
                days_back
            )
            return [dict(row) for row in rows]
        except Exception as e:
            logger.warning(f"Could not get low performance questions: {e}")
            return []


feedback_analyzer = FeedbackAnalyzer()