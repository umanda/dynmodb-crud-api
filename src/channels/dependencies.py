from fastapi import Depends, Query

from src.channels.config import channels_settings
from src.channels.exceptions import UnknownTableError

TABLES = channels_settings.DYNAMODB_TABLES


def validate_table(table: str) -> str:
    """Validate that the given table name is in the allowed list."""
    if table not in TABLES:
        raise UnknownTableError(table=table, valid_tables=TABLES)
    return table


def get_table_query(
    table: str | None = Query(
        default=None,
        description="Filter by table name.",
    ),
) -> str | None:
    """Optional table query parameter dependency."""
    if table is not None:
        validate_table(table)
    return table


def get_required_table_query(
    table: str = Query(
        ...,
        description="Target DynamoDB table (required).",
    ),
) -> str:
    """Required table query parameter dependency."""
    validate_table(table)
    return table
