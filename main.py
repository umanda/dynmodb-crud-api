import boto3
import json
import os
from typing import Optional, List
from fastapi import FastAPI, Query, HTTPException, Body
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError
from pydantic import BaseModel, Field, field_validator

app = FastAPI(
    title="DynamoDB Channel API",
    description="""
Browse, create, update, and delete channel items stored in DynamoDB.

**Current active table:** `test-KCRChannel-retored`

> For production, swap `TABLES` in `main.py` back to `BMIChannel`, `KCRChannel`, `KoreaChannel`.

**Swagger UI:** `http://localhost:8000/docs`  
**ReDoc:** `http://localhost:8000/redoc`
""",
    version="1.1.0",
)

# ── Active tables ─────────────────────────────────────────────────────────────
# Testing: single restored table
TABLES = ["test-KCRChannel-retored"]

# Production (comment out above and uncomment below):
# TABLES = ["BMIChannel", "KCRChannel", "KoreaChannel"]
# ─────────────────────────────────────────────────────────────────────────────

# Populated at startup: { "TableName": {"pk": "id", "sk": "service"} }
TABLE_KEYS: dict = {}


@app.on_event("startup")
def discover_table_keys():
    """Use DescribeTable to find the real partition + sort key names for each table."""
    dynamo = get_dynamo()
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


def get_dynamo():
    return boto3.resource(
        "dynamodb",
        region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
    )


def validate_table(table: str):
    if table not in TABLES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown table '{table}'. Must be one of: {TABLES}",
        )


def extract_string(value) -> str:
    """Unwrap a DynamoDB typed value like {"S": "..."} or return plain string."""
    if isinstance(value, dict) and "S" in value:
        return value["S"]
    return str(value) if value is not None else ""


def normalize_item(i: dict, pk: str = "id") -> dict:
    raw_urls = i.get("url") or i.get("urls")

    if isinstance(raw_urls, list):
        # Each entry may be {"S": "http://..."} or a plain string or {"url": "..."}
        urls = []
        for u in raw_urls:
            if isinstance(u, dict):
                if "S" in u:
                    urls.append(u["S"])
                elif "url" in u:
                    urls.append(u["url"])
                else:
                    urls.append(str(u))
            else:
                urls.append(str(u))
    elif isinstance(raw_urls, dict):
        if "S" in raw_urls:
            urls = [raw_urls["S"]]
        elif "url" in raw_urls:
            urls = [raw_urls["url"]]
        else:
            urls = []
    elif isinstance(raw_urls, str):
        urls = [raw_urls]
    else:
        urls = []

    return {
        "ChannelCode": i.get(pk),
        "Client": i.get("client"),
        "TVorRadio": i.get("tv"),
        "Label": i.get("label"),
        "Project": i.get("project"),
        "Service": i.get("service"),
        "URLs": urls,
    }


def fetch_or_404(tbl, channel_code: str, service: str = None) -> dict:
    """
    Fetch an item by channel_code (and optionally service for composite-key tables).
    Falls back to a Scan+filter when the sort key value is unknown.
    """
    pk = get_table_key(tbl.name)
    sk = get_table_sk(tbl.name)

    # If we have both keys, do a direct GetItem
    if sk and service:
        try:
            resp = tbl.get_item(Key={pk: channel_code, sk: service})
            item = resp.get("Item")
            if item:
                return item
        except ClientError as e:
            raise HTTPException(status_code=502, detail=str(e))
    else:
        # No sort key value supplied — fall back to Scan
        try:
            resp = tbl.scan(FilterExpression=Attr(pk).eq(channel_code))
            items = resp.get("Items", [])
            if items:
                return items[0]
        except ClientError as e:
            raise HTTPException(status_code=502, detail=str(e))

    raise HTTPException(status_code=404, detail=f"Channel '{channel_code}' not found.")


# ── Pydantic models ───────────────────────────────────────────────────────────

class ChannelWrite(BaseModel):
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
                "Service": "KCR",
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
        }
    }

    @field_validator("URLs")
    @classmethod
    def urls_not_empty(cls, v):
        if not v:
            raise ValueError("URLs must contain at least one entry.")
        return v


