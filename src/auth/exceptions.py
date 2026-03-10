from fastapi import HTTPException, status


class InvalidTokenError(HTTPException):
    def __init__(self, detail: str = "Invalid token."):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class PublicKeyNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to find matching public key.",
        )


class TokenValidationError(HTTPException):
    def __init__(self, detail: str = "Token validation failed."):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class PermissionDeniedError(HTTPException):
    def __init__(self, required: str, granted: list[str]):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied. Required: '{required}'. Granted: {granted}",
        )
