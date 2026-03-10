from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class ChannelWrite(BaseModel):
    """Schema for creating or fully replacing a channel."""

    table: str = Field(alias="_table")
    ChannelCode: str
    URLs: List[str]
    Client: Optional[str] = None
    TVorRadio: Optional[str] = None
    Label: Optional[str] = None
    Project: Optional[str] = None
    Service: Optional[str] = None

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "_table": "test-KCRChannel-retored",
                "ChannelCode": "UST59FOXWEATHER",
                "Client": None,
                "TVorRadio": "true",
                "Label": "nattvnormal",
                "Project": None,
                "Service": "TESTService-A",
                "URLs": ["http://185.45.98.43:8080/hls/UST59FOXWEATHER.m3u8"],
            }
        },
    }

    @field_validator("URLs")
    @classmethod
    def urls_not_empty(cls, v):
        if not v:
            raise ValueError("URLs must contain at least one entry.")
        return v

    @field_validator("ChannelCode")
    @classmethod
    def not_blank(cls, v):
        if not v or not v.strip():
            raise ValueError("ChannelCode must not be blank.")
        return v.strip()


class ChannelPatch(BaseModel):
    """Schema for partially updating a channel."""

    table: str = Field(alias="_table")
    ChannelCode: str
    URLs: List[str]
    Client: Optional[str] = None
    TVorRadio: Optional[str] = None
    Label: Optional[str] = None
    Project: Optional[str] = None
    Service: Optional[str] = None

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "_table": "test-KCRChannel-retored",
                "ChannelCode": "UST59FOXWEATHER",
                "Label": "nattvnormal",
                "Service": "KCR_UPDATED",
                "URLs": ["http://185.45.98.43:8080/hls/UST59FOXWEATHER.m3u8"],
            }
        },
    }

    @field_validator("URLs")
    @classmethod
    def urls_not_empty(cls, v):
        if not v:
            raise ValueError("URLs must contain at least one entry.")
        return v


class ChannelResponse(BaseModel):
    """Normalized channel response."""

    ChannelCode: Optional[str] = None
    Client: Optional[str] = None
    TVorRadio: Optional[str] = None
    Label: Optional[str] = None
    Project: Optional[str] = None
    Service: Optional[str] = None
    URLs: List[str] = []
    _table: Optional[str] = None
