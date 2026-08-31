import asyncpg
from app.core.config import settings

async def get_pool():
	print("getting pool")
	
	return await asyncpg.create_pool(
		host=settings.postgres_host,
		port =settings.postgres_port,
		database=settings.postgres_db,	
		user=settings.postgres_user,
		password=settings.postgres_password,
		max_size=10,
		min_size=2
	)
	




