from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Global application settings loaded from environment variables."""

    APP_TITLE: str = "DynamoDB Channel API - Boto3 Auth0 MVC Example"
    APP_VERSION: str = "2.0.0"
    ENVIRONMENT: str = "local"

    # AWS
    AWS_DEFAULT_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
