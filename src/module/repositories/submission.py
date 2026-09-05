import uuid
from typing import Any, Dict
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from src.main import logger
from src.module.schemas import Submission
from src.Shared.exceptions import NotFoundError, DatabaseError
from src.module.schemas.submission import SubmissionStatus


class SubmissionRepository:
    """
    Repository for Submission entity with multi-tenancy support.

    This repository provides CRUD operations for submissions while ensuring
    proper data isolation within tenant scope and handling persistence layer operations.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        widget_id: uuid.UUID,
        tenant_id: uuid.UUID,
        payload: Dict[str, Any],
        client_ip: str,
        user_agent: str,
        geo_data: dict[str, Any],
        status: SubmissionStatus,
    ) -> Submission:
        try:
            new_submission = Submission(
                id=uuid.uuid4(),
                widget_id=widget_id,
                tenant_id=tenant_id,
                payload=payload,
                client_ip=client_ip,
                user_agent=user_agent,
                geo_data=geo_data,
                status=status,
                created_at=datetime.now(timezone.utc),
            )
            self.session.add(new_submission)
            await self.session.commit()
            await self.session.refresh(new_submission)

            logger.info(
                f"Created new submission with id: {new_submission.id} for widget: {widget_id}"
            )
            return new_submission

        except SQLAlchemyError as e:
            logger.error(f"Failed to create submission: {str(e)}")
            await self.session.rollback()
            raise DatabaseError(
                message="Failed to create submission in database",
                context="submission_creation",
                details={
                    "widget_id": str(widget_id),
                    "tenant_id": str(tenant_id),
                    "error": str(e),
                },
            )

    async def get_by_id(self, submission_id: uuid.UUID) -> Submission:
        try:
            result = await self.session.execute(
                select(Submission).where(Submission.id == submission_id)
            )
            submission = result.scalar_one_or_none()

            if submission:
                logger.info(f"Retrieved submission by id: {submission_id}")
                return submission
            else:
                logger.debug(f"Submission not found with id: {submission_id}")
                raise NotFoundError(
                    message="Submission not found",
                    context="submission_retrieval",
                    details={"submission_id": str(submission_id)},
                )

        except NotFoundError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Failed to retrieve submission by id: {str(e)}")
            raise DatabaseError(
                message="Failed to retrieve submission from database",
                context="submission_retrieval",
                details={"submission_id": str(submission_id), "error": str(e)},
            )

    async def get_by_widget_id(
        self, widget_id: uuid.UUID, page: int = 1, limit: int = 20
    ) -> tuple[list[Submission], int]:
        try:
            count_query = select(Submission).where(Submission.widget_id == widget_id)
            count_result = await self.session.execute(count_query)
            total_count = len(count_result.scalars().all())

            offset = (page - 1) * limit
            query = (
                select(Submission)
                .where(Submission.widget_id == widget_id)
                .order_by(Submission.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            result = await self.session.execute(query)
            submissions = result.scalars().all()

            logger.info(
                f"Retrieved {len(submissions)} submissions for widget: {widget_id} (page {page})"
            )
            return list(submissions), total_count

        except SQLAlchemyError as e:
            logger.error(f"Failed to retrieve submissions by widget id: {str(e)}")
            raise DatabaseError(
                message="Failed to retrieve submissions from database",
                context="submission_retrieval",
                details={"widget_id": str(widget_id), "error": str(e)},
            )

    async def get_by_tenant_id(
        self, tenant_id: uuid.UUID, page: int = 1, limit: int = 20
    ) -> tuple[list[Submission], int]:
        try:
            count_query = select(Submission).where(Submission.tenant_id == tenant_id)
            count_result = await self.session.execute(count_query)
            total_count = len(count_result.scalars().all())

            offset = (page - 1) * limit
            query = (
                select(Submission)
                .where(Submission.tenant_id == tenant_id)
                .order_by(Submission.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            result = await self.session.execute(query)
            submissions = result.scalars().all()

            logger.info(
                f"Retrieved {len(submissions)} submissions for tenant: {tenant_id} (page {page})"
            )
            return list(submissions), total_count

        except SQLAlchemyError as e:
            logger.error(f"Failed to retrieve submissions by tenant id: {str(e)}")
            raise DatabaseError(
                message="Failed to retrieve submissions from database",
                context="submission_retrieval",
                details={"tenant_id": str(tenant_id), "error": str(e)},
            )
