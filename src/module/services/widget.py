from uuid import UUID
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.Shared.exceptions import ConflictError, NotFoundError
from src.Shared.Infrastructure.db_context.context import settings
from src.Shared.Infrastructure.db_context.config import get_db
from src.main import logger
from src.module.schemas import Widget
from src.module.schemas.widget import WidgetType
from src.module.repositories.widget import WidgetRepository
from typing import Any, List, Optional
from jwt import decode  # type: ignore
from fastapi import Depends
from aiofiles import open
import os


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

    async def get_widget_loader_script(self) -> str:
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            script_path = os.path.join(current_dir, "widget_loader_script.js")

            js_script_string = None
            async with open(script_path, "r", encoding="utf-8") as file:
                js_script_string = await file.read()
            modified_js = js_script_string.replace("__BASE_URL__", settings.BASE_URL)

            return modified_js
        except Exception as e:
            logger.error(f"Widget loader script delivery workflow failed: {str(e)}")
            raise ConflictError(
                message="Failed to generate widget loader script",
                context="widget_loader_script",
                details={"error": str(e)},
            )

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
        widget = await self.widget_repository.get_by_id(widget_id)
        return widget

    async def get_public_widget_config(self, widget_id: UUID) -> Widget:
        widget = await self.widget_repository.get_by_id(widget_id)

        if not widget.is_active:
            logger.warning(f"Public config requested for inactive widget: {widget_id}")
            raise NotFoundError(
                message="Widget not found",
                context="public_widget_config",
                details={"widget_id": str(widget_id)},
            )

        return widget

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
