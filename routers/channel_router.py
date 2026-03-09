from fastapi import APIRouter

from api.handlers import ChannelHandler
from services.concrete import ChannelService

# ── Dependency wiring (poor-man's DI) ────────────────────────────────────────
_service = ChannelService()
_handler = ChannelHandler(service=_service)

router = APIRouter(prefix="/channels", tags=["Channels"])

router.add_api_route(
    "",
    _handler.list_channels,
    methods=["GET"],
    summary="List all channels (paginated)",
)

router.add_api_route(
    "/{channel_code}",
    _handler.get_channel,
    methods=["GET"],
    summary="Get a channel by ChannelCode",
)

router.add_api_route(
    "",
    _handler.create_channel,
    methods=["POST"],
    summary="Create a new channel",
    status_code=201,
)

router.add_api_route(
    "/{channel_code}",
    _handler.replace_channel,
    methods=["PUT"],
    summary="Fully replace a channel",
)

router.add_api_route(
    "/{channel_code}",
    _handler.patch_channel,
    methods=["PATCH"],
    summary="Partially update a channel",
)

router.add_api_route(
    "/{channel_code}",
    _handler.delete_channel,
    methods=["DELETE"],
    summary="Delete a channel",
)
