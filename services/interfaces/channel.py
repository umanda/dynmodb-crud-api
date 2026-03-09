from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from dto import (
    ChannelCreateRequest,
    ChannelPatchRequest,
    ChannelReplaceRequest,
    ChannelResponse,
    PaginatedChannelResponse,
)


class ChannelServiceInterface(ABC):

    @abstractmethod
    def list_channels(
        self,
        table: Optional[str],
        limit: int,
        last_evaluated_key: Optional[str],
    ) -> PaginatedChannelResponse:
        ...

    @abstractmethod
    def get_channel(
        self,
        channel_code: str,
        table: Optional[str],
    ) -> ChannelResponse:
        ...

    @abstractmethod
    def create_channel(self, payload: ChannelCreateRequest) -> ChannelResponse:
        ...

    @abstractmethod
    def replace_channel(
        self,
        channel_code: str,
        payload: ChannelReplaceRequest,
    ) -> ChannelResponse:
        ...

    @abstractmethod
    def patch_channel(
        self,
        channel_code: str,
        payload: ChannelPatchRequest,
    ) -> ChannelResponse:
        ...

    @abstractmethod
    def delete_channel(self, channel_code: str, table: str) -> dict:
        ...