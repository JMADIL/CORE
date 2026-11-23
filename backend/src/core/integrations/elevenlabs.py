"""Official ElevenCreative MCP authentication, with personal and shared modes.

Vercel Connect owns OAuth consent and refresh tokens. Provider credentials never
reach the browser. Shared mode uses a server-selected provider subject.
"""
import os

import httpx
from dotenv import dotenv_values
from vercel import connect
from vercel.connect import ConnectOptions, ConnectUserTokenSubject

from core.config import REPOSITORY_ROOT, settings

MCP_URL = "https://api.elevenlabs.io/v1/mcp-creative"
SHARED_SUBJECT = "core-shared-demo-v1"
SCOPES = ["user_read", "flows", "image_video_generation", "text_to_speech", "voice_generation"]
CREATIVE_TOOLS = {
    "creative_generate_image", "creative_edit_image", "creative_generate_video",
    "creative_generate_speech", "creative_generate_in_flow", "creative_list_voices",
    "creative_get_flow_node_types", "creative_get_model_guide", "creative_get_model_schema",
    "creative_get_flow_run_status", "creative_get_generations", "creative_get_flow",
    "creative_get_flow_node", "creative_show_flow_results",
}


class ElevenLabsUnavailable(Exception):
    def __init__(self, *, connection_required=False):
        self.code = "elevenlabs_connection_required" if connection_required else "elevenlabs_unavailable"
        self.detail = (
            "Connect your ElevenLabs account to generate media. Open ElevenLabs in the sidebar, "
            "choose Connect ElevenLabs, and complete sign-in. Then send your request again."
            if connection_required else
            "Core could not access the ElevenLabs generation tools. Open ElevenLabs in the sidebar "
            "to check or reconnect your account, then try again."
        )
        if settings.ELEVENLABS_SHARED_ACCOUNT:
            self.detail = "Media generation is temporarily unavailable. Core's owner needs to connect or renew the shared ElevenLabs account. You do not need your own account."
        super().__init__(self.detail)


class ElevenLabsImageLimit(Exception):
    code = "elevenlabs_image_daily_limit"

    def __init__(self):
        account = "Core's shared ElevenLabs account" if settings.ELEVENLABS_SHARED_ACCOUNT else "Your connected ElevenLabs account"
        self.detail = f"{account} has reached its daily image generation limit. Please try again after ElevenLabs resets the limit."
        super().__init__(self.detail)


def image_limit_reached(error: BaseException) -> bool:
    # Hosted MCP wraps provider errors as tool exceptions, sometimes in task
    # groups. Match the provider's code; never return its raw error to visitors.
    if isinstance(error, BaseExceptionGroup):
        return any(image_limit_reached(child) for child in error.exceptions)
    return "free_tier_image_limit_reached" in str(error)


def needs_authorization(error: BaseException) -> bool:
    from vercel.connect import UserAuthorizationRequiredError, AuthorizationPendingError
    if isinstance(error, (UserAuthorizationRequiredError, AuthorizationPendingError)):
        return True
    # MCP transports can wrap the original authentication error in a task group.
    if isinstance(error, BaseExceptionGroup):
        return any(needs_authorization(child) for child in error.exceptions)
    return False


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
        settings.ELEVENLABS_CONNECTOR,
        subject=ConnectUserTokenSubject(id=SHARED_SUBJECT if settings.ELEVENLABS_SHARED_ACCOUNT else owner),
        # Match the consent request exactly. An additional resource indicator
        # selects a different Vercel Connect grant and falsely asks for consent.
        scopes=SCOPES, options=options(force_refresh=force_refresh),
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
