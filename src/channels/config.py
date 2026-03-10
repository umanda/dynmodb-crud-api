from pydantic_settings import BaseSettings


class ChannelsConfig(BaseSettings):
    """Channel-specific configuration."""

    # Testing: single restored table
    DYNAMODB_TABLES: list[str] = ["test-KCRChannel-retored"]

    # Production (override via env var):
    # DYNAMODB_TABLES='["BMIChannel","KCRChannel","KoreaChannel"]'

    model_config = {"env_file": ".env", "extra": "ignore"}


channels_settings = ChannelsConfig()
