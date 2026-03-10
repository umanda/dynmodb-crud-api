import json
from typing import Any

from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

from src.database import get_dynamodb_resource
from src.exceptions import DynamoDBError
from src.channels.config import channels_settings
from src.channels.exceptions import (
    ChannelAlreadyExistsError,
    ChannelNotFoundError,
    InvalidPaginationTokenError,
    NoUpdatableFieldsError,
    SortKeyResolutionError,
)
from src.channels.schemas import ChannelPatch, ChannelWrite
from src.channels.utils import model_to_dynamo, normalize_item

TABLES = channels_settings.DYNAMODB_TABLES

# Populated at startup: { "TableName": {"pk": "id", "sk": "service"} }
TABLE_KEYS: dict[str, dict[str, str | None]] = {}


def discover_table_keys() -> None:
    """Use DescribeTable to find the real partition + sort key names for each table."""
    dynamo = get_dynamodb_resource()
    client = dynamo.meta.client
    for tname in TABLES:
        try:
            desc = client.describe_table(TableName=tname)
            key_schema = desc["Table"]["KeySchema"]
            pk = next(k["AttributeName"] for k in key_schema if k["KeyType"] == "HASH")
            sk_list = [k["AttributeName"] for k in key_schema if k["KeyType"] == "RANGE"]
            sk = sk_list[0] if sk_list else None
            TABLE_KEYS[tname] = {"pk": pk, "sk": sk}
            print(f"[startup] {tname} -> partition key = '{pk}', sort key = '{sk}'")
        except Exception as e:
            print(f"[startup] WARNING: could not describe {tname}: {e}")
            TABLE_KEYS[tname] = {"pk": "id", "sk": None}


def get_table_key(tname: str) -> str:
    """Return the partition key name for a table."""
    return TABLE_KEYS.get(tname, {}).get("pk", "id")


def get_table_sk(tname: str) -> str | None:
    """Return the sort key name for a table, or None if there is no sort key."""
    return TABLE_KEYS.get(tname, {}).get("sk")


def fetch_or_404(tbl, channel_code: str, service: str | None = None) -> dict:
    """
    Fetch an item by channel_code (and optionally service for composite-key tables).
    Falls back to a Scan+filter when the sort key value is unknown.
    """
    pk = get_table_key(tbl.name)
    sk = get_table_sk(tbl.name)

    if sk and service:
        try:
            resp = tbl.get_item(Key={pk: channel_code, sk: service})
            item = resp.get("Item")
            if item:
                return item
        except ClientError as e:
            raise DynamoDBError(detail=str(e))
    else:
        try:
            resp = tbl.scan(FilterExpression=Attr(pk).eq(channel_code))
            items = resp.get("Items", [])
            if items:
                return items[0]
        except ClientError as e:
            raise DynamoDBError(detail=str(e))

    raise ChannelNotFoundError(channel_code)


def list_channels(
    table: str | None = None,
    limit: int = 20,
    last_evaluated_key: str | None = None,
) -> dict[str, Any]:
    """Paginated scan across one or all tables."""
    dynamo = get_dynamodb_resource()
    tables_to_scan = [table] if table else TABLES
    all_items: list[dict] = []
    next_key_out = None

    lek = None
    if last_evaluated_key:
        try:
            lek = json.loads(last_evaluated_key)
        except json.JSONDecodeError:
            raise InvalidPaginationTokenError()

    remaining = limit

    for tname in tables_to_scan:
        if remaining <= 0:
            break
        tbl = dynamo.Table(tname)
        scan_kwargs: dict = {"Limit": remaining}
        if lek:
            scan_kwargs["ExclusiveStartKey"] = lek
            lek = None

        try:
            resp = tbl.scan(**scan_kwargs)
        except ClientError as e:
            raise DynamoDBError(detail=str(e))

        for item in resp.get("Items", []):
            all_items.append({**normalize_item(item, get_table_key(tname)), "_table": tname})
            remaining -= 1
            if remaining <= 0:
                break

        if resp.get("LastEvaluatedKey") and remaining <= 0:
            next_key_out = json.dumps(resp["LastEvaluatedKey"])

    return {"items": all_items, "count": len(all_items), "next_page_token": next_key_out}


def get_channel(channel_code: str, table: str | None = None) -> dict:
    """Fetch a single channel by ChannelCode, optionally narrowed to one table."""
    dynamo = get_dynamodb_resource()
    tables_to_search = [table] if table else TABLES

    for tname in tables_to_search:
        tbl = dynamo.Table(tname)
        pk = get_table_key(tname)
        try:
            resp = tbl.get_item(Key={pk: channel_code})
            item = resp.get("Item")
            if item:
                return {**normalize_item(item, pk), "_table": tname}
        except ClientError:
            pass
        try:
            resp = tbl.scan(FilterExpression=Attr(pk).eq(channel_code))
            items = resp.get("Items", [])
            if items:
                return {**normalize_item(items[0], pk), "_table": tname}
        except ClientError as e:
            raise DynamoDBError(detail=str(e))

    raise ChannelNotFoundError(channel_code)


def create_channel(payload: ChannelWrite) -> dict:
    """Create a new channel item in DynamoDB."""
    dynamo = get_dynamodb_resource()
    tbl = dynamo.Table(payload.table)
    pk = get_table_key(payload.table)
    sk = get_table_sk(payload.table)
    item = model_to_dynamo(payload, pk, sk)

    try:
        tbl.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(#pk)",
            ExpressionAttributeNames={"#pk": pk},
        )
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "ConditionalCheckFailedException":
            raise ChannelAlreadyExistsError(payload.ChannelCode, payload.table)
        raise DynamoDBError(detail=str(e))

    return {**normalize_item(item, pk), "_table": payload.table}


def replace_channel(channel_code: str, payload: ChannelWrite) -> dict:
    """Fully replace an existing channel item."""
    dynamo = get_dynamodb_resource()
    tbl = dynamo.Table(payload.table)
    pk = get_table_key(payload.table)
    sk = get_table_sk(payload.table)
    item = model_to_dynamo(payload, pk, sk)

    try:
        tbl.put_item(
            Item=item,
            ConditionExpression="attribute_exists(#pk)",
            ExpressionAttributeNames={"#pk": pk},
        )
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "ConditionalCheckFailedException":
            raise ChannelNotFoundError(channel_code)
        raise DynamoDBError(detail=str(e))

    return {**normalize_item(item, pk), "_table": payload.table}


def patch_channel(channel_code: str, payload: ChannelPatch) -> dict:
    """Partially update a channel, preserving existing values for omitted fields."""
    dynamo = get_dynamodb_resource()
    tbl = dynamo.Table(payload.table)
    pk = get_table_key(payload.table)
    sk = get_table_sk(payload.table)

    existing = fetch_or_404(tbl, channel_code)
    existing_sk_value = existing.get(sk) if sk else None

    field_map = {
        "client": payload.Client,
        "tv": payload.TVorRadio,
        "label": payload.Label,
        "project": payload.Project,
        "url": payload.URLs,
    }
    updates = {k: v for k, v in field_map.items() if v is not None}

    if not updates:
        raise NoUpdatableFieldsError()

    set_parts = ", ".join(f"#{k} = :{k}" for k in updates)
    expr_names = {f"#{k}": k for k in updates}
    expr_values = {f":{k}": v for k, v in updates.items()}

    key = {pk: channel_code}
    if sk and existing_sk_value:
        key[sk] = existing_sk_value

    try:
        tbl.update_item(
            Key=key,
            UpdateExpression=f"SET {set_parts}",
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
        )
    except ClientError as e:
        raise DynamoDBError(detail=str(e))

    updated = fetch_or_404(tbl, channel_code)
    return {**normalize_item(updated, pk), "_table": payload.table}


def delete_channel(channel_code: str, table: str) -> dict:
    """Delete a channel item from DynamoDB."""
    dynamo = get_dynamodb_resource()
    tbl = dynamo.Table(table)
    pk = get_table_key(table)
    sk = get_table_sk(table)

    item = fetch_or_404(tbl, channel_code)

    key = {pk: channel_code}
    if sk:
        sk_value = item.get(sk)
        if not sk_value:
            raise SortKeyResolutionError(sk)
        key[sk] = sk_value

    try:
        tbl.delete_item(Key=key)
    except ClientError as e:
        raise DynamoDBError(detail=str(e))

    return {"deleted": True, "ChannelCode": channel_code, "_table": table}
