from typing import Optional

from fastapi import APIRouter, Depends, Query

from src.activity_logs import service as activity_log_service
from src.auth.constants import PERMISSION_READ_CHANNEL
from src.auth.dependencies import require_permission

router = APIRouter(tags=["Activity Logs"])


@router.get(
    "/activity-logs",
    summary="List activity logs (paginated)",
    dependencies=[Depends(require_permission(PERMISSION_READ_CHANNEL))],
)
def list_activity_logs(
    limit: int = Query(default=20, ge=1, le=100, description="Items per page (1-100)."),
    last_evaluated_key: Optional[str] = Query(
        default=None,
        description="Pagination token from a previous response (`next_page_token`). JSON-encoded.",
    ),
):
    return activity_log_service.list_activity_logs(
        limit=limit,
        last_evaluated_key=last_evaluated_key,
    )


@router.get(
    "/activity-logs/search",
    summary="Search activity logs by keyword",
    dependencies=[Depends(require_permission(PERMISSION_READ_CHANNEL))],
)
def search_activity_logs(
    keyword: str = Query(..., min_length=1, description="Keyword to match (email, channel code, service, etc.)."),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page (1-100)."),
    last_evaluated_key: Optional[str] = Query(
        default=None,
        description="Pagination token from a previous response (`next_page_token`). JSON-encoded.",
    ),
):
    return activity_log_service.search_activity_logs(
        keyword=keyword,
        limit=limit,
        last_evaluated_key=last_evaluated_key,
    )
