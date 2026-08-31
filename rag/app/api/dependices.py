from fastapi import Request

async def get_connection(request: Request):
    pool = request.app.state.pool
    if pool is None:
        raise Exception("DB Pool isn't initialised yet")
    
    async with pool.acquire() as connection:
        yield connection

def get_embedder(request: Request):
    return request.app.state.embedder

def get_access_rate_limiter(request: Request):
    return request.app.state.limiter