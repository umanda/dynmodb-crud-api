import os

# ── AWS ──────────────────────────────────────────────────────────────────────
AWS_REGION: str = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
AWS_ACCESS_KEY_ID: str = os.environ.get("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY: str = os.environ.get("AWS_SECRET_ACCESS_KEY", "")

# ── DynamoDB tables ──────────────────────────────────────────────────────────
# Read from env (comma-separated) when deployed, fall back to dev default.
ACTIVE_TABLES: list[str] = [
    t.strip()
    for t in os.environ.get("ACTIVE_TABLES", "test-KCRChannel-retored").split(",")
    if t.strip()
]

# ── Auth0 ─────────────────────────────────────────────────────────────────────
AUTH0_DOMAIN: str        = os.environ.get("AUTH0_DOMAIN",        "dev-umanda.us.auth0.com")
AUTH0_AUDIENCE: str      = os.environ.get("AUTH0_AUDIENCE",      "https://api.acme.test")
AUTH0_CLIENT_ID: str     = os.environ.get("AUTH0_CLIENT_ID",     "gJwhRquTGMF5qeHlJB4kTnuu6J8BgvYr")
AUTH0_CLIENT_SECRET: str = os.environ.get("AUTH0_CLIENT_SECRET", "")
AUTH0_REALM: str         = os.environ.get("AUTH0_REALM",         "Username-Password-Authentication")
AUTH0_ALGORITHMS: list[str] = ["RS256"]