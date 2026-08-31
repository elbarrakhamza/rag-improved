from fastapi import Security, HTTPException, status, Request
from fastapi.security import APIKeyHeader
from app.core.config import settings
from typing import Optional, Dict, Any
import hashlib

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Cache des clés API en mémoire (pour performances)
_api_key_cache: Dict[str, Dict[str, Any]] = {}


async def get_api_key_info(api_key: str, request: Optional[Request] = None) -> Dict[str, Any]:
    """
    Récupère les informations de la clé API depuis la base de données
    Retourne: {"role": "admin"|"employee"|"public", "user_id": int, "key_hash": str}
    """
    # Vérifier le cache
    if api_key in _api_key_cache:
        return _api_key_cache[api_key]
    
    # Calculer le hash de la clé
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    
    # Vérifier si c'est la clé admin (fallback rapide)
    if api_key == settings.admin_api_key:
        result = {"role": "admin", "user_id": 0, "key_hash": key_hash}
        _api_key_cache[api_key] = result
        return result
    
    # Vérifier dans la base de données
    if request and hasattr(request.app, "state") and hasattr(request.app.state, "pool"):
        pool = request.app.state.pool
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, role, user_id, is_active
                FROM api_keys
                WHERE key_hash = $1 AND is_active = true
                """,
                key_hash
            )
            
            if row:
                result = {
                    "role": row["role"],
                    "user_id": row["user_id"],
                    "key_hash": key_hash,
                    "api_key_id": row["id"]
                }
                _api_key_cache[api_key] = result
                return result
    
    return {"role": "public", "user_id": None, "key_hash": key_hash}


# CORRECTION ICI : remplacer Optional[Request] par Request avec None par défaut
async def get_api_key(
    api_key: str = Security(api_key_header),
    request: Request = None
) -> Dict[str, Any]:
    """
    Vérifie et retourne les informations de la clé API
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key is missing!"
        )
    
    key_info = await get_api_key_info(api_key, request)
    
    # Vérifier que la clé est valide (admin ou en base de données)
    if api_key != settings.admin_api_key and key_info.get("role") == "public":
        if request and hasattr(request.app, "state") and hasattr(request.app.state, "pool"):
            pool = request.app.state.pool
            async with pool.acquire() as conn:
                exists = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM api_keys WHERE key_hash = $1 AND is_active = true)",
                    key_info["key_hash"]
                )
                if not exists:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Invalid API Key"
                    )
    
    return key_info


# CORRECTION ICI aussi
async def get_admin_api_key(
    api_key: str = Security(api_key_header),
    request: Request = None
) -> Dict[str, Any]:
    """
    Vérifie que la clé API a des droits admin
    """
    key_info = await get_api_key(api_key, request)
    
    if key_info.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    return key_info


def clear_api_key_cache():
    """Vide le cache des clés API (utile après modification)"""
    global _api_key_cache
    _api_key_cache.clear()