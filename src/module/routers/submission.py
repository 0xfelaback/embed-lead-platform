from typing import Any
from fastapi import APIRouter, Depends, status, HTTPException, Request, Response
from src.module.services.submission import SubmissionService, get_SubmissionService
from src.module.dtos.submission import SubmissionResponse, SubmissionRequest
from src.module.orchestrators.submission import (
    SubmissionOrchestrator,
    get_SubmissionOrchestrator,
)
from src.Shared.exceptions import (
    InternalServerError,
    NotFoundError,
    DatabaseError,
)
from src.Shared.Infrastructure.redis import redis_client
from src.main import logger
from sys import getsizeof

router = APIRouter(prefix="", tags=["Submissions"])


@router.options(
    "/v1/submissions",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="CORS preflight for submissions endpoint",
    description="Handles CORS preflight requests for the submissions endpoint to allow cross-origin requests from embedded widgets.",
)
async def submission_cors_preflight(request: Request):
    origin = request.headers.get("Origin", "*")  # pyright: ignore[reportUnusedVariable]
    request_method = request.headers.get(  # type: ignore
        "Access-Control-Request-Method", "POST"
    )
    request_headers = request.headers.get(  # type: ignore
        "Access-Control-Request-Headers", ""
    )

    logger.info(
        f"CORS preflight request from origin: {origin}, method: {request_method}"
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
        headers={
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Max-Age": "86400",
            "Access-Control-Allow-Credentials": "false",
        },
    )


@router.post(
    "/v1/submissions",
    response_model=SubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a submission",
    description="Creates a new submission for a widget from embedded form data.",
)
async def submission_ingestion(
    payload: SubmissionRequest,
    response: Response,
    request: Request,
    submission_orchestrator: SubmissionOrchestrator = Depends(
        get_SubmissionOrchestrator
    ),
    submission_service: SubmissionService = Depends(get_SubmissionService),
):
    """
    Public endpoint for creating submissions from embedded widgets.

    This endpoint is called by the widget JavaScript when users submit forms.
    It extracts client information (IP, user agent) and creates a submission record.
    """
    try:
        client_ip: str = request.client.host if request.client else "unknown"
        redis_key = f"widget-{payload.widget_id}: client-{client_ip}"
        current_requests = await redis_client.incr(redis_key)
        if current_requests == 1:
            await redis_client.expire(redis_key, 60)
        if current_requests > 5:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded for this resource. Try again in a minute.",
            )

        logger.info(f"Submission ingestion started for widget: {payload.widget_id}")
        geo_data: dict[str, Any] | None = submission_service.get_ip_location(client_ip)
        user_agent = request.headers.get("user-agent", "unknown")
        origin = request.headers.get("Origin", "*")

        logger.info(
            f"Client info - IP: {client_ip}, Origin: {origin}, User-Agent: {user_agent[:50]}..."
        )

        if getsizeof(payload) > 100 * 1024:
            logger.warning(
                f"Payload too large for widget {payload.widget_id}: {getsizeof(payload)} bytes"
            )
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="The request payload is larger than the limit of 100KB",
            )

        logger.info(
            f"Payload validation passed, starting workflow for widget: {payload.widget_id}"
        )

        response_data = await submission_orchestrator.create_submission_workflow(
            widget_id=payload.widget_id,
            payload=payload.form_data,
            client_ip=client_ip,
            user_agent=user_agent,
            geo_data=geo_data if geo_data is not None else {},
            origin=origin,
        )

        logger.info(
            f"Submission ingestion completed successfully for widget: {payload.widget_id}, submission: {response_data.id}"
        )

        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Cache-Control"] = "public, max-age=60"

        return response_data

    except (NotFoundError, DatabaseError) as e:
        raise
    except Exception as e:
        logger.error(f"Submission ingestion failed: {str(e)}")
        raise InternalServerError(
            message="An unexpected error occurred during submission ingestion",
            context="submission_ingestion",
            details={"error": str(e)},
        )
