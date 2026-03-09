# DynamoDB Channel API v2

A structured FastAPI + PynamoDB service for managing DynamoDB channel items, with full CRUD and Swagger UI at `http://localhost:8000/docs`.

---

## Project Structure

```
channel-api/
├── main.py                               # App entry point, mounts routers
├── config/
│   └── settings.py                       # AWS credentials & active table names
├── models/
│   └── channel.py                        # PynamoDB model (composite key: id + service)
├── dto/
│   └── channel.py                        # Pydantic request / response shapes
├── services/
│   ├── interfaces/
│   │   └── channel.py                    # Abstract service contract
│   └── concrete/
│       └── channel/
│           └── channel_service.py        # PynamoDB implementation
├── api/
│   └── handlers/
│       └── channel_handler.py            # HTTP layer — delegates to service
├── routers/
│   └── channel_router.py                 # Wires FastAPI routes to handler methods
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

**Layer responsibilities:**

| Layer | Responsibility |
|---|---|
| `config/` | All environment-driven settings in one place |
| `models/` | PynamoDB table definition — maps DynamoDB schema to Python objects |
| `dto/` | Pydantic shapes for API requests and responses |
| `services/interfaces/` | Abstract contract — swap implementations without touching routes |
| `services/concrete/` | Real DynamoDB logic using PynamoDB |
| `api/handlers/` | Translate HTTP parameters → service calls, nothing else |
| `routers/` | Register routes and inject dependencies |

---

## 1 · IAM User & Policy

In the AWS Console → IAM → Users → **Add user**:

- **Username**: `dynamo-channel-api` (or any name)
- **Access type**: Programmatic access (Access Key)

### Testing policy — full CRUD on restored table

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CRUDChannelTables",
      "Effect": "Allow",
      "Action": [
        "dynamodb:Scan",
        "dynamodb:GetItem",
        "dynamodb:DescribeTable",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem"
      ],
      "Resource": [
        "arn:aws:dynamodb:*:*:table/test-KCRChannel-retored"
      ]
    }
  ]
}
```

### Production policy — read-only on live tables

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ReadChannelTables",
      "Effect": "Allow",
      "Action": [
        "dynamodb:Scan",
        "dynamodb:GetItem",
        "dynamodb:DescribeTable"
      ],
      "Resource": [
        "arn:aws:dynamodb:*:*:table/BMIChannel",
        "arn:aws:dynamodb:*:*:table/KCRChannel",
        "arn:aws:dynamodb:*:*:table/KoreaChannel"
      ]
    }
  ]
}
```

> Add `PutItem`, `UpdateItem`, `DeleteItem` to the production policy if write access is needed there too.

Download the **Access Key ID** and **Secret Access Key** after creating the user.

---

## 2 · Configure Credentials

```bash
cp .env.example .env
# Fill in your AWS credentials
```

`.env` contents:

```
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=your_secret_here
AWS_DEFAULT_REGION=us-east-1
```

---

## 3 · Switch Between Testing and Production Tables

Edit `config/settings.py`:

```python
# Testing: single restored table
ACTIVE_TABLES: list[str] = ["test-KCRChannel-retored"]

# Production (comment out above and uncomment below):
# ACTIVE_TABLES: list[str] = ["BMIChannel", "KCRChannel", "KoreaChannel"]
```

Rebuild the container after changing this.

---

## 4 · Run with Docker Compose

```bash
# Build and start (with live reload)
docker compose up --build

# Run in background
docker compose up --build -d

# View logs
docker compose logs -f api

# Stop
docker compose down
```

The API starts at **http://localhost:8000**

---

## 5 · Run Without Docker (local Python)

```bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate

pip install -r requirements.txt

export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=us-east-1

uvicorn main:app --reload
```

---

## 6 · Swagger UI

Open **http://localhost:8000/docs** in your browser.

Alternative docs (read-only): **http://localhost:8000/redoc**

---

## 7 · API Endpoints

### Overview

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/channels` | Paginated list (all tables or filtered by one) |
| `GET` | `/channels/{channel_code}` | Fetch a single channel by ChannelCode |
| `POST` | `/channels` | Create a new channel |
| `PUT` | `/channels/{channel_code}` | Fully replace an existing channel |
| `PATCH` | `/channels/{channel_code}` | Partially update an existing channel |
| `DELETE` | `/channels/{channel_code}` | Delete a channel |
| `GET` | `/tables` | List managed table names |
| `GET` | `/health` | Health check |

---

### GET /channels — paginated list

```
GET /channels?limit=20
GET /channels?table=test-KCRChannel-retored&limit=10
```

Response:
```json
{
  "items": [...],
  "count": 20,
  "next_page_token": "{\"id\": {\"S\": \"UST46FoxNews\"}, \"service\": {\"S\": \"KCR\"}}"
}
```

Paginate by passing `next_page_token` as `last_evaluated_key` on the next request:

```
GET /channels?limit=10&last_evaluated_key={"id":{"S":"UST46FoxNews"},"service":{"S":"KCR"}}
```

---

### GET /channels/{channel_code}

```
GET /channels/UST59FOXWEATHER
GET /channels/UST59FOXWEATHER?table=test-KCRChannel-retored
```

Returns `404` if not found.

---

### POST /channels — create

`_table`, `ChannelCode`, and `URLs` (at least one) are **mandatory**.

```json
POST /channels
{
  "_table": "test-KCRChannel-retored",
  "ChannelCode": "UST59FOXWEATHER_NEW",
  "TVorRadio": "true",
  "Label": "nattvnormal",
  "Service": "KCR",
  "URLs": ["http://185.45.98.43:8080/hls/UST59FOXWEATHER.m3u8"]
}
```

Returns `201 Created` with the new item, or `409 Conflict` if ChannelCode already exists.

---

### PUT /channels/{channel_code} — full replace

Overwrites **all** fields. `_table`, `ChannelCode` (must match URL path), and `URLs` are **mandatory**.

```json
PUT /channels/UST59FOXWEATHER_NEW
{
  "_table": "test-KCRChannel-retored",
  "ChannelCode": "UST59FOXWEATHER_NEW",
  "TVorRadio": "true",
  "Label": "nattvnormal",
  "Client": "SomeClient",
  "Service": "KCR",
  "URLs": ["http://185.45.98.43:8080/hls/UST59FOXWEATHER.m3u8"]
}
```

Returns `404` if the channel does not exist — use `POST` to create it first.

---

### PATCH /channels/{channel_code} — partial update

Only the fields you provide are changed; everything else keeps its current value.

`_table`, `ChannelCode` (must match URL), and `URLs` are **mandatory**.

> `Service` is the DynamoDB **sort key** and **cannot be changed**. Do not include it in PATCH requests.

```json
PATCH /channels/UST59FOXWEATHER_NEW
{
  "_table": "test-KCRChannel-retored",
  "ChannelCode": "UST59FOXWEATHER_NEW",
  "Label": "updated_label",
  "URLs": ["http://185.45.98.43:8080/hls/UPDATED.m3u8"]
}
```

---

### DELETE /channels/{channel_code}

`table` query param is **mandatory**.

```
DELETE /channels/UST59FOXWEATHER_NEW?table=test-KCRChannel-retored
```

Returns `404` if not found.

---

## 8 · DynamoDB Table Schema

| Attribute | Type | Role |
|---|---|---|
| `id` | String | Partition key — maps to `ChannelCode` |
| `service` | String | Sort key — maps to `Service` |
| `client` | String | Optional |
| `tv` | String | Optional — maps to `TVorRadio` |
| `label` | String | Optional |
| `project` | String | Optional |
| `url` | List | One or more stream URLs |

> `id` + `service` form a **composite key**. Both are required when creating a channel.

---

## 9 · Adding a New Table

1. Update `ACTIVE_TABLES` in `config/settings.py`
2. Update the IAM policy to include the new table ARN
3. If the new table has a different key schema, update `models/channel.py`
4. Rebuild: `docker compose up --build`