from fastapi import APIRouter
from fastapi import APIRouter, Depends, status, HTTPException, Request
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
from src.main import logger
from sys import getsizeof

router = APIRouter(prefix="", tags=["Submissions"])


@router.post(
    "/v1/submissions",
    response_model=SubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a submission",
    description="Creates a new submission for a widget from embedded form data.",
)
async def submission_ingestion(
    payload: SubmissionRequest,
    request: Request,
    submission_orchestrator: SubmissionOrchestrator = Depends(
        get_SubmissionOrchestrator
    ),
):
    """
    Public endpoint for creating submissions from embedded widgets.

    This endpoint is called by the widget JavaScript when users submit forms.
    It extracts client information (IP, user agent) and creates a submission record.
    """
    try:
        # Extract client information
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        if getsizeof(payload) > 100 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="The request payload is larger than the limit of 100KB",
            )

        response_data = await submission_orchestrator.create_submission_workflow(
            widget_id=payload.widget_id,
            payload=payload.form_data,
            client_ip=client_ip,
            user_agent=user_agent,
            geo_data={},
        )

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
