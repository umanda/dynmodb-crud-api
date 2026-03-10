from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ActivityLogRecord(BaseModel):
    id: str
    action: str
    http_method: str
    occurred_at: datetime
    entity_type: str
    entity_id: str
    source_table: str
    actor: dict[str, str | None]
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None


class ActivityLogPage(BaseModel):
    items: list[ActivityLogRecord]
    count: int
    next_page_token: str | None = None
