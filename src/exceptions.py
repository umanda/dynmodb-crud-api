from fastapi import HTTPException, status


class NotFoundError(HTTPException):
    """Base 404 error."""

    def __init__(self, detail: str = "Resource not found."):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class ConflictError(HTTPException):
    """Base 409 error."""

    def __init__(self, detail: str = "Resource already exists."):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class BadRequestError(HTTPException):
    """Base 400 error."""

    def __init__(self, detail: str = "Bad request."):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class DynamoDBError(HTTPException):
    """Wraps DynamoDB / boto3 errors into a 502."""

    def __init__(self, detail: str = "DynamoDB operation failed."):
        super().__init__(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)
