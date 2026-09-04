from uuid import UUID
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.Shared.Infrastructure.db_context.context import settings
from src.Shared.Infrastructure.db_context.config import get_db
from src.main import logger
from src.module.schemas import Widget
from src.module.schemas.widget import WidgetType
from src.module.repositories.widget import WidgetRepository
from typing import Any, List, Optional
from jwt import decode  # type: ignore
from fastapi import Depends


class WidgetService:
    """
    Service handling widget-related business logic.

    This service encapsulates widget creation, validation, and embed snippet generation
    with proper error handling and business rules.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.widget_repository = WidgetRepository(session)

    def generate_embed_snippet(self, widget_id: UUID) -> str:
        api_base_url = settings.BASE_URL
        return f'<script src="{api_base_url}/widget.js?id={widget_id}"></script>'

    async def create_widget(
        self,
        tenant_id: UUID,
        widget_type: WidgetType,
        title: str,
        settings: dict[str, Any],
    ) -> Widget:
        widget = await self.widget_repository.create(
            tenant_id=tenant_id,
            widget_type=widget_type,
            title=title,
            settings=settings,
        )

        logger.info(f"Widget created successfully: {widget.id}")
        return widget

    async def get_widget_by_id(self, widget_id: UUID) -> Widget:
        return await self.widget_repository.get_by_id(widget_id)

    async def get_widgets_by_tenant(self, tenant_id: UUID) -> tuple[List[Widget], int]:
        return await self.widget_repository.get_by_tenant_id(tenant_id)

    async def get_widgets_paginated(
        self,
        tenant_id: UUID,
        page: int = 1,
        limit: int = 20,
        status_filter: Optional[str] = None,
    ) -> tuple[list[Widget], int]:
        limit = min(limit, 20)
        return await self.widget_repository.get_by_tenant_id(
            tenant_id, page, limit, status_filter
        )


def get_WidgetService(
    session: AsyncSession = Depends(get_db),
) -> WidgetService:
    return WidgetService(session=session)