def model_to_dynamo(m: ChannelWrite, pk: str = "id", sk: str = None) -> dict:
    item = {
        pk: m.ChannelCode,
        "client": m.Client,
        "tv": m.TVorRadio,
        "label": m.Label,
        "project": m.Project,
        "service": m.Service,
        "url": m.URLs,   # stored as "url" to match existing table schema
    }
    # Remove None values so we don't write nulls
    item = {k: v for k, v in item.items() if v is not None}
    # If table has a sort key and it's not already in the item, add it explicitly
    if sk and sk not in item and m.Service:
        item[sk] = m.Service
    return item


# ════════════════════════════════════════════════════════════════════════════
# GET  /channels  – paginated list
# ════════════════════════════════════════════════════════════════════════════

@app.get("/channels", summary="List all channels (paginated)", tags=["Channels"])
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
    dynamo = get_dynamo()
    tables_to_scan = [table] if table else TABLES
    all_items = []
    next_key_out = None

    lek = None
    if last_evaluated_key:
        try:
            lek = json.loads(last_evaluated_key)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid last_evaluated_key — must be JSON.")

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
            raise HTTPException(status_code=502, detail=str(e))

        for item in resp.get("Items", []):
            all_items.append({**normalize_item(item, get_table_key(tname)), "_table": tname})
            remaining -= 1
            if remaining <= 0:
                break

        if resp.get("LastEvaluatedKey") and remaining <= 0:
            next_key_out = json.dumps(resp["LastEvaluatedKey"])

    return {"items": all_items, "count": len(all_items), "next_page_token": next_key_out}


# ════════════════════════════════════════════════════════════════════════════
# GET  /channels/{channel_code}
# ════════════════════════════════════════════════════════════════════════════

@app.get("/channels/{channel_code}", summary="Get a channel by ChannelCode", tags=["Channels"])
def get_channel(
    channel_code: str,
    table: Optional[str] = Query(default=None, description="Narrow search to one table.", enum=TABLES),
):
    """
    Fetches the item whose **id** matches *channel_code*.
    Supply **table** to skip scanning other tables (faster).
    """
    dynamo = get_dynamo()
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
            raise HTTPException(status_code=502, detail=str(e))

    raise HTTPException(status_code=404, detail=f"Channel '{channel_code}' not found.")


# ════════════════════════════════════════════════════════════════════════════
# POST  /channels  – create
# ════════════════════════════════════════════════════════════════════════════

