# DynamoDB Channel API — Local Dev Setup

FastAPI service that exposes your DynamoDB channel tables via a full CRUD REST API,
with Swagger UI at `http://localhost:8000/docs`.

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
        "arn:aws:dynamodb:*:*:table/BMIChannel",
        "arn:aws:dynamodb:*:*:table/KCRChannel",
        "arn:aws:dynamodb:*:*:table/KoreaChannel"
      ]
    }
  ]
}
```

### Testing policy (full CRUD on restored table)

Used during local testing against `test-KCRChannel-retored`:

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
        "arn:aws:dynamodb:*:*:table/test-KCRChannel-retored"
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
```

---

## 3 · Switch between Testing and Production tables

In `main.py`, find the `TABLES` section near the top:

```python
# Testing: single restored table
TABLES = ["test-KCRChannel-retored"]

# Production (comment out above and uncomment below):
# TABLES = ["BMIChannel", "KCRChannel", "KoreaChannel"]
```

Switch the comments as needed, then rebuild the container.

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
| `GET`    | `/channels`                 | Paginated list (all tables or one)       |
| `GET`    | `/channels/{channel_code}`  | Fetch a single item by ChannelCode       |
| `POST`   | `/channels`                 | Create a new channel                     |
| `PUT`    | `/channels/{channel_code}`  | Fully replace an existing channel        |
| `PATCH`  | `/channels/{channel_code}`  | Partially update an existing channel     |
| `DELETE` | `/channels/{channel_code}`  | Delete a channel                         |
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
GET /channels/GBR149CapitalDance
GET /channels/GBR149CapitalDance?table=test-KCRChannel-retored
```

### Create a channel (POST)

`_table`, `ChannelCode`, and `URLs` (at least one) are **mandatory**.

```json
POST /channels
{
  "_table": "test-KCRChannel-retored",
  "ChannelCode": "GBR149CapitalDance",
  "Service": "KCR",
  "URLs": ["https://media-ssl.musicradio.com/CapitalDance?isLoggedIn=false"]
}
```

Returns `409 Conflict` if the ChannelCode already exists.

### Full replace (PUT)

Overwrites **all** fields. `_table`, `ChannelCode` (must match URL), and `URLs` are **mandatory**.

```json
PUT /channels/GBR149CapitalDance
{
  "_table": "test-KCRChannel-retored",
  "ChannelCode": "GBR149CapitalDance",
  "Service": "KCR",
  "Client": "Global",
  "URLs": ["https://media-ssl.musicradio.com/CapitalDance?isLoggedIn=false"]
}
```

### Partial update (PATCH)

Only the fields you send are changed; everything else stays as-is.  
`_table`, `ChannelCode` (must match URL, **cannot be changed**), and `URLs` are **mandatory**.

```json
PATCH /channels/GBR149CapitalDance
{
  "_table": "test-KCRChannel-retored",
  "ChannelCode": "GBR149CapitalDance",
  "Service": "KCR_UPDATED",
  "URLs": ["https://media-ssl.musicradio.com/CapitalDance?isLoggedIn=false"]
}
```

### Delete a channel (DELETE)

`table` query param and path `channel_code` are **mandatory**.

```
DELETE /channels/GBR149CapitalDance?table=test-KCRChannel-retored
```

---

## 6 · Run without Docker (local Python)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=us-east-1

uvicorn main:app --reload
```
