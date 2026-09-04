from fastapi import APIRouter, Depends, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uuid
from src.module.dtos import (
    SingleWidgetListItemResponse,
    WidgetCreateRequest,
    WidgetCreateResponse,
    WidgetListResponse,
    WidgetUpdateRequest,
)
from src.module.service import (
    AuthService,
    get_AuthService,
)
from src.module.schemas import Tenant
from src.module.orchestrator import WidgetOrchestrator, get_WidgetOrchestrator
from src.Shared.exceptions import (
    ValidationError,
    InternalServerError,
    UnauthorizedError,
    NotFoundError,
    ResourceAccessDeniedError,
)
from src.main import logger

router = APIRouter(prefix="", tags=["Widgets"])

security = HTTPBearer()


async def get_current_tenant(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_AuthService),
) -> Tenant:
    """Dependency to get current authenticated tenant."""
    return await auth_service.get_current_tenant(credentials)


@router.post(
    "/api/v1/widgets",
    response_model=WidgetCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new widget",
    description="Creates a new widget for the authenticated tenant with the specified configuration.",
)
async def create_widget(
    widget_data: WidgetCreateRequest,
    tenant: Tenant = Depends(get_current_tenant),
    widget_orchestrator: WidgetOrchestrator = Depends(get_WidgetOrchestrator),
):
    try:
        response_data = await widget_orchestrator.create_widget_workflow(
            tenant_id=tenant.id,
            widget_type=widget_data.type,
            title=widget_data.title,
            settings=widget_data.settings.model_dump(),
        )
        response_data["tenant_id"] = tenant.id

        return WidgetCreateResponse(**response_data)

    except UnauthorizedError as e:
        logger.warning(f"Widget creation unauthorized: {str(e)}")
        raise UnauthorizedError(
            message="Invalid or missing authentication token",
            context="widget_creation",
        )
    except ValueError as e:
        logger.error(f"Widget creation validation error: {str(e)}")
        raise ValidationError(
            message=str(e),
            context="widget_creation",
            details={"error_type": "validation_error"},
        )
    except Exception as e:
        logger.error(f"Widget creation failed: {str(e)}")
        raise InternalServerError(
            message="An unexpected error occurred during widget creation",
            context="widget_creation",
            details={"error": str(e)},
        )


@router.get(
    "/api/v1/widgets",
    response_model=WidgetListResponse,
    summary="List all widgets for the authenticated tenant",
    description="Retrieves a paginated list of widgets belonging to the authenticated tenant.",
)
async def list_widgets(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: str = Query(
        None,
        pattern="^(active|inactive)?$",
        description="Filter by status: active or inactive",
    ),
    tenant: Tenant = Depends(get_current_tenant),
    widget_orchestrator: WidgetOrchestrator = Depends(get_WidgetOrchestrator),
):
    try:
        response_data = await widget_orchestrator.list_widgets_workflow(
            tenant_id=tenant.id,
            page=page,
            limit=limit,
            status_filter=status_filter,
        )
        return WidgetListResponse(**response_data)

    except UnauthorizedError as e:
        logger.warning(f"Widget list unauthorized: {str(e)}")
        raise UnauthorizedError(
            message="Invalid or missing authentication token",
            context="widget_list",
        )
    except ValueError as e:
        logger.error(f"Widget list validation error: {str(e)}")
        raise ValidationError(
            message=str(e),
            context="widget_list",
            details={"error_type": "validation_error"},
        )
    except Exception as e:
        logger.error(f"Widget list failed: {str(e)}")
        raise InternalServerError(
            message="An unexpected error occurred while retrieving widgets",
            context="widget_list",
            details={"error": str(e)},
        )


