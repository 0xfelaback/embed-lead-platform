"""
RUN: uvicorn src.main:app --port 3001 --reload --loop asyncio
"""

from sys import stderr
from loguru import logger
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import FastAPI
from datetime import datetime

from src.Shared.repository.SharedRepository import SharedRepository
from src.Shared.Infrastructure.db_context.context import get_engine

current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log_filename = f"logs/{current_time}-log-embed-lead-platform.log"
logger.remove()

logger.add(
    log_filename,
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} | {message}",
    colorize=False,
    backtrace=True,
    diagnose=True,
    rotation="00:00",
    retention="7 days",
    compression="zip",
)

logger.add(
    stderr,
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | <level>{level: <8}</level> | {name}:{function}:{line} | {message}",
    colorize=True,
    backtrace=True,
    diagnose=True,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        engine = get_engine()
        async with AsyncSession(engine) as session:
            sharedrepository = SharedRepository(session)
            db_available = await sharedrepository.check_database_availability()
            if not db_available:
                logger.error("Database is not available. Application cannot start.")
                raise RuntimeError("Database is not available")
            logger.info("Database is available")
    except:
        pass
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health_check():
    logger.info("Health check endpoint called")
    return {"status": "ok"}
