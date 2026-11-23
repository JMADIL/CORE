"""Official ElevenCreative MCP authentication, scoped to each browser owner.

Vercel Connect owns OAuth consent and refresh tokens. Provider credentials never
reach the browser and are never shared between Core's anonymous sessions.
"""
import os

import httpx
from dotenv import dotenv_values
from vercel import connect
from vercel.connect import ConnectOptions, ConnectUserTokenSubject

from core.config import REPOSITORY_ROOT, settings

MCP_URL = "https://api.elevenlabs.io/v1/mcp-creative"
SCOPES = ["user_read", "flows", "image_video_generation", "text_to_speech", "voice_generation"]
CREATIVE_TOOLS = {
    "creative_generate_image", "creative_edit_image", "creative_generate_video",
    "creative_generate_speech", "creative_generate_in_flow", "creative_list_voices",
    "creative_get_flow_node_types", "creative_get_model_guide", "creative_get_model_schema",
    "creative_get_flow_run_status", "creative_get_generations", "creative_get_flow",
    "creative_get_flow_node", "creative_show_flow_results",
}


def enabled() -> bool:
    return bool(settings.ELEVENLABS_CONNECTOR and settings.CORE_PUBLIC_URL)


def _oidc_token() -> str:
    token = os.environ.get("VERCEL_OIDC_TOKEN")
    if not token and not os.environ.get("VERCEL"):
        token = dotenv_values(REPOSITORY_ROOT / ".env.local").get("VERCEL_OIDC_TOKEN")
    if not token:
        raise RuntimeError("Vercel Connect credentials are not configured")
    return token


def options(*, force_refresh=False):
    # In a container the platform may rotate OIDC through a token file rather
    # than an environment variable. Let the SDK resolve runtime credentials.
    return ConnectOptions(
        vercel_token=None if os.environ.get("VERCEL") else _oidc_token,
        force_refresh=force_refresh,
    )


async def provider_token(owner: str, *, force_refresh=False) -> str:
    return await connect.get_token(
        settings.ELEVENLABS_CONNECTOR, subject=ConnectUserTokenSubject(id=owner),
        scopes=SCOPES, resources=[MCP_URL], options=options(force_refresh=force_refresh),
    )


class ElevenLabsAuth(httpx.Auth):
    async def async_auth_flow(self, request):
        request.headers["Authorization"] = "Bearer " + await provider_token(self.owner)
        response = yield request
        if response.status_code == 401:
            # Refresh once after revocation/expiry; never retry paid generations.
            request.headers["Authorization"] = "Bearer " + await provider_token(self.owner, force_refresh=True)
            yield request

    def __init__(self, owner: str):
        self.owner = owner