@app.post("/channels", summary="Create a new channel", tags=["Channels"], status_code=201)
def create_channel(
    payload: ChannelWrite = Body(
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
    )
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
    dynamo = get_dynamo()
    tbl = dynamo.Table(payload.table)

    pk = get_table_key(payload.table)
    sk = get_table_sk(payload.table)
    item = model_to_dynamo(payload, pk, sk)

    try:
        # attribute_not_exists(pk) ensures we get a 409 if the item already exists
        tbl.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(#pk)",
            ExpressionAttributeNames={"#pk": pk},
        )
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "ConditionalCheckFailedException":
            raise HTTPException(
                status_code=409,
                detail=f"Channel '{payload.ChannelCode}' already exists in '{payload.table}'.",
            )
        raise HTTPException(status_code=502, detail=str(e))

    return {**normalize_item(item, pk), "_table": payload.table}


# ════════════════════════════════════════════════════════════════════════════
# PUT  /channels/{channel_code}  – full replace
# ════════════════════════════════════════════════════════════════════════════

@app.put("/channels/{channel_code}", summary="Fully replace a channel", tags=["Channels"])
def replace_channel(
    channel_code: str,
    payload: ChannelWrite = Body(
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
    )
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
        raise HTTPException(
            status_code=400,
            detail=f"ChannelCode in body ('{payload.ChannelCode}') must match the URL path ('{channel_code}').",
        )
    validate_table(payload.table)
    dynamo = get_dynamo()
    tbl = dynamo.Table(payload.table)
    pk = get_table_key(payload.table)
    sk = get_table_sk(payload.table)

    item = model_to_dynamo(payload, pk, sk)
    try:
        # attribute_exists(pk) ensures we only replace, never create a new item
        tbl.put_item(
            Item=item,
            ConditionExpression="attribute_exists(#pk)",
            ExpressionAttributeNames={"#pk": pk},
        )
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "ConditionalCheckFailedException":
            raise HTTPException(
                status_code=404,
                detail=f"Channel '{channel_code}' not found in '{payload.table}'. Use POST to create it.",
            )
        raise HTTPException(status_code=502, detail=str(e))

    return {**normalize_item(item, pk), "_table": payload.table}


# ════════════════════════════════════════════════════════════════════════════
# PATCH  /channels/{channel_code}  – partial update
# ════════════════════════════════════════════════════════════════════════════

@app.patch("/channels/{channel_code}", summary="Partially update a channel", tags=["Channels"])
def patch_channel(
    channel_code: str,
    payload: ChannelPatch = Body(
        openapi_examples={
            "Partial update": {
                "summary": "Update service and label only",
                "value": {
                    "_table": "test-KCRChannel-retored",
                    "ChannelCode": "UST59FOXWEATHER",
                    "Label": "nattvnormal_updated",
                    "URLs": ["http://185.45.98.43:8080/hls/UST59FOXWEATHER_updated.m3u8"],
                },
            }
        }
    )
):
    """
    **Partial update** — only the fields you supply are changed; omitted fields keep their existing values.

    **Required fields:**
    - `_table` — target DynamoDB table
    - `ChannelCode` — must match the path parameter *(cannot be changed)*
    - `URLs` — list with at least one URL (always required to keep the item valid)

    `ChannelCode` (`id`) is the partition key and `Service` is the sort key — **neither can be changed**. Omit `Service` from PATCH requests; it is ignored.
    """
    if payload.ChannelCode != channel_code:
        raise HTTPException(
            status_code=400,
            detail=f"ChannelCode cannot be changed. Body has '{payload.ChannelCode}', path has '{channel_code}'.",
        )
    validate_table(payload.table)
    dynamo = get_dynamo()
    tbl = dynamo.Table(payload.table)
    pk = get_table_key(payload.table)
    sk = get_table_sk(payload.table)

    # Always fetch via Scan (no sort key needed) to get the existing item and
    # its CURRENT sort key value — Service in the body may differ from stored value
    existing = fetch_or_404(tbl, channel_code)
    existing_sk_value = existing.get(sk) if sk else None

    field_map = {
        "client": payload.Client,
        "tv": payload.TVorRadio,
        "label": payload.Label,
        "project": payload.Project,
        "url": payload.URLs,   # stored as "url" to match table schema
        # Note: service (sort key) is intentionally excluded — sort keys cannot be updated in DynamoDB
    }
    updates = {k: v for k, v in field_map.items() if v is not None}

    if not updates:
        raise HTTPException(status_code=400, detail="No updatable fields provided.")

    set_parts = ", ".join(f"#{k} = :{k}" for k in updates)
    expr_names = {f"#{k}": k for k in updates}
    expr_values = {f":{k}": v for k, v in updates.items()}

    # Build the full key using the EXISTING sort key value, not the one from the body
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
        raise HTTPException(status_code=502, detail=str(e))

    updated = fetch_or_404(tbl, channel_code)
    return {**normalize_item(updated, pk), "_table": payload.table}


# ════════════════════════════════════════════════════════════════════════════
# DELETE  /channels/{channel_code}
# ════════════════════════════════════════════════════════════════════════════

@app.delete("/channels/{channel_code}", summary="Delete a channel", tags=["Channels"])
def delete_channel(
    channel_code: str,
    table: str = Query(..., description="Target DynamoDB table (required).", enum=TABLES),
):
    """
    Deletes the channel item identified by *channel_code*.

    **Required query parameter:**
    - `table` — the DynamoDB table that holds the item

    Returns **404** if the channel does not exist.
    """
    validate_table(table)
    dynamo = get_dynamo()
    tbl = dynamo.Table(table)
    pk = get_table_key(table)
    sk = get_table_sk(table)

    # Fetch the item first so we can get the sort key value for deletion
    item = fetch_or_404(tbl, channel_code)

    key = {pk: channel_code}
    if sk:
        sk_value = item.get(sk)
        if not sk_value:
            raise HTTPException(status_code=500, detail=f"Could not resolve sort key '{sk}' for deletion.")
        key[sk] = sk_value

    try:
        tbl.delete_item(Key=key)
    except ClientError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {"deleted": True, "ChannelCode": channel_code, "_table": table}


# ════════════════════════════════════════════════════════════════════════════
# META
# ════════════════════════════════════════════════════════════════════════════

@app.get("/tables", summary="List available DynamoDB tables", tags=["Meta"])
def list_tables():
    """Returns the list of DynamoDB tables this API manages."""
    return {"tables": TABLES}


@app.get("/health", summary="Health check", tags=["Meta"])
def health():
    return {"status": "ok"}
