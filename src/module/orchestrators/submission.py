from uuid import UUID
from typing import Any, Optional
from fastapi import Depends
from src.module.dtos.submission import SubmissionResponse
from src.Shared.exceptions import (
    NotFoundError,
    InternalServerError,
    DatabaseError,
)
from src.main import logger
from src.module.services.submission import SubmissionService, get_SubmissionService


class SubmissionOrchestrator:
    """
    Orchestrator for submission-related workflows.

    This class coordinates the creation and management of submissions,
    handling the business logic flow between services and repositories.
    """

    def __init__(self, submission_service: SubmissionService):
        self.submission_service = submission_service

    async def create_submission_workflow(
        self,
        widget_id: UUID,
        payload: dict[str, Any],
        client_ip: str,
        user_agent: str,
        geo_data: Optional[dict[str, Any]] = None,
    ) -> SubmissionResponse:
        try:
            logger.info(
                f"Starting submission creation workflow for widget: {widget_id}"
            )

            submission = await self.submission_service.create_submission(
                widget_id=widget_id,
                payload=payload,
                client_ip=client_ip,
                user_agent=user_agent,
                geo_data=geo_data or {},
            )

            response_data = SubmissionResponse.model_validate(
                {
                    "id": submission.id,
                    "widget_id": submission.widget_id,
                    "tenant_id": submission.tenant_id,
                    "payload": submission.payload,
                    "client_ip": str(submission.client_ip),
                    "geo_data": submission.geo_data,
                    "user_agent": submission.user_agent,
                    "status": submission.status,
                    "created_at": submission.created_at,
                }
            )

            logger.info(
                f"Submission creation workflow completed successfully: {submission.id}"
            )
            return response_data

        except (NotFoundError, DatabaseError):
            raise
        except Exception as e:
            logger.error(f"Submission creation workflow failed: {str(e)}")
            raise InternalServerError(
                message="Submission creation failed",
                context="submission_creation",
                details={"error": str(e)},
            )

    async def get_submission_workflow(self, submission_id: UUID) -> SubmissionResponse:
        try:
            logger.info(f"Starting submission retrieval workflow: {submission_id}")

            submission = await self.submission_service.get_submission_by_id(
                submission_id
            )

            response_data = SubmissionResponse.model_validate(
                {
                    "id": submission.id,
                    "widget_id": submission.widget_id,
                    "tenant_id": submission.tenant_id,
                    "payload": submission.payload,
                    "client_ip": submission.client_ip,
                    "geo_data": submission.geo_data,
                    "user_agent": submission.user_agent,
                    "created_at": submission.created_at,
                }
            )

            logger.info(f"Submission retrieval workflow completed: {submission_id}")
            return response_data

        except (NotFoundError, DatabaseError):
            raise
        except Exception as e:
            logger.error(f"Submission retrieval workflow failed: {str(e)}")
            raise InternalServerError(
                message="Submission retrieval failed",
                context="submission_retrieval",
                details={"error": str(e)},
            )

    async def get_submissions_by_widget_workflow(
        self, widget_id: UUID, page: int = 1, limit: int = 20
    ) -> dict[str, Any]:
        try:
            logger.info(
                f"Starting widget submissions retrieval workflow for widget: {widget_id} "
                f"(page {page}, limit {limit})"
            )

            submissions, total_count = (
                await self.submission_service.get_submissions_by_widget(
                    widget_id=widget_id,
                    page=page,
                    limit=limit,
                )
            )

            total_pages = (total_count + limit - 1) // limit if total_count > 0 else 0

            response_data: dict[str, Any] = {
                "data": [
                    SubmissionResponse.model_validate(
                        {
                            "id": submission.id,
                            "widget_id": submission.widget_id,
                            "tenant_id": submission.tenant_id,
                            "payload": submission.payload,
                            "client_ip": submission.client_ip,
                            "geo_data": submission.geo_data,
                            "user_agent": submission.user_agent,
                            "created_at": submission.created_at,
                        }
                    )
                    for submission in submissions
                ],
                "pagination": {
                    "current_page": page,
                    "per_page": limit,
                    "total_records": total_count,
                    "total_pages": total_pages,
                },
            }

            logger.info(
                f"Widget submissions retrieval workflow completed: {len(submissions)} submissions, page {page}"
            )
            return response_data

        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Widget submissions retrieval workflow failed: {str(e)}")
            raise InternalServerError(
                message="Widget submissions retrieval failed",
                context="widget_submissions_retrieval",
                details={"error": str(e)},
            )


def get_SubmissionOrchestrator(
    submission_service: SubmissionService = Depends(get_SubmissionService),
) -> SubmissionOrchestrator:
    return SubmissionOrchestrator(submission_service)
