from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel, Field
from asyncpg import Connection
from loguru import logger
import asyncio
from app.core.security import get_api_key
from app.service.llm import generate
from app.service.prompt_builder import build_prompt
from app.service.embedder import Embedder
from app.service.retriever import retrive
from app.service.cache import embedding_cache
from app.service.feedback_analyzer import feedback_analyzer
from app.api.dependices import get_connection, get_embedder
from app.api.limiter import limiter
from app.core.config import settings
from typing import Optional

router = APIRouter()


class QueryRequest(BaseModel):
    question: str = Field(min_length=5, max_length=500)
    use_cache: bool = Field(default=True)
    top_k: Optional[int] = Field(default=None, ge=1, le=20)


@router.post("/query")
@limiter.limit("3/minute")
async def query(
    request: Request,
    query_request: QueryRequest,
    embedder: Embedder = Depends(get_embedder),
    db_connection: Connection = Depends(get_connection),
    key_info: dict = Depends(get_api_key)
):
    """
    Endpoint de question/réponse avec cache et feedback
    """
    try:
        async with asyncio.timeout(15):
            question = query_request.question
            use_cache = query_request.use_cache
            top_k = query_request.top_k or settings.top_k
            role = key_info.get("role", "public")
            
            logger.info(f"Question reçue de {role}: {question[:100]}...")
            
            # 1. Vérifier le cache pour la réponse complète
            cached_answer = None
            if use_cache:
                cached_answer = embedding_cache.get_answer(question)
            
            if cached_answer:
                logger.info(f"Réponse en cache pour: {question[:50]}...")
                # Enregistrer la question pour analyse
                await feedback_analyzer.record_question_pattern(db_connection, question)
                return {
                    "answer": cached_answer["answer"],
                    "token_usage": cached_answer["token_usage"],
                    "cached": True,
                    "sources": []  # On ne stocke pas les sources en cache
                }
            
            # 2. Embedding (avec cache)
            embedded_question = embedder.embed(question, use_cache=use_cache)
            embedded_question_str = str(embedded_question)
            
            # 3. Recherche des chunks (avec filtrage par rôle)
            retrieved_chunks = await retrive(
                db_con=db_connection,
                embedding=embedded_question_str,
                top_k=top_k,
                role=role,
                boost_high_feedback=True
            )
            
            if len(retrieved_chunks) == 0:
                logger.warning("Aucun chunk trouvé pour la question")
                # Enregistrer la question sans réponse
                await feedback_analyzer.record_question_pattern(db_connection, question)
                return {
                    "answer": "Information not found",
                    "token_usage": 0,
                    "sources": [],
                    "cached": False
                }
            
            logger.info(f"{len(retrieved_chunks)} chunks récupérés")
            
            # 4. Construction du prompt et génération
            prompt = build_prompt(
                question=question,
                documents=retrieved_chunks
            )
            response = await generate(prompt)
            
            # 5. Mettre en cache la réponse
            if use_cache:
                embedding_cache.set_answer(question, response[0], response[1])
            
            # 6. Enregistrer la question pour analyse
            await feedback_analyzer.record_question_pattern(db_connection, question)
            
            # 7. Préparer les sources
            sources = []
            for chunk in retrieved_chunks:
                metadata = chunk.get("metadata", {})
                sources.append({
                    "page": metadata.get("page_number", "N/A"),
                    "source_file": metadata.get("source_file", "N/A"),
                    "content": chunk.get("content", "")[:200] + "...",
                    "similarity": chunk.get("similarity", 0),
                    "feedback_score": chunk.get("feedback_score", 0),
                    "feedback_count": chunk.get("feedback_count", 0)
                })

    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Request timed out"
        )
    
    return {
        "answer": response[0],
        "token_usage": response[1],
        "sources": sources,
        "cached": False
    }