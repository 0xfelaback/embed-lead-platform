from uuid import UUID
from typing import Any
from fastapi import Depends
from requests import get as HttpGet, exceptions
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
        origin: str,
    ) -> Submission:
        logger.info(f"Service: Starting submission creation for widget: {widget_id}")

        logger.info(f"Service: Validating widget: {widget_id}")
        widget = await self.widget_repository.get_by_id(widget_id)
        
        if not widget.is_active:
            logger.warning(f"Attempted submission to inactive widget: {widget_id}")
            raise NotFoundError(
                message="Widget is not active",
                context="submission_creation",
                details={"widget_id": str(widget_id)},
            )

        logger.info(f"Service: Widget {widget_id} is active, proceeding with submission creation")

        logger.info(f"Service: Calling repository to create submission for widget: {widget_id}")
        submission = await self.submission_repository.create(
            widget_id=widget_id,
            tenant_id=widget.tenant_id,
            payload=payload,
            client_ip=client_ip,
            user_agent=user_agent,
            geo_data=geo_data,
            status=SubmissionStatus.SUCCESS,
            origin=origin,
        )

        logger.info(f"Service: Repository returned submission: {submission.id}")
        logger.info(f"Submission created successfully: {submission.id}")
        return submission

    async def get_submission_by_id(self, submission_id: UUID) -> Submission:
        logger.info(f"Service: Retrieving submission by id: {submission_id}")
        submission = await self.submission_repository.get_by_id(submission_id)
        logger.info(f"Service: Retrieved submission: {submission_id}")
        return submission

    async def get_submissions_by_widget(
        self, widget_id: UUID, page: int = 1, limit: int = 20
    ) -> tuple[list[Submission], int]:
        logger.info(f"Service: Retrieving submissions for widget: {widget_id} (page {page})")
        submissions, total_count = await self.submission_repository.get_by_widget_id(widget_id, page, limit)
        logger.info(f"Service: Retrieved {len(submissions)} submissions for widget: {widget_id}")
        return submissions, total_count

    async def get_submissions_by_tenant(
        self, tenant_id: UUID, page: int = 1, limit: int = 20
    ) -> tuple[list[Submission], int]:
        logger.info(f"Service: Retrieving submissions for tenant: {tenant_id} (page {page})")
        submissions, total_count = await self.submission_repository.get_by_tenant_id(tenant_id, page, limit)
        logger.info(f"Service: Retrieved {len(submissions)} submissions for tenant: {tenant_id}")
        return submissions, total_count

    def get_ip_location(self, client_ip: str) -> dict[str, Any] | None:
        logger.info(f"Service: Starting geolocation lookup for IP: {client_ip}")
        headers = {"User-Agent": "python-requests/2.0.0"}
        timeout = 5

        url_a = f"http://ip-api.com{client_ip}"
        try:
            logger.info(f"Service: Trying provider A (ip-api.com) for IP: {client_ip}")
            response_a = HttpGet(url_a, headers=headers, timeout=timeout)

            if response_a.status_code == 200:
                data_a = response_a.json()
                if data_a.get("status") == "success":
                    logger.info(f"Service: Successfully geolocated IP {client_ip} using ip-api.com")
                    return {
                        "provider": "ip-api.com",
                        "city": data_a.get("city"),
                        "region": data_a.get("regionName"),
                        "country": data_a.get("country"),
                        "raw": data_a,
                    }
                elif (
                    data_a.get("status") == "fail"
                    and data_a.get("message") == "private range"
                ):
                    logger.warning(
                        f"Private IP address {client_ip} range cannot be geolocated"
                    )
                    pass

        except exceptions.RequestException:
            logger.warning(f"Service: Provider A (ip-api.com) failed for IP: {client_ip}")
            pass

        url_b = f"https://ipapi.co/{client_ip}/json/"
        try:
            logger.info(f"Service: Trying provider B (ipapi.co) for IP: {client_ip}")
            response_b = HttpGet(url_b, headers=headers, timeout=timeout)
            if response_b.status_code == 200:
                data_b = response_b.json()
                if "error" not in data_b:
                    logger.info(f"Service: Successfully geolocated IP {client_ip} using ipapi.co")
                    return {
                        "provider": "ipapi.co",
                        "city": data_b.get("city"),
                        "region": data_b.get("region"),
                        "country": data_b.get("country_name"),
                        "raw": data_b,
                    }
                else:
                    logger.error(data_b.get("reason", "Provider B internal error"))
                    pass
            else:
                logger.error(
                    f"Both providers failed for {client_ip}. Provider B status: {response_b.status_code}"
                )
                pass

        except exceptions.RequestException as e:
            logger.error(
                f"Both providers failed for {client_ip}. Provider B error: {str(e)}"
            )
            pass

        logger.warning(f"Service: Could not geolocate IP: {client_ip}")
        return None


def get_SubmissionService(
    session: AsyncSession = Depends(get_db),
) -> SubmissionService:
    return SubmissionService(session=session)
