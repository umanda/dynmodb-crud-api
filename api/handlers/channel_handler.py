from __future__ import annotations

from typing import Optional

from fastapi import Body, HTTPException, Query

from config import ACTIVE_TABLES
from dto import (
    ChannelCreateRequest,
    ChannelPatchRequest,
    ChannelReplaceRequest,
    ChannelResponse,
    PaginatedChannelResponse,
)
from services.interfaces import ChannelServiceInterface


class ChannelHandler:
    """
    HTTP handler — translates FastAPI request parameters into service calls
    and returns HTTP responses. Contains no business logic.
    """

    def __init__(self, service: ChannelServiceInterface) -> None:
        self._service = service

    # ── GET /channels ─────────────────────────────────────────────────────────

    def list_channels(
        self,
        table: Optional[str] = Query(default=None, enum=ACTIVE_TABLES,
                                     description="Filter by table name."),
        limit: int = Query(default=20, ge=1, le=100, description="Items per page (1–100)"),
        last_evaluated_key: Optional[str] = Query(
            default=None,
            description="Pagination token from a previous response (`next_page_token`). JSON-encoded.",
        ),
    ) -> PaginatedChannelResponse:
        return self._service.list_channels(table, limit, last_evaluated_key)

    # ── GET /channels/{channel_code} ──────────────────────────────────────────

    def get_channel(
        self,
        channel_code: str,
        table: Optional[str] = Query(default=None, enum=ACTIVE_TABLES,
                                     description="Narrow search to one table."),
    ) -> ChannelResponse:
        return self._service.get_channel(channel_code, table)

    # ── POST /channels ────────────────────────────────────────────────────────

    def create_channel(
        self,
        payload: ChannelCreateRequest = Body(
            openapi_examples={
                "KCR channel": {
                    "summary": "Standard KCR channel",
                    "value": {
                        "_table": "test-KCRChannel-retored",
                        "ChannelCode": "UST59FOXWEATHER",
                        "TVorRadio": "true",
                        "Label": "nattvnormal",
                        "Service": "KCR",
                        "URLs": ["http://185.45.98.43:8080/hls/UST59FOXWEATHER.m3u8"],
                    },
                }
            }
        ),
    ) -> ChannelResponse:
        return self._service.create_channel(payload)

    # ── PUT /channels/{channel_code} ──────────────────────────────────────────

    def replace_channel(
        self,
        channel_code: str,
        payload: ChannelReplaceRequest = Body(
            openapi_examples={
                "Full replace": {
                    "summary": "Replace all fields",
                    "value": {
                        "_table": "test-KCRChannel-retored",
                        "ChannelCode": "UST59FOXWEATHER",
                        "TVorRadio": "true",
                        "Label": "nattvnormal",
                        "Client": "SomeClient",
                        "Service": "KCR",
                        "URLs": ["http://185.45.98.43:8080/hls/UST59FOXWEATHER.m3u8"],
                    },
                }
            }
        ),
    ) -> ChannelResponse:
        return self._service.replace_channel(channel_code, payload)

    # ── PATCH /channels/{channel_code} ────────────────────────────────────────

    def patch_channel(
        self,
        channel_code: str,
        payload: ChannelPatchRequest = Body(
            openapi_examples={
                "Partial update": {
                    "summary": "Update label and URL only",
                    "value": {
                        "_table": "test-KCRChannel-retored",
                        "ChannelCode": "UST59FOXWEATHER",
                        "Label": "nattvnormal_updated",
                        "URLs": ["http://185.45.98.43:8080/hls/UST59FOXWEATHER_updated.m3u8"],
                    },
                }
            }
        ),
    ) -> ChannelResponse:
        return self._service.patch_channel(channel_code, payload)

    # ── DELETE /channels/{channel_code} ───────────────────────────────────────

    def delete_channel(
        self,
        channel_code: str,
        table: str = Query(..., enum=ACTIVE_TABLES,
                           description="Target DynamoDB table (required)."),
    ) -> dict:
        return self._service.delete_channel(channel_code, table)
