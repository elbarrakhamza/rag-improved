import asyncpg
from app.core.config import settings

async def get_pool():
    print("getting pool")
    return await asyncpg.create_pool(
        host=settings.postgres_host,
        port=settings.postgres_port,
        database=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password,
        max_size=20,   # Augmenté de 10 à 20 pour éviter la saturation
        min_size=2,
    )