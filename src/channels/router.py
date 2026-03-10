from typing import Optional

from fastapi import APIRouter, Body, Depends, Query

from src.auth.constants import (
    PERMISSION_DELETE_CHANNEL,
    PERMISSION_EDIT_CHANNEL,
    PERMISSION_READ_CHANNEL,
    PERMISSION_WRITE_CHANNEL,
)
from src.auth.dependencies import require_permission
from src.channels import service as channel_service
from src.channels.config import channels_settings
from src.channels.dependencies import validate_table
from src.channels.exceptions import ChannelCodeMismatchError
from src.channels.schemas import ChannelPatch, ChannelWrite

TABLES = channels_settings.DYNAMODB_TABLES

router = APIRouter(tags=["Channels"])


# ════════════════════════════════════════════════════════════════════════════
# GET  /channels  – paginated list
# ════════════════════════════════════════════════════════════════════════════


@router.get(
    "/channels",
    summary="List all channels (paginated)",
    dependencies=[Depends(require_permission(PERMISSION_READ_CHANNEL))],
)
def list_channels(
    table: Optional[str] = Query(default=None, description="Filter by table name.", enum=TABLES),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page (1–100)"),
    last_evaluated_key: Optional[str] = Query(
        default=None,
        description="Pagination token from a previous response (`next_page_token`). JSON-encoded.",
    ),
):
    """
    Returns a paginated list of channel items.

    - **table** – restrict to one DynamoDB table (optional).
    - **limit** – page size, 1–100 (default 20).
    - **last_evaluated_key** – paste the `next_page_token` from the previous response to get the next page.
    """
    return channel_service.list_channels(
        table=table,
        limit=limit,
        last_evaluated_key=last_evaluated_key,
    )


# ════════════════════════════════════════════════════════════════════════════
# GET  /channels/{channel_code}
# ════════════════════════════════════════════════════════════════════════════


@router.get(
    "/channels/{channel_code}",
    summary="Get a channel by ChannelCode",
    dependencies=[Depends(require_permission(PERMISSION_READ_CHANNEL))],
)
def get_channel(
    channel_code: str,
    table: Optional[str] = Query(default=None, description="Narrow search to one table.", enum=TABLES),
):
    """
    Fetches the item whose **id** matches *channel_code*.
    Supply **table** to skip scanning other tables (faster).
    """
    return channel_service.get_channel(channel_code, table=table)


# ════════════════════════════════════════════════════════════════════════════
# POST  /channels  – create
# ════════════════════════════════════════════════════════════════════════════


@router.post(
    "/channels",
    summary="Create a new channel",
    status_code=201,
)
def create_channel(
    payload: ChannelWrite = Body(
        openapi_examples={
            "TESTService-A channel": {
                "summary": "Standard TESTService-A channel",
                "value": {
                    "_table": "test-table",
                    "ChannelCode": "UST59FOXWEATHER",
                    "TVorRadio": "true",
                    "Label": "nattvnormal",
                    "Service": "TESTService-A",
                    "URLs": ["http://185.45.98.43:8080/hls/UST59FOXWEATHER.m3u8"],
                },
            }
        }
    ),
    user: dict = Depends(require_permission(PERMISSION_WRITE_CHANNEL)),
):
    """
    Creates a new channel item in DynamoDB.

    **Required fields:**
    - `_table` — target DynamoDB table
    - `ChannelCode` — unique identifier (stored as `id`)
    - `URLs` — list with at least one URL

    **Optional:** `Client`, `TVorRadio`, `Project`, `Service`

    Returns **409 Conflict** if a channel with the same ChannelCode already exists.
    """
    validate_table(payload.table)
    return channel_service.create_channel(payload, user)


# ════════════════════════════════════════════════════════════════════════════
# PUT  /channels/{channel_code}  – full replace
# ════════════════════════════════════════════════════════════════════════════


@router.put(
    "/channels/{channel_code}",
    summary="Fully replace a channel",
)
def replace_channel(
    channel_code: str,
    payload: ChannelWrite = Body(
        openapi_examples={
            "Full replace": {
                "summary": "Replace all fields",
                "value": {
                    "_table": "test-table",
                    "ChannelCode": "UST59FOXWEATHER",
                    "TVorRadio": "true",
                    "Label": "nattvnormal",
                    "Client": "SomeClient",
                    "Service": "TESTService-A",
                    "URLs": ["http://185.45.98.43:8080/hls/UST59FOXWEATHER.m3u8"],
                },
            }
        }
    ),
    user: dict = Depends(require_permission(PERMISSION_EDIT_CHANNEL)),
):
    """
    **Full replacement** — all fields are overwritten with what you provide.

    **Required fields:**
    - `_table` — target DynamoDB table
    - `ChannelCode` — must match the path parameter
    - `URLs` — list with at least one URL

    Returns **404** if the channel does not exist.
    Returns **400** if `ChannelCode` in the body does not match the URL.
    """
    if payload.ChannelCode != channel_code:
        raise ChannelCodeMismatchError(body_code=payload.ChannelCode, path_code=channel_code)
    validate_table(payload.table)
    return channel_service.replace_channel(channel_code, payload, user)


# ════════════════════════════════════════════════════════════════════════════
# PATCH  /channels/{channel_code}  – partial update
# ════════════════════════════════════════════════════════════════════════════


@router.patch(
    "/channels/{channel_code}",
    summary="Partially update a channel",
)
def patch_channel(
    channel_code: str,
    payload: ChannelPatch = Body(
        openapi_examples={
            "Partial update": {
                "summary": "Update service and label only",
                "value": {
                    "_table": "test-table",
                    "ChannelCode": "UST59FOXWEATHER",
                    "Label": "nattvnormal_updated",
                    "URLs": ["http://185.45.98.43:8080/hls/UST59FOXWEATHER_updated.m3u8"],
                },
            }
        }
    ),
    user: dict = Depends(require_permission(PERMISSION_EDIT_CHANNEL)),
):
    """
    **Partial update** — only the fields you supply are changed; omitted fields keep their existing values.

    **Required fields:**
    - `_table` — target DynamoDB table
    - `ChannelCode` — must match the path parameter *(cannot be changed)*
    - `URLs` — list with at least one URL (always required to keep the item valid)

    `ChannelCode` (`id`) is the partition key and `Service` is the sort key —
    **neither can be changed**. Omit `Service` from PATCH requests; it is ignored.
    """
    if payload.ChannelCode != channel_code:
        raise ChannelCodeMismatchError(body_code=payload.ChannelCode, path_code=channel_code)
    validate_table(payload.table)
    return channel_service.patch_channel(channel_code, payload, user)


# ════════════════════════════════════════════════════════════════════════════
# DELETE  /channels/{channel_code}
# ════════════════════════════════════════════════════════════════════════════


@router.delete(
    "/channels/{channel_code}",
    summary="Delete a channel",
)
def delete_channel(
    channel_code: str,
    table: str = Query(..., description="Target DynamoDB table (required).", enum=TABLES),
    user: dict = Depends(require_permission(PERMISSION_DELETE_CHANNEL)),
):
    """
    Deletes the channel item identified by *channel_code*.

    **Required query parameter:**
    - `table` — the DynamoDB table that holds the item

    Returns **404** if the channel does not exist.
    """
    validate_table(table)
    return channel_service.delete_channel(channel_code, table, user)
