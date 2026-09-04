import uuid
from typing import Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from src.main import logger
from src.module.schemas.widget import Widget, WidgetType
from src.Shared.exceptions import NotFoundError, ConflictError, DatabaseError


class WidgetRepository:
    """
    Repository for Widget entity with multi-tenancy support.

    This repository provides CRUD operations for widgets while ensuring
    proper data isolation within tenant scope.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        tenant_id: uuid.UUID,
        widget_type: WidgetType,
        title: str,
        settings: dict[str, Any],
    ) -> Widget:
        """
        Create a new widget for a tenant.

        Args:
            tenant_id: ID of the tenant owning this widget
            widget_type: Type of widget (signup, cta, popover)
            title: Display title for the widget
            settings: Widget configuration settings
        """
        try:
            new_widget = Widget(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                type=widget_type,
                title=title,
                settings=settings,
            )
            self.session.add(new_widget)
            await self.session.commit()
            await self.session.refresh(new_widget)

            logger.info(
                f"Created new widget with id: {new_widget.id} for tenant: {tenant_id}"
            )
            return new_widget

        except IntegrityError as e:
            logger.error(f"Widget creation constraint violation: {str(e)}")
            await self.session.rollback()
            raise ConflictError(
                message="Widget creation failed due to a constraint violation",
                context="widget_creation",
                details={"tenant_id": str(tenant_id), "error": str(e)},
            )
        except SQLAlchemyError as e:
            logger.error(f"Failed to create widget: {str(e)}")
            await self.session.rollback()
            raise DatabaseError(
                message="Failed to create widget in database",
                context="widget_creation",
                details={"tenant_id": str(tenant_id), "error": str(e)},
            )

    async def get_by_id(self, widget_id: uuid.UUID) -> Widget:
        try:
            result = await self.session.execute(
                select(Widget).where(Widget.id == widget_id)
            )
            widget = result.scalar_one_or_none()

            if widget:
                logger.info(f"Retrieved widget by id: {widget_id}")
                return widget
            else:
                logger.debug(f"Widget not found with id: {widget_id}")
                raise NotFoundError(
                    message="Widget not found",
                    context="widget_retrieval",
                    details={"widget_id": str(widget_id)},
                )

        except NotFoundError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Failed to retrieve widget by id: {str(e)}")
            raise DatabaseError(
                message="Failed to retrieve widget from database",
                context="widget_retrieval",
                details={"widget_id": str(widget_id), "error": str(e)},
            )

    async def get_by_tenant_id(
        self,
        tenant_id: uuid.UUID,
        page: int = 1,
        limit: int = 20,
        status_filter: Optional[str] = None,
    ) -> tuple[List[Widget], int]:
        """
        Retrieve widgets for a specific tenant with pagination and filtering.

        Returns:
            Tuple of (list of widgets, total count)
        """
        try:
            # Build base query
            query = select(Widget).where(Widget.tenant_id == tenant_id)

            if status_filter == "active":
                query = query.where(Widget.is_active == True)
            elif status_filter == "inactive":
                query = query.where(Widget.is_active == False)

            count_query = (
                select(func.count())
                .select_from(Widget)
                .where(Widget.tenant_id == tenant_id)
            )
            if status_filter == "active":
                count_query = count_query.where(Widget.is_active == True)
            elif status_filter == "inactive":
                count_query = count_query.where(Widget.is_active == False)

            total_result = await self.session.execute(count_query)
            total_count = total_result.scalar() or 0

            offset = (page - 1) * limit
            query = query.order_by(Widget.created_at.desc()).offset(offset).limit(limit)

            result = await self.session.execute(query)
            widgets = result.scalars().all()

            logger.info(
                f"Retrieved {len(widgets)} widgets for tenant: {tenant_id} "
                f"(page {page}, limit {limit}, total {total_count})"
            )
            return list(widgets), total_count

        except SQLAlchemyError as e:
            logger.error(f"Failed to retrieve widgets by tenant id: {str(e)}")
            raise DatabaseError(
                message="Failed to retrieve widgets from database",
                context="widget_list",
                details={"tenant_id": str(tenant_id), "error": str(e)},
            )

    async def update(
        self,
        widget_id: uuid.UUID,
        title: Optional[str] = None,
        settings: Optional[dict[str, Any]] = None,
        is_active: Optional[bool] = None,
        domain_whitelist: Optional[list[str]] = None,
    ) -> Widget:
        try:
            await self.get_by_id(widget_id)  # raises its errors internally.

            update_values = {}
            if title is not None:
                update_values["title"] = title
            if settings is not None:
                update_values["settings"] = settings
            if is_active is not None:
                update_values["is_active"] = is_active
            if domain_whitelist is not None:
                update_values["domain_whitelist"] = domain_whitelist

            if update_values:
                await self.session.execute(
                    update(Widget).where(Widget.id == widget_id).values(**update_values)
                )
                await self.session.commit()

            updated_widget = await self.get_by_id(widget_id)
            logger.info(f"Updated widget: {widget_id}")
            return updated_widget

        except NotFoundError:
            raise
        except IntegrityError as e:
            logger.error(f"Widget update constraint violation: {str(e)}")
            await self.session.rollback()
            raise ConflictError(
                message="Widget update failed due to a constraint violation",
                context="widget_update",
                details={"widget_id": str(widget_id), "error": str(e)},
            )
        except SQLAlchemyError as e:
            logger.error(f"Failed to update widget: {str(e)}")
            await self.session.rollback()
            raise DatabaseError(
                message="Failed to update widget in database",
                context="widget_update",
                details={"widget_id": str(widget_id), "error": str(e)},
            )

    async def delete(self, widget_id: uuid.UUID) -> bool:
        try:
            widget = await self.get_by_id(widget_id)
            widget.mark_widget_deleted()
            await self.session.commit()

            logger.info(f"Soft deleted widget: {widget_id}")
            return True

        except NotFoundError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Failed to delete widget: {str(e)}")
            await self.session.rollback()
            raise DatabaseError(
                message="Failed to delete widget from database",
                context="widget_deletion",
                details={"widget_id": str(widget_id), "error": str(e)},
            )

    async def exists_by_id(self, widget_id: uuid.UUID) -> bool:
        try:
            result = await self.session.execute(
                select(Widget.id).where(Widget.id == widget_id)
            )
            return result.scalar_one_or_none() is not None
        except SQLAlchemyError as e:
            logger.error(f"Failed to check widget existence by id: {str(e)}")
            return False

    async def belongs_to_tenant(
        self, widget_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> bool:
        """
        RLS enforced at application level 👀: anti-pattern
        """
        try:
            result = await self.session.execute(
                select(Widget.id).where(
                    Widget.id == widget_id, Widget.tenant_id == tenant_id
                )
            )
            return result.scalar_one_or_none() is not None
        except SQLAlchemyError as e:
            logger.error(f"Failed to check widget ownership: {str(e)}")
            return False
