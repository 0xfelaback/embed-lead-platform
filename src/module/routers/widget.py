from fastapi import APIRouter, Depends, status, Query, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uuid
from src.module.services.widget import WidgetService, get_WidgetService
from src.module.dtos.widget import (
    SingleWidgetListItemResponse,
    PublicWidgetConfigResponse,
    WidgetCreateRequest,
    WidgetCreateResponse,
    WidgetListResponse,
    WidgetUpdateRequest,
)
from src.module.services.auth import (
    AuthService,
    get_AuthService,
)
from src.module.schemas import Tenant
from src.module.orchestrators.widget import WidgetOrchestrator, get_WidgetOrchestrator
from src.Shared.exceptions import (
    InternalServerError,
    NotFoundError,
    ResourceAccessDeniedError,
    ConflictError,
    DatabaseError,
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
            settings=widget_data.settings.model_dump(mode="json"),
        )
        return response_data

    except (ConflictError, DatabaseError, InternalServerError) as e:
        raise
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
        return response_data

    except (DatabaseError, InternalServerError) as e:
        raise
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
        response_data: SingleWidgetListItemResponse = (
            await widget_orchestrator.get_widget_workflow(widget_id, tenant.id)
        )
        return response_data

    except (
        ResourceAccessDeniedError,
        NotFoundError,
        DatabaseError,
        InternalServerError,
    ) as e:
        raise
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
    description="Performs a SOFT DELETE on the specified widget if it belongs to the authenticated tenant.",
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

    except (
        NotFoundError,
        ResourceAccessDeniedError,
        DatabaseError,
        InternalServerError,
    ) as e:
        raise
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
            settings=(
                widget_data.settings.model_dump(mode="json")
                if widget_data.settings
                else None
            ),
        )
        return WidgetCreateResponse(**response_data)

    except (
        NotFoundError,
        ResourceAccessDeniedError,
        ConflictError,
        DatabaseError,
        InternalServerError,
    ) as e:
        raise
    except Exception as e:
        logger.error(f"Widget update failed: {str(e)}")
        raise InternalServerError(
            message="An unexpected error occurred while updating the widget",
            context="widget_update",
            details={"error": str(e)},
        )


@router.get(
    "/v1/widget.js",
    summary="Get widget loader script",
    description="Returns the minified client loader script. The script reads its own src parameter (id=...), fetches the corresponding widget configuration JSON from the backend, renders the DOM elements inside the target page, and wires up submit events to the public submission route.",
)
async def get_widget_loader_script(
    id: uuid.UUID = Query(
        None, description="unique identifier for the widget"
    ),  # TODO: utilise the versioning correctly, the one required for cache-busting.
    widget_service: WidgetService = Depends(get_WidgetService),
):
    """
    Public endpoint for serving the widget JavaScript loader script.

    The script is heavily cached for performance (1 month) with the option
    to bust cache using the 'v' query parameter.
    """
    try:
        logger.info(f"Widget loader script requested (Id: {id})")
        loader_script = await widget_service.get_widget_loader_script()

        return Response(
            content=loader_script,
            media_type="application/javascript; charset=utf-8",
            headers={
                "Cache-Control": "public, max-age=2592000, stale-while-revalidate",
                "Access-Control-Allow-Origin": "*",
            },
        )
    except (InternalServerError, ConflictError) as e:
        raise
    except Exception as e:
        logger.error(f"Widget loader script delivery failed: {str(e)}")
        raise InternalServerError(
            message="An unexpected error occurred while delivering the widget loader script",
            context="widget_loader_script",
            details={"error": str(e)},
        )


@router.get(
    "/v1/widgets/{widget_id}/config",
    response_model=PublicWidgetConfigResponse,
    summary="Get public widget configuration",
    description="Returns widget configuration for the loader script. Public endpoint with CORS enabled and caching. Only contains necessary fields for widget rendering (id, title, settings).",
)
async def get_public_widget_config(
    widget_id: uuid.UUID,
    widget_service: WidgetService = Depends(get_WidgetService),
):
    """
    Public endpoint for widget configuration.

    This endpoint is called by the widget loader script to get the widget
    configuration needed to render the widget UI. It's public (no auth required)
    and only returns non-sensitive information.
    """
    try:
        logger.info(f"Public widget config requested: {widget_id}")
        widget = await widget_service.get_public_widget_config(widget_id)

        response_data = PublicWidgetConfigResponse.model_validate(
            {
                "id": widget.id,
                "title": widget.title,
                "settings": widget.settings,
            }
        )

        return Response(
            content=response_data.model_dump_json(),
            media_type="application/json",
            headers={
                "Cache-Control": "public, no-cache, max-age=600",  # TODO: how is the http 304 accounted for ?
                "Access-Control-Allow-Origin": "*",
            },
        )

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Public widget config retrieval failed: {str(e)}")
        raise InternalServerError(
            message="An unexpected error occurred while retrieving widget configuration",
            context="public_widget_config",
            details={"error": str(e)},
        )
