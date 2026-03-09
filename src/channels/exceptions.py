from src.exceptions import BadRequestError, ConflictError, NotFoundError


class ChannelNotFoundError(NotFoundError):
    def __init__(self, channel_code: str):
        super().__init__(detail=f"Channel '{channel_code}' not found.")


class ChannelAlreadyExistsError(ConflictError):
    def __init__(self, channel_code: str, table: str):
        super().__init__(
            detail=f"Channel '{channel_code}' already exists in '{table}'."
        )


class UnknownTableError(BadRequestError):
    def __init__(self, table: str, valid_tables: list[str]):
        super().__init__(
            detail=f"Unknown table '{table}'. Must be one of: {valid_tables}"
        )


class InvalidPaginationTokenError(BadRequestError):
    def __init__(self):
        super().__init__(detail="Invalid last_evaluated_key — must be JSON.")


class ChannelCodeMismatchError(BadRequestError):
    def __init__(self, body_code: str, path_code: str):
        super().__init__(
            detail=f"ChannelCode in body ('{body_code}') must match the URL path ('{path_code}')."
        )


class NoUpdatableFieldsError(BadRequestError):
    def __init__(self):
        super().__init__(detail="No updatable fields provided.")


class SortKeyResolutionError(Exception):
    """Raised when the sort key value cannot be resolved for a deletion."""

    def __init__(self, sort_key: str):
        self.sort_key = sort_key
        super().__init__(f"Could not resolve sort key '{sort_key}' for deletion.")
