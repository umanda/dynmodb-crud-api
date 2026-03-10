import json
import uuid
from datetime import datetime, timezone
from typing import Any

from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

from src.activity_logs.config import activity_logs_settings
from src.database import get_dynamodb_resource
from src.exceptions import BadRequestError, DynamoDBError


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _actor_from_claims(user: dict | None) -> dict[str, str | None]:
    user = user or {}
    return {
        "subject": user.get("sub"),
        "email": user.get("email"),
        "name": user.get("name"),
    }


def _build_search_blob(entry: dict[str, Any]) -> str:
    values = [
        entry.get("action", ""),
        entry.get("http_method", ""),
        entry.get("entity_type", ""),
        entry.get("entity_id", ""),
        entry.get("source_table", ""),
        json.dumps(entry.get("actor", {}), default=str),
        json.dumps(entry.get("before", {}), default=str),
        json.dumps(entry.get("after", {}), default=str),
    ]
    return " ".join(str(v) for v in values if v).lower()


def log_channel_activity(
    *,
    action: str,
    http_method: str,
    source_table: str,
    channel_code: str,
    user: dict | None,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
    occurred_at: str | None = None,
) -> dict[str, Any]:
    """Persist a channel audit event into the activity log table."""
    dynamo = get_dynamodb_resource()
    table = dynamo.Table(activity_logs_settings.ACTIVITY_LOG_TABLE)

    item = {
        "id": str(uuid.uuid4()),
        "action": action.upper(),
        "http_method": http_method.upper(),
        "occurred_at": occurred_at or _utc_now_iso(),
        "entity_type": "CHANNEL",
        "entity_id": channel_code,
        "source_table": source_table,
        "actor": _actor_from_claims(user),
        "before": before,
        "after": after,
    }
    item["search_blob"] = _build_search_blob(item)

    try:
        table.put_item(Item=item)
    except ClientError as e:
        raise DynamoDBError(detail=f"Failed to write activity log: {e}")

    return item


def _scan_activity_logs(
    *,
    limit: int,
    last_evaluated_key: str | None,
    filter_expression=None,
) -> dict[str, Any]:
    dynamo = get_dynamodb_resource()
    table = dynamo.Table(activity_logs_settings.ACTIVITY_LOG_TABLE)

    scan_kwargs: dict[str, Any] = {"Limit": limit}
    if filter_expression is not None:
        scan_kwargs["FilterExpression"] = filter_expression

    if last_evaluated_key:
        try:
            scan_kwargs["ExclusiveStartKey"] = json.loads(last_evaluated_key)
        except json.JSONDecodeError:
            raise BadRequestError(detail="Invalid last_evaluated_key. Must be JSON.")

    try:
        resp = table.scan(**scan_kwargs)
    except ClientError as e:
        raise DynamoDBError(detail=f"Failed to read activity logs: {e}")

    items = resp.get("Items", [])
    items.sort(key=lambda x: x.get("occurred_at", ""), reverse=True)
    next_page = resp.get("LastEvaluatedKey")

    return {
        "items": items,
        "count": len(items),
        "next_page_token": json.dumps(next_page) if next_page else None,
    }


def list_activity_logs(limit: int = 20, last_evaluated_key: str | None = None) -> dict[str, Any]:
    """List activity logs in descending occurred_at order for the current page."""
    return _scan_activity_logs(limit=limit, last_evaluated_key=last_evaluated_key)


def search_activity_logs(
    keyword: str,
    limit: int = 20,
    last_evaluated_key: str | None = None,
) -> dict[str, Any]:
    """Search activity logs by keyword against a normalized search blob."""
    normalized = keyword.strip().lower()
    if not normalized:
        raise BadRequestError(detail="keyword must not be blank.")

    return _scan_activity_logs(
        limit=limit,
        last_evaluated_key=last_evaluated_key,
        filter_expression=Attr("search_blob").contains(normalized),
    )
