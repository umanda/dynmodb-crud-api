from pydantic import BaseModel, Field


class TokenRequest(BaseModel):
    username: str = Field(..., example="user-admin@acme.test")
    password: str = Field(..., example="!@#$Qwer1234")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    scope: str
