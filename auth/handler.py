from __future__ import annotations

from fastapi import Body

from dto.auth import TokenRequest, TokenResponse
from auth.interfaces import AuthServiceInterface


class AuthHandler:
    """
    HTTP handler for authentication.
    Thin layer — delegates all logic to AuthServiceInterface.
    """

    def __init__(self, service: AuthServiceInterface) -> None:
        self._service = service

    def get_token(
        self,
        body: TokenRequest = Body(
            openapi_examples={
                "Admin": {
                    "summary": "Admin — read, write, edit, delete",
                    "value": {"username": "user-admin@acme.test", "password": "!@#$Qwer1234"},
                },
                "Editor": {
                    "summary": "Editor — read, edit",
                    "value": {"username": "user-editor@acme.test", "password": "!@#$Qwer1234"},
                },
                "Viewer": {
                    "summary": "Viewer — read only",
                    "value": {"username": "user-viewer@acme.test", "password": "!@#$Qwer1234"},
                },
                "Manager": {
                    "summary": "Manager — read, write, edit",
                    "value": {"username": "user-manager@acme.test", "password": "!@#$Qwer1234"},
                },
            }
        ),
    ) -> TokenResponse:
        return self._service.get_token(body)
