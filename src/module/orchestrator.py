from uuid import UUID
from typing import Dict, Any, Optional

from fastapi import Depends
from src.main import logger
from src.module.service import WidgetService, get_WidgetService
from src.module.schemas import WidgetType


class WidgetOrchestrator:
    """
    Orchestrator for widget-related workflows.

    This class coordinates the creation and management of widgets,
    handling the business logic flow between services and repositories.
    """

    def __init__(self, widget_service: WidgetService):
        self.widget_service = widget_service

    async def create_widget_workflow(
        self,
        tenant_id: UUID,
        widget_type: WidgetType,
        title: str,
        settings: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            logger.info(f"Starting widget creation workflow for tenant: {tenant_id}")
            widget = await self.widget_service.create_widget(
                tenant_id=tenant_id,
                widget_type=widget_type,
                title=title,
                settings=settings,
            )

            embed_snippet = self.widget_service.generate_embed_snippet(widget.id)

            response_data: dict[str, Any] = {
                "id": str(widget.id),
                "tenant_id": str(widget.tenant_id),
                "type": (
                    widget.type.value
                    if hasattr(widget.type, "value")
                    else str(widget.type)
                ),
                "title": widget.title,
                "settings": widget.settings,
                "embed_snippet": embed_snippet,
                "is_active": widget.is_active,
                "created_at": widget.created_at,
                "updated_at": widget.updated_at,
            }

            logger.info(f"Widget creation workflow completed successfully: {widget.id}")
            return response_data

        except Exception as e:
            logger.error(f"Widget creation workflow failed: {str(e)}")
            raise ValueError(f"Widget creation failed: {str(e)}")

    async def get_widget_workflow(self, widget_id: UUID) -> Dict[str, Any]:
        try:
            logger.info(f"Starting widget retrieval workflow: {widget_id}")
            widget = await self.widget_service.get_widget_by_id(widget_id)

            if not widget:
                raise ValueError(f"Widget not found: {widget_id}")

            embed_snippet = self.widget_service.generate_embed_snippet(widget.id)
            response_data: dict[str, Any] = {
                "id": str(widget.id),
                "tenant_id": str(widget.tenant_id),
                "type": (
                    widget.type.value
                    if hasattr(widget.type, "value")
                    else str(widget.type)
                ),
                "title": widget.title,
                "settings": widget.settings,
                "embed_snippet": embed_snippet,
                "is_active": widget.is_active,
                "created_at": widget.created_at,
                "updated_at": widget.updated_at,
            }

            logger.info(f"Widget retrieval workflow completed: {widget_id}")
            return response_data

        except Exception as e:
            logger.error(f"Widget retrieval workflow failed: {str(e)}")
            raise ValueError(f"Widget retrieval failed: {str(e)}")

    async def list_widgets_workflow(
        self,
        tenant_id: UUID,
        page: int = 1,
        limit: int = 20,
        status_filter: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Execute the widget list workflow with pagination.

        Args:
            status_filter: Filter by "active" or "inactive"

        Returns:
            Dictionary containing widget list and pagination metadata
        """
        try:
            logger.info(
                f"Starting widget list workflow for tenant: {tenant_id} "
                f"(page {page}, limit {limit}, status: {status_filter})"
            )

            widgets, total_count = await self.widget_service.get_widgets_paginated(
                tenant_id=tenant_id,
                page=page,
                limit=limit,
                status_filter=status_filter,
            )

            total_pages = (total_count + limit - 1) // limit if total_count > 0 else 0

            widget_items: list[dict[str, Any]] = [
                {
                    "id": str(widget.id),
                    "type": (
                        widget.type.value
                        if hasattr(widget.type, "value")
                        else str(widget.type)
                    ),
                    "title": widget.title,
                    "is_active": widget.is_active,
                    "created_at": widget.created_at,
                }
                for widget in widgets
            ]

            response_data: dict[str, Any] = {
                "data": widget_items,
                "pagination": {
                    "current_page": page,
                    "per_page": limit,
                    "total_records": total_count,
                    "total_pages": total_pages,
                },
            }

            logger.info(
                f"Widget list workflow completed: {len(widgets)} widgets, page {page}"
            )
            return response_data

        except Exception as e:
            logger.error(f"Widget list workflow failed: {str(e)}")
            raise ValueError(f"Widget list failed: {str(e)}")

    async def delete_widget_workflow(self, widget_id: UUID, tenant_id: UUID) -> bool:
        try:
            logger.info(
                f"Starting widget deletion workflow: widget_id={widget_id}, tenant_id={tenant_id}"
            )
            belongs_to_tenant = (
                await self.widget_service.widget_repository.belongs_to_tenant(
                    widget_id=widget_id,
                    tenant_id=tenant_id,
                )
            )

            if not belongs_to_tenant:
                logger.warning(
                    f"Widget deletion unauthorized: widget_id={widget_id}, tenant_id={tenant_id}"
                )
                raise ValueError("Widget not found or access denied")

            deleted = await self.widget_service.widget_repository.delete(widget_id)
            if not deleted:
                logger.error(f"Widget deletion failed: widget_id={widget_id}")
                raise ValueError("Failed to delete widget")

            logger.info(f"Widget deletion workflow completed: widget_id={widget_id}")
            return True

        except ValueError as e:
            logger.error(f"Widget deletion workflow validation error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Widget deletion workflow failed: {str(e)}")
            raise ValueError(f"Widget deletion failed: {str(e)}")

    async def update_widget_workflow(
        self,
        widget_id: UUID,
        tenant_id: UUID,
        title: Optional[str] = None,
        is_active: Optional[bool] = None,
        domain_whitelist: Optional[list[str]] = None,
        settings: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        try:
            logger.info(
                f"Starting widget update workflow: widget_id={widget_id}, tenant_id={tenant_id}"
            )

            belongs_to_tenant = (
                await self.widget_service.widget_repository.belongs_to_tenant(
                    widget_id=widget_id,
                    tenant_id=tenant_id,
                )
            )

            if not belongs_to_tenant:
                logger.warning(
                    f"Widget update unauthorized: widget_id={widget_id}, tenant_id={tenant_id}"
                )
                raise ValueError("Widget not found or access denied")

            settings_dict = settings if settings else None
            updated_widget = await self.widget_service.widget_repository.update(
                widget_id=widget_id,
                title=title,
                settings=settings_dict,
                is_active=is_active,
                domain_whitelist=domain_whitelist,
            )

            if not updated_widget:
                logger.error(f"Widget update failed: widget_id={widget_id}")
                raise ValueError("Failed to update widget")

            embed_snippet = self.widget_service.generate_embed_snippet(widget_id)
            response_data: dict[str, Any] = {
                "id": str(updated_widget.id),
                "tenant_id": str(updated_widget.tenant_id),
                "type": (
                    updated_widget.type.value
                    if hasattr(updated_widget.type, "value")
                    else str(updated_widget.type)
                ),
                "title": updated_widget.title,
                "settings": updated_widget.settings,
                "embed_snippet": embed_snippet,
                "is_active": updated_widget.is_active,
                "created_at": updated_widget.created_at,
                "updated_at": updated_widget.updated_at,
            }

            logger.info(f"Widget update workflow completed: widget_id={widget_id}")
            return response_data

        except ValueError as e:
            logger.error(f"Widget update workflow validation error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Widget update workflow failed: {str(e)}")
            raise ValueError(f"Widget update failed: {str(e)}")


def get_WidgetOrchestrator(
    widget_service: WidgetService = Depends(get_WidgetService),
) -> WidgetOrchestrator:
    return WidgetOrchestrator(widget_service)
