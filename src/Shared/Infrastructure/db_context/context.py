from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


class Settings(BaseSettings):
    DATABASE_CONNECTION_STRING: str = Field(default=...)
    POSTGRES_USER: str = Field(default=...)
    POSTGRES_PASSWORD: str = Field(default=...)
    POSTGRES_DB: str = Field(default=...)
    JWT_SECRET: str = Field(default=...)

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()

_engine = None
_session_local = None


def _async_database_url(connection_string: str) -> str:
    if connection_string.startswith("postgresql+asyncpg://"):
        return connection_string
    if connection_string.startswith("postgresql://"):
        return connection_string.replace("postgresql://", "postgresql+asyncpg://", 1)
    return connection_string


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            _async_database_url(settings.DATABASE_CONNECTION_STRING),
            connect_args={"timeout": 15},
            pool_pre_ping=True,
            pool_recycle=1800,
        )
    return _engine


def get_session_local():
    global _session_local
    if _session_local is None:
        _session_local = async_sessionmaker(
            autoflush=False,
            bind=get_engine(),
            expire_on_commit=False,
            class_=AsyncSession,
        )
    return _session_local


class _LazySessionLocal:
    def __call__(self, *args, **kwargs):  # type: ignore
        return get_session_local()(*args, **kwargs)


sessionLocal = _LazySessionLocal()