@router.get(
    "/api/v1/widget",
    response_model=WidgetCreateResponse,
    summary="Get a specific widget by ID",
    description="Retrieves a specific widget by ID if it belongs to the authenticated tenant.",
)
async def get_widget_details(
    widget_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    widget_orchestrator: WidgetOrchestrator = Depends(get_WidgetOrchestrator),
):
    try:
        belongs_to_tenant = await widget_orchestrator.widget_service.widget_repository.belongs_to_tenant(
            widget_id=widget_id,
            tenant_id=tenant.id,
        )

        if not belongs_to_tenant:
            logger.warning(
                f"Unauthorized widget access attempt: widget_id={widget_id}, tenant_id={tenant.id}"
            )
            raise ResourceAccessDeniedError(
                message="You do not have permission to access this widget",
                context="widget_retrieval",
                details={"widget_id": str(widget_id)},
            )

        response_data = await widget_orchestrator.get_widget_workflow(widget_id)
        return SingleWidgetListItemResponse(**response_data)

    except ResourceAccessDeniedError as e:
        logger.warning(f"Widget access denied: {str(e)}")
        raise
    except NotFoundError as e:
        logger.warning(f"Widget not found: {str(e)}")
        raise NotFoundError(
            message="Widget not found",
            context="widget_retrieval",
            details={"widget_id": str(widget_id)},
        )
    except UnauthorizedError as e:
        logger.warning(f"Widget retrieval unauthorized: {str(e)}")
        raise UnauthorizedError(
            message="Invalid or missing authentication token",
            context="widget_retrieval",
        )
    except ValueError as e:
        logger.error(f"Widget retrieval validation error: {str(e)}")
        raise ValidationError(
            message=str(e),
            context="widget_retrieval",
            details={"error_type": "validation_error"},
        )
    except Exception as e:
        logger.error(f"Widget retrieval failed: {str(e)}")
        raise InternalServerError(
            message="An unexpected error occurred while retrieving the widget",
            context="widget_retrieval",
            details={"error": str(e)},
        )


@router.delete(
    "/api/v1/widgets/{widget_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a widget",
    description="Performs a hard deletion of the specified widget if it belongs to the authenticated tenant.",
)
async def delete_widget(
    widget_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    widget_orchestrator: WidgetOrchestrator = Depends(get_WidgetOrchestrator),
):
    try:
        await widget_orchestrator.delete_widget_workflow(
            widget_id=widget_id,
            tenant_id=tenant.id,
        )
        return None

    except ValueError as e:
        if "not found" in str(e).lower() or "access denied" in str(e).lower():
            logger.warning(f"Widget deletion not found or access denied: {str(e)}")
            raise NotFoundError(
                message="Widget not found or belongs to another tenant",
                context="widget_deletion",
                details={"widget_id": str(widget_id)},
            )
        logger.error(f"Widget deletion validation error: {str(e)}")
        raise ValidationError(
            message=str(e),
            context="widget_deletion",
            details={"error_type": "validation_error"},
        )
    except Exception as e:
        logger.error(f"Widget deletion failed: {str(e)}")
        raise InternalServerError(
            message="An unexpected error occurred while deleting the widget",
            context="widget_deletion",
            details={"error": str(e)},
        )


@router.patch(
    "/api/v1/widgets/{widget_id}",
    response_model=WidgetCreateResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a widget",
    description="Performs a partial update of the specified widget if it belongs to the authenticated tenant.",
)
async def update_widget(
    widget_id: uuid.UUID,
    widget_data: WidgetUpdateRequest,
    tenant: Tenant = Depends(get_current_tenant),
    widget_orchestrator: WidgetOrchestrator = Depends(get_WidgetOrchestrator),
):
    try:
        response_data = await widget_orchestrator.update_widget_workflow(
            widget_id=widget_id,
            tenant_id=tenant.id,
            title=widget_data.title,
            is_active=widget_data.is_active,
            domain_whitelist=widget_data.domain_whitelist,
            settings=widget_data.settings.model_dump() if widget_data.settings else None,
        )
        return WidgetCreateResponse(**response_data)

    except ValueError as e:
        if "not found" in str(e).lower() or "access denied" in str(e).lower():
            logger.warning(f"Widget update not found or access denied: {str(e)}")
            raise NotFoundError(
                message="Widget not found or belongs to another tenant",
                context="widget_update",
                details={"widget_id": str(widget_id)},
            )
        logger.error(f"Widget update validation error: {str(e)}")
        raise ValidationError(
            message=str(e),
            context="widget_update",
            details={"error_type": "validation_error"},
        )
    except Exception as e:
        logger.error(f"Widget update failed: {str(e)}")
        raise InternalServerError(
            message="An unexpected error occurred while updating the widget",
            context="widget_update",
            details={"error": str(e)},
        )
