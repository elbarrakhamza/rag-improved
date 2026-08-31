from fastapi import Security,HTTPException,status
from fastapi.security import APIKeyHeader
from app.core.config import settings


api_key=APIKeyHeader(name="X-API-Key",auto_error=False)

async def get_api_key(api_key:str=Security(api_key)):
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key is missing!"
        )
    elif api_key!=settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Key"
        )
    return api_key