# DynamoDB Channel API

FastAPI service that exposes your DynamoDB channel tables via a full CRUD REST API,
with Swagger UI at `http://localhost:8000/docs`.

Structured following [FastAPI Best Practices](https://github.com/zhanymkanov/fastapi-best-practices) — a domain-driven, modular layout inspired by Netflix's Dispatch.

See [docs/best-practices.md](docs/best-practices.md) for contributor guidelines.

---

## Project Structure

```
dynmodb-crud-api/
├── src/
│   ├── __init__.py
│   ├── main.py              # FastAPI app factory, lifespan, router includes
│   ├── config.py             # Global settings (BaseSettings)
│   ├── database.py           # DynamoDB resource factory
│   ├── exceptions.py         # Global HTTP exception classes
│   ├── activity_logs/
│   │   ├── __init__.py
│   │   ├── config.py         # Activity log table settings
│   │   ├── router.py         # GET /activity-logs, /activity-logs/search
│   │   ├── schemas.py        # Activity log response models
│   │   └── service.py        # Audit write/list/search logic
│   ├── notifications/
│   │   ├── __init__.py
│   │   ├── config.py         # Notification settings (GChat webhook)
│   │   └── service.py        # GChat notification formatting + send
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── config.py         # Auth0 settings (BaseSettings)
│   │   ├── constants.py      # Algorithms, permission names
│   │   ├── dependencies.py   # get_current_user, require_permission
│   │   ├── exceptions.py     # Auth-specific exceptions
│   │   ├── router.py         # POST /auth/token
│   │   ├── schemas.py        # TokenRequest, TokenResponse
│   │   └── service.py        # JWKS fetch, JWT decode, Auth0 token exchange
│   └── channels/
│       ├── __init__.py
│       ├── config.py          # TABLES settings (BaseSettings)
│       ├── constants.py       # DynamoDB field name mappings
│       ├── dependencies.py    # validate_table dependency
│       ├── exceptions.py      # ChannelNotFound, ChannelAlreadyExists, etc.
│       ├── router.py          # All /channels endpoints
│       ├── schemas.py         # ChannelWrite, ChannelPatch, ChannelResponse
│       ├── service.py         # DynamoDB CRUD business logic
│       └── utils.py           # normalize_item, model_to_dynamo
├── tests/
│   ├── __init__.py
│   ├── auth/
│   │   └── __init__.py
│   └── channels/
│       └── __init__.py
├── docs/
│   └── best-practices.md     # Contributor best-practices guide
├── auth0.http
├── auth0.http.sample
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

### Module convention

Each domain package (`auth/`, `channels/`) follows a consistent layout:

| File | Purpose |
|---|---|
| `router.py` | Endpoint definitions (thin — delegates to service) |
| `schemas.py` | Pydantic request/response models |
| `service.py` | Business logic and data access |
| `dependencies.py` | FastAPI dependencies (auth guards, validators) |
| `config.py` | Domain-specific `BaseSettings` |
| `constants.py` | Module constants and error codes |
| `exceptions.py` | Module-specific HTTP exceptions |
| `utils.py` | Non-business-logic helpers (normalization, etc.) |

---

## 1 · IAM User & Policy

In the AWS Console → IAM → Users → **Add user**:

- **Username**: `dynamo-channel-api` (or any name)
- **Access type**: Programmatic access (Access Key)

### Production policy (read-only)

Attach this **inline policy** for the three production tables:

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
        "arn:aws:dynamodb:*:*:table/LiveChannelTable_1",
        "arn:aws:dynamodb:*:*:table/LiveChannelTable_2",
        "arn:aws:dynamodb:*:*:table/LiveChannelTable_3"
      ]
    }
  ]
}
```

### Testing policy (full CRUD on restored table)

Used during local testing against `test-table`:

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
        "dynamodb:DescribeTable",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem"
      ],
      "Resource": [
        "arn:aws:dynamodb:*:*:table/test-table"
      ]
    },
    {
      "Sid": "ActivityLogReadWrite",
      "Effect": "Allow",
      "Action": [
        "dynamodb:Scan",
        "dynamodb:GetItem",
        "dynamodb:DescribeTable",
        "dynamodb:PutItem"
      ],
      "Resource": [
        "arn:aws:dynamodb:*:*:table/test-table-activity-log"
      ]
    }
  ]
}
```

Download the **Access Key ID** and **Secret Access Key**.

---

## 2 · Configure credentials

```bash
cp .env.example .env
# Edit .env and paste your key + secret

# Optional for notifications
# GCHAT_WEBHOOK_URL=https://chat.googleapis.com/v1/spaces/.../messages?key=...&token=...

