from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel, Field
from asyncpg import Connection
from loguru import logger
import asyncio
from typing import Optional, Dict, Any, List

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

router = APIRouter()


class QueryRequest(BaseModel):
    question: str = Field(min_length=5, max_length=500)
    use_cache: bool = Field(default=True)
    top_k: Optional[int] = Field(default=None, ge=1, le=20)


class SourceInfo(BaseModel):
    page: str
    source_file: str
    content: str
    similarity: float
    feedback_score: float
    feedback_count: int


class QueryResponse(BaseModel):
    answer: str
    token_usage: int
    sources: List[SourceInfo] = []
    cached: bool = False


@router.post("/query", response_model=QueryResponse)
@limiter.limit("3/minute")
async def query(
    request: Request,
    query_request: QueryRequest,
    embedder: Embedder = Depends(get_embedder),
    db_connection: Connection = Depends(get_connection),
    key_info: Dict[str, Any] = Depends(get_api_key)
):
    """
    Endpoint de question/réponse avec cache et feedback
    """
    response = None
    sources = []
    
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
                await feedback_analyzer.record_question_pattern(db_connection, question)
                return QueryResponse(
                    answer=cached_answer["answer"],
                    token_usage=cached_answer["token_usage"],
                    sources=[],
                    cached=True
                )
            
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
                await feedback_analyzer.record_question_pattern(db_connection, question)
                return QueryResponse(
                    answer="Information not found",
                    token_usage=0,
                    sources=[],
                    cached=False
                )
            
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
            for chunk in retrieved_chunks:
                metadata = chunk.get("metadata", {})
                sources.append(
                    SourceInfo(
                        page=str(metadata.get("page_number", "N/A")),
                        source_file=metadata.get("source_file", "N/A"),
                        content=chunk.get("content", "")[:200] + "...",
                        similarity=chunk.get("similarity", 0),
                        feedback_score=chunk.get("feedback_score", 0),
                        feedback_count=chunk.get("feedback_count", 0)
                    )
                )

    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Request timed out"
        )
    except Exception as e:
        logger.error(f"Erreur lors du traitement: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
    
    return QueryResponse(
        answer=response[0] if response else "Erreur: pas de réponse générée",
        token_usage=response[1] if response else 0,
        sources=sources,
        cached=False
    )