import os

# ── AWS ──────────────────────────────────────────────────────────────────────
AWS_REGION: str = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
AWS_ACCESS_KEY_ID: str = os.environ.get("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY: str = os.environ.get("AWS_SECRET_ACCESS_KEY", "")

# ── DynamoDB tables ──────────────────────────────────────────────────────────
# Testing: single restored table
ACTIVE_TABLES: list[str] = ["test-KCRChannel-retored"]

# Production (comment out above and uncomment below):
# ACTIVE_TABLES: list[str] = ["BMIChannel", "KCRChannel", "KoreaChannel"]
