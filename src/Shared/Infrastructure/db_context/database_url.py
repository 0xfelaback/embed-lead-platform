from src.Shared.Infrastructure.db_context.context import settings


def sqlalchemy_migration_url(connection_string: str | None = None) -> str:
    """Return a sync postgresql:// URL for Alembic."""
    url = (connection_string or settings.DATABASE_CONNECTION_STRING).strip()
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://", 1)
    if url.startswith("postgresql://"):
        return url
    raise ValueError(
        "DATABASE_CONNECTION_STRING must use postgresql:// or postgresql+asyncpg://"
    )