# Audit log table name
# ACTIVITY_LOG_TABLE=test-table-activity-log
```

### Mandatory Auth0 step for audit actor email

This step is **required**. If omitted, audit records and notifications may miss the actor email.

1. In Auth0 Dashboard, open **Actions → Flows → Post-Login**.
2. Create a custom Post-Login Action (Node.js runtime).
3. Add logic to inject email into the access token.
4. Deploy the Action and add it to the Post-Login flow.
5. Perform a fresh login and decode the new access token to verify the claim exists.

Use this snippet in your Action:

```javascript
exports.onExecutePostLogin = async (event, api) => {
  // Recommended: replace with your own URL namespace in production.
  const namespace = 'user-email';

  if (event.authorization && event.user && event.user.email) {
    api.accessToken.setCustomClaim(`${namespace}`, event.user.email);
  }
};
```

Notes:
- The API reads standard `email` and custom `user-email` claims for actor extraction.
- Prefer a URL namespace claim in long-term production setups to align with OIDC recommendations.

---

## 3 · Switch between Testing and Production tables

Tables are configured via the `DYNAMODB_TABLES` env var (JSON array) or by editing
`src/channels/config.py`:

```python
# Default (testing): single restored table
DYNAMODB_TABLES: list[str] = ["test-table"]
```

To switch to production, set the environment variable:

```bash
DYNAMODB_TABLES='["LiveChannelTable_1","LiveChannelTable_2","LiveChannelTable_3"]'
```

Or override it in `docker-compose.yml`, then rebuild the container.

---

## 4 · Run with Docker Compose

```bash
# Build and start
docker compose up --build

# Or run in background
docker compose up --build -d
```

The API starts at **http://localhost:8000**

---

## 5 · Swagger UI

Open **http://localhost:8000/docs** in your browser.

### All Endpoints

| Method   | Path                        | Description                              |
|----------|-----------------------------|------------------------------------------|
| `POST`   | `/auth/token`               | Get Auth0 access token (ROPC flow)       |
| `GET`    | `/channels`                 | Paginated list (all tables or one)       |
| `GET`    | `/channels/{channel_code}`  | Fetch a single item by ChannelCode       |
| `POST`   | `/channels`                 | Create a new channel                     |
| `PUT`    | `/channels/{channel_code}`  | Fully replace an existing channel        |
| `PATCH`  | `/channels/{channel_code}`  | Partially update an existing channel     |
| `DELETE` | `/channels/{channel_code}`  | Delete a channel                         |
| `GET`    | `/activity-logs`            | List audit logs (paginated)              |
| `GET`    | `/activity-logs/search`     | Search audit logs by keyword             |
| `GET`    | `/tables`                   | List managed table names                 |
| `GET`    | `/health`                   | Health check                             |

---

### Pagination

```
# First page
GET /channels?limit=10

# Next page — paste the next_page_token value from the previous response
GET /channels?limit=10&last_evaluated_key={"id":{"S":"CH001"}}
```

### Lookup by ChannelCode

```
GET /channels/TESTChannelCode
GET /channels/TESTChannelCode?table=test-table
```

### Create a channel (POST)

`_table`, `ChannelCode`, and `URLs` (at least one) are **mandatory**.

```json
POST /channels
{
  "_table": "test-table",
  "ChannelCode": "TESTChannelCode",
  "Service": "TESTService-A",
  "URLs": ["https://test-media-feed.com/mp3"]
}
```

Returns `409 Conflict` if the ChannelCode already exists.

### Full replace (PUT)

Overwrites **all** fields. `_table`, `ChannelCode` (must match URL), and `URLs` are **mandatory**.

```json
PUT /channels/TESTChannelCode
{
  "_table": "test-table",
  "ChannelCode": "TESTChannelCode",
  "Service": "TESTService-A",
  "Client": "Global",
  "URLs": ["https://test-media-feed.com/mp3"]
}
```

### Partial update (PATCH)

Only the fields you send are changed; everything else stays as-is.  
`_table`, `ChannelCode` (must match URL, **cannot be changed**), and `URLs` are **mandatory**.

```json
PATCH /channels/TESTChannelCode
{
  "_table": "test-table",
  "ChannelCode": "TESTChannelCode",
  "Service": "KCR_UPDATED",
  "URLs": ["https://test-media-feed.com/mp3"]
}
```

### Delete a channel (DELETE)

`table` query param and path `channel_code` are **mandatory**.

```
DELETE /channels/TESTChannelCode?table=test-table
```

### List activity logs

```
GET /activity-logs?limit=20
```

### Search activity logs by keyword

Searches across actor info and payload data, including values such as email, ChannelCode, Service, and URLs.

```
GET /activity-logs/search?keyword=user-admin@acme.test&limit=20
GET /activity-logs/search?keyword=UST59FOXWEATHER
```

### Mutation audit + notification behavior

- Every `POST`, `PUT`, `PATCH`, and `DELETE` on channels writes one record to `ACTIVITY_LOG_TABLE`.
- Audit records include: action, HTTP method, who performed the action, when it happened (UTC), source table, channel id, and before/after data.
- For `PUT` and `PATCH`, the API stores both old and new values.
- The API sends a Google Chat webhook notification (if `GCHAT_WEBHOOK_URL` is configured) that includes actor and timestamp.

---

## 6 · Run without Docker (local Python)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=us-east-1

uvicorn src.main:app --reload
```
