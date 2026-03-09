from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# ── Shared base ───────────────────────────────────────────────────────────────

class ChannelBase(BaseModel):
    ChannelCode: str
    URLs: List[str]
    Client: Optional[str] = None
    TVorRadio: Optional[str] = None
    Label: Optional[str] = None
    Project: Optional[str] = None
    Service: Optional[str] = None

    @field_validator("URLs")
    @classmethod
    def urls_not_empty(cls, v: list) -> list:
        if not v:
            raise ValueError("URLs must contain at least one entry.")
        return v

    @field_validator("ChannelCode")
    @classmethod
    def channel_code_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("ChannelCode must not be blank.")
        return v.strip()


# ── Write payloads (POST / PUT) ───────────────────────────────────────────────

class ChannelCreateRequest(ChannelBase):
    """
    Used for POST (create).
    `_table`, `ChannelCode`, and `URLs` are mandatory.
    """
    table: str = Field(alias="_table")

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "_table": "test-KCRChannel-retored",
                "ChannelCode": "UST59FOXWEATHER",
                "TVorRadio": "true",
                "Label": "nattvnormal",
                "Service": "KCR",
                "URLs": ["http://185.45.98.43:8080/hls/UST59FOXWEATHER.m3u8"],
            }
        },
    }


class ChannelReplaceRequest(ChannelBase):
    """
    Used for PUT (full replace).
    `_table`, `ChannelCode`, and `URLs` are mandatory.
    `ChannelCode` must match the path parameter.
    """
    table: str = Field(alias="_table")

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "_table": "test-KCRChannel-retored",
                "ChannelCode": "UST59FOXWEATHER",
                "TVorRadio": "true",
                "Label": "nattvnormal",
                "Client": "SomeClient",
                "Service": "KCR",
                "URLs": ["http://185.45.98.43:8080/hls/UST59FOXWEATHER.m3u8"],
            }
        },
    }


# ── Patch payload ─────────────────────────────────────────────────────────────

class ChannelPatchRequest(BaseModel):
    """
    Used for PATCH (partial update).
    `_table`, `ChannelCode`, and `URLs` are mandatory.
    `Service` (sort key) cannot be changed — it is used only for lookup if provided.
    """
    table: str = Field(alias="_table")
    ChannelCode: str
    URLs: List[str]
    Client: Optional[str] = None
    TVorRadio: Optional[str] = None
    Label: Optional[str] = None
    Project: Optional[str] = None

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "_table": "test-KCRChannel-retored",
                "ChannelCode": "UST59FOXWEATHER",
                "Label": "nattvnormal_updated",
                "URLs": ["http://185.45.98.43:8080/hls/UST59FOXWEATHER_updated.m3u8"],
            }
        },
    }

    @field_validator("URLs")
    @classmethod
    def urls_not_empty(cls, v: list) -> list:
        if not v:
            raise ValueError("URLs must contain at least one entry.")
        return v


# ── Response shape ────────────────────────────────────────────────────────────

class ChannelResponse(BaseModel):
    ChannelCode: Optional[str] = None
    Client: Optional[str] = None
    TVorRadio: Optional[str] = None
    Label: Optional[str] = None
    Project: Optional[str] = None
    Service: Optional[str] = None
    URLs: List[str] = []
    table: str = Field(alias="_table")

    model_config = {"populate_by_name": True}


class PaginatedChannelResponse(BaseModel):
    items: List[ChannelResponse]
    count: int
    next_page_token: Optional[str] = None