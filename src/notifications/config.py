from pydantic_settings import BaseSettings


class NotificationsConfig(BaseSettings):
    """Notification settings."""

    GCHAT_WEBHOOK_URL: str | None = None

    model_config = {"env_file": ".env", "extra": "ignore"}


notifications_settings = NotificationsConfig()
