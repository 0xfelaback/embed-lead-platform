from uuid import UUID
from typing import Any
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.main import logger
from src.module.schemas import Submission
from src.module.repositories.submission import SubmissionRepository
from src.module.repositories.widget import WidgetRepository
from src.Shared.Infrastructure.db_context.config import get_db
from src.Shared.exceptions import NotFoundError
from src.module.schemas.submission import SubmissionStatus


class SubmissionService:
    """
    Service handling submission-related business logic.

    This service encapsulates submission creation, validation, and retrieval
    with proper error handling and business rules.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.submission_repository = SubmissionRepository(session)
        self.widget_repository = WidgetRepository(session)

    async def create_submission(
        self,
        widget_id: UUID,
        payload: dict[str, Any],
        client_ip: str,
        user_agent: str,
        geo_data: dict[str, Any],
    ) -> Submission:
        widget = await self.widget_repository.get_by_id(widget_id)
        if not widget.is_active:
            logger.warning(f"Attempted submission to inactive widget: {widget_id}")
            raise NotFoundError(
                message="Widget is not active",
                context="submission_creation",
                details={"widget_id": str(widget_id)},
            )

        submission = await self.submission_repository.create(
            widget_id=widget_id,
            tenant_id=widget.tenant_id,
            payload=payload,
            client_ip=client_ip,
            user_agent=user_agent,
            geo_data=geo_data,
            status=SubmissionStatus.SUCCESS,
        )

        logger.info(f"Submission created successfully: {submission.id}")
        return submission

    async def get_submission_by_id(self, submission_id: UUID) -> Submission:
        return await self.submission_repository.get_by_id(submission_id)

    async def get_submissions_by_widget(
        self, widget_id: UUID, page: int = 1, limit: int = 20
    ) -> tuple[list[Submission], int]:
        return await self.submission_repository.get_by_widget_id(widget_id, page, limit)

    async def get_submissions_by_tenant(
        self, tenant_id: UUID, page: int = 1, limit: int = 20
    ) -> tuple[list[Submission], int]:
        return await self.submission_repository.get_by_tenant_id(tenant_id, page, limit)


def get_SubmissionService(
    session: AsyncSession = Depends(get_db),
) -> SubmissionService:
    return SubmissionService(session=session)
