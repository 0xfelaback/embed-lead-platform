from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from .context import sessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with sessionLocal() as database:
        yield database
