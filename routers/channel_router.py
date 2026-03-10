from fastapi import APIRouter, Depends

from api.handlers import ChannelHandler
from auth import Auth0Service
from services.concrete import ChannelService

# ── Dependency wiring ─────────────────────────────────────────────────────────
_service      = ChannelService()
_handler      = ChannelHandler(service=_service)
_auth_service = Auth0Service()

router = APIRouter(prefix="/channels", tags=["Channels"])

router.add_api_route(
    "",
    _handler.list_channels,
    methods=["GET"],
    summary="List all channels (paginated)",
    dependencies=[Depends(_auth_service.require_permission("read:channel"))],
)

router.add_api_route(
    "/{channel_code}",
    _handler.get_channel,
    methods=["GET"],
    summary="Get a channel by ChannelCode",
    dependencies=[Depends(_auth_service.require_permission("read:channel"))],
)

router.add_api_route(
    "",
    _handler.create_channel,
    methods=["POST"],
    summary="Create a new channel",
    status_code=201,
    dependencies=[Depends(_auth_service.require_permission("write:channel"))],
)

router.add_api_route(
    "/{channel_code}",
    _handler.replace_channel,
    methods=["PUT"],
    summary="Fully replace a channel",
    dependencies=[Depends(_auth_service.require_permission("edit:channel"))],
)

router.add_api_route(
    "/{channel_code}",
    _handler.patch_channel,
    methods=["PATCH"],
    summary="Partially update a channel",
    dependencies=[Depends(_auth_service.require_permission("edit:channel"))],
)

router.add_api_route(
    "/{channel_code}",
    _handler.delete_channel,
    methods=["DELETE"],
    summary="Delete a channel",
    dependencies=[Depends(_auth_service.require_permission("delete:channel"))],
)
