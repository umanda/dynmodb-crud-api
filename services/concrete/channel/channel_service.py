from __future__ import annotations

import json
from typing import Optional

from fastapi import HTTPException
from pynamodb.exceptions import DoesNotExist, PutError, UpdateError

from config import ACTIVE_TABLES
from dto import (
    ChannelCreateRequest,
    ChannelPatchRequest,
    ChannelReplaceRequest,
    ChannelResponse,
    PaginatedChannelResponse,
)
from models import make_channel_model
from services.interfaces import ChannelServiceInterface


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_urls(raw) -> list[str]:
    """Normalise the `url` attribute which may hold various formats."""
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        result = []
        for u in raw:
            if isinstance(u, dict):
                result.append(u.get("S") or u.get("url") or str(u))
            else:
                result.append(str(u))
        return result
    return []


def _model_to_response(item, table_name: str) -> ChannelResponse:
    raw_url = None
    try:
        raw_url = item.url
        # PynamoDB returns ListAttribute as a list of MapAttribute or raw values
        if raw_url is not None:
            raw_url = list(raw_url)
    except Exception:
        raw_url = None

    return ChannelResponse(
        **{
            "ChannelCode": item.id,
            "Client": getattr(item, "client", None),
            "TVorRadio": getattr(item, "tv", None),
            "Label": getattr(item, "label", None),
            "Project": getattr(item, "project", None),
            "Service": item.service,
            "URLs": _extract_urls(raw_url),
            "_table": table_name,
        }
    )


def _validate_table(table: str) -> None:
    if table not in ACTIVE_TABLES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown table '{table}'. Must be one of: {ACTIVE_TABLES}",
        )


# ── Concrete service ──────────────────────────────────────────────────────────

class ChannelService(ChannelServiceInterface):
    """
    Concrete implementation backed by PynamoDB / DynamoDB.
    """

    # ── LIST ──────────────────────────────────────────────────────────────────

    def list_channels(
        self,
        table: Optional[str],
        limit: int,
        last_evaluated_key: Optional[str],
    ) -> PaginatedChannelResponse:
        tables_to_scan = [table] if table else ACTIVE_TABLES
        all_items: list[ChannelResponse] = []
        next_token: Optional[str] = None
        remaining = limit

        lek = None
        if last_evaluated_key:
            try:
                lek = json.loads(last_evaluated_key)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid last_evaluated_key — must be a JSON string.",
                )

        for tname in tables_to_scan:
            if remaining <= 0:
                break
            Model = make_channel_model(tname)
            scan_kwargs: dict = {"limit": remaining}
            if lek:
                scan_kwargs["last_evaluated_key"] = lek
                lek = None

            result = Model.scan(**scan_kwargs)
            for item in result:
                all_items.append(_model_to_response(item, tname))
                remaining -= 1
                if remaining <= 0:
                    break

            lk = result.last_evaluated_key
            if lk and remaining <= 0:
                next_token = json.dumps(lk)

        return PaginatedChannelResponse(
            items=all_items,
            count=len(all_items),
            next_page_token=next_token,
        )

    # ── GET ───────────────────────────────────────────────────────────────────

    def get_channel(
        self,
        channel_code: str,
        table: Optional[str],
    ) -> ChannelResponse:
        tables_to_search = [table] if table else ACTIVE_TABLES

        for tname in tables_to_search:
            Model = make_channel_model(tname)
            # Scan with filter — avoids needing the sort key value
            results = list(Model.scan(Model.id == channel_code, limit=1))
            if results:
                return _model_to_response(results[0], tname)

        raise HTTPException(
            status_code=404,
            detail=f"Channel '{channel_code}' not found.",
        )

    # ── CREATE ────────────────────────────────────────────────────────────────

    def create_channel(self, payload: ChannelCreateRequest) -> ChannelResponse:
        _validate_table(payload.table)
        Model = make_channel_model(payload.table)

        # Check for duplicate using scan (avoids needing the sort key)
        existing = list(Model.scan(Model.id == payload.ChannelCode, limit=1))
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Channel '{payload.ChannelCode}' already exists in '{payload.table}'.",
            )

        item = Model(
            id=payload.ChannelCode,
            service=payload.Service or "",
            client=payload.Client,
            tv=payload.TVorRadio,
            label=payload.Label,
            project=payload.Project,
            url=payload.URLs,
        )
        item.save(condition=Model.id.does_not_exist())
        return _model_to_response(item, payload.table)

    # ── REPLACE (PUT) ─────────────────────────────────────────────────────────

    def replace_channel(
        self,
        channel_code: str,
        payload: ChannelReplaceRequest,
    ) -> ChannelResponse:
        _validate_table(payload.table)
        if payload.ChannelCode != channel_code:
            raise HTTPException(
                status_code=400,
                detail=f"ChannelCode in body ('{payload.ChannelCode}') must match URL path ('{channel_code}').",
            )

        Model = make_channel_model(payload.table)

        # Fetch existing item to get the sort key value
        existing = list(Model.scan(Model.id == channel_code, limit=1))
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Channel '{channel_code}' not found in '{payload.table}'. Use POST to create it.",
            )

        # Delete old item and re-create with new values (PynamoDB put_item replaces fully)
        old_item = existing[0]
        old_item.delete()

        new_item = Model(
            id=payload.ChannelCode,
            service=payload.Service or old_item.service,
            client=payload.Client,
            tv=payload.TVorRadio,
            label=payload.Label,
            project=payload.Project,
            url=payload.URLs,
        )
        new_item.save()
        return _model_to_response(new_item, payload.table)

    # ── PATCH ─────────────────────────────────────────────────────────────────

    def patch_channel(
        self,
        channel_code: str,
        payload: ChannelPatchRequest,
    ) -> ChannelResponse:
        _validate_table(payload.table)
        if payload.ChannelCode != channel_code:
            raise HTTPException(
                status_code=400,
                detail=f"ChannelCode cannot be changed. Body has '{payload.ChannelCode}', path has '{channel_code}'.",
            )

        Model = make_channel_model(payload.table)

        # Fetch via scan — no sort key needed
        results = list(Model.scan(Model.id == channel_code, limit=1))
        if not results:
            raise HTTPException(
                status_code=404,
                detail=f"Channel '{channel_code}' not found.",
            )

        item = results[0]

        # Build list of PynamoDB actions for only the fields supplied
        actions = []
        if payload.Client is not None:
            actions.append(Model.client.set(payload.Client))
        if payload.TVorRadio is not None:
            actions.append(Model.tv.set(payload.TVorRadio))
        if payload.Label is not None:
            actions.append(Model.label.set(payload.Label))
        if payload.Project is not None:
            actions.append(Model.project.set(payload.Project))
        if payload.URLs:
            actions.append(Model.url.set(payload.URLs))

        if not actions:
            raise HTTPException(status_code=400, detail="No updatable fields provided.")

        item.update(actions=actions)

        # Re-fetch to return fresh state
        refreshed = list(Model.scan(Model.id == channel_code, limit=1))
        return _model_to_response(refreshed[0], payload.table)

    # ── DELETE ────────────────────────────────────────────────────────────────

    def delete_channel(self, channel_code: str, table: str) -> dict:
        _validate_table(table)
        Model = make_channel_model(table)

        results = list(Model.scan(Model.id == channel_code, limit=1))
        if not results:
            raise HTTPException(
                status_code=404,
                detail=f"Channel '{channel_code}' not found.",
            )

        results[0].delete()
        return {"deleted": True, "ChannelCode": channel_code, "_table": table}
