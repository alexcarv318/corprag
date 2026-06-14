from psycopg_pool import ConnectionPool

from corporate_rag.settings import DatabaseSettings


def create_database_pool(settings: DatabaseSettings) -> ConnectionPool:
    pool = ConnectionPool(
        conninfo=settings.database_url,
        min_size=settings.database_pool_min_size,
        max_size=settings.database_pool_max_size,
        open=False,
    )
    pool.open(wait=True)
    return pool
