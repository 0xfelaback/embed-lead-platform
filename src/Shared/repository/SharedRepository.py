from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from src.main import logger
from src.Shared.Infrastructure.db_context.config import get_db


class SharedRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def check_database_availability(self) -> bool:
        """Check if the database is reachable and available."""
        try:
            result = await self.session.execute(text("SELECT 1"))
            result.scalar()
            logger.info("Database availability check passed")
            return True
        except Exception as e:
            logger.error(f"Database availability check failed: {str(e)}")
            return False


def get_SharedRepository(session: AsyncSession = Depends(get_db)) -> SharedRepository:
    return SharedRepository(session)
