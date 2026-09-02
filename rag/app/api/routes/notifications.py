from fastapi import APIRouter, Request, Depends
from asyncpg import Connection
from loguru import logger
from app.core.security import get_api_key
from app.api.dependices import get_connection

router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.get("/stream")
async def notifications_stream(request: Request):
    """SSE endpoint pour les notifications en temps réel."""
    async def event_generator():
        # À implémenter avec Redis Pub/Sub ou un mécanisme de queue
        # Exemple simplifié : envoyer un ping toutes les 5 secondes
        import asyncio
        while True:
            yield f"data: {json.dumps({'type': 'ping'})}\n\n"
            await asyncio.sleep(5)
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")