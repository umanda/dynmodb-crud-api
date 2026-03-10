from pydantic_settings import BaseSettings


class ActivityLogsConfig(BaseSettings):
    """Activity logging configuration."""

    ACTIVITY_LOG_TABLE: str = "test-table-activity-log"

    model_config = {"env_file": ".env", "extra": "ignore"}


activity_logs_settings = ActivityLogsConfig()
