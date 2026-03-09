from pydantic_settings import BaseSettings


class AuthConfig(BaseSettings):
    """Auth0-specific configuration loaded from environment variables."""

    AUTH0_DOMAIN: str = "dev-umanda.us.auth0.com"
    AUTH0_AUDIENCE: str = "https://api.acme.test"
    AUTH0_CLIENT_ID: str = "gJwhRquTGMF5qeHlJB4kTnuu6J8BgvYr"
    AUTH0_CLIENT_SECRET: str = ""
    AUTH0_REALM: str = "Username-Password-Authentication"

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def jwks_url(self) -> str:
        return f"https://{self.AUTH0_DOMAIN}/.well-known/jwks.json"

    @property
    def token_url(self) -> str:
        return f"https://{self.AUTH0_DOMAIN}/oauth/token"

    @property
    def issuer(self) -> str:
        return f"https://{self.AUTH0_DOMAIN}/"


auth_settings = AuthConfig()
