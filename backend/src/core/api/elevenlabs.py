"""Browser-owned ElevenLabs consent, status and disconnect endpoints."""
import logging
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Response
from vercel import connect
from vercel.connect import ConnectUserTokenSubject, UserAuthorizationRequiredError, AuthorizationPendingError

from core.api.dependencies import session_owner
from core.config import settings
from core.integrations import elevenlabs

router = APIRouter(prefix="/api/integrations/elevenlabs")
logger = logging.getLogger("elevenlabs")


def configured():
    if not elevenlabs.enabled():
        raise HTTPException(503, "ElevenLabs is not configured on this deployment.")


@router.get("")
async def connection_status(response: Response, owner: str = Depends(session_owner)):
    response.headers["Cache-Control"] = "no-store"
    if not elevenlabs.enabled():
        return {"enabled": False, "connected": False}
    try:
        await elevenlabs.provider_token(owner, force_refresh=True)
        return {"enabled": True, "connected": True}
    except (UserAuthorizationRequiredError, AuthorizationPendingError):
        return {"enabled": True, "connected": False}
    except Exception:
        logger.warning("ElevenLabs connection status unavailable")
        raise HTTPException(503, "Could not check ElevenLabs. Please try again later.") from None


@router.post("/connect", dependencies=[Depends(configured)])
async def connect_account(response: Response, owner: str = Depends(session_owner)):
    # Configured origin only: never accept a client-controlled redirect or Host.
    origin = settings.CORE_PUBLIC_URL.rstrip("/")
    url = urlsplit(origin)
    if (url.scheme != "https" and not (url.scheme == "http" and url.hostname == "localhost")) or url.username or url.query or url.fragment or url.path:
        raise HTTPException(503, "ElevenLabs return URL is not configured correctly.")
    try:
        authorization = await connect.start_authorization(
            settings.ELEVENLABS_CONNECTOR, subject=ConnectUserTokenSubject(id=owner),
            scopes=elevenlabs.SCOPES, return_url=origin + "/", options=elevenlabs.options(),
        )
        response.headers["Cache-Control"] = "no-store"
        return {"url": authorization.url}
    except Exception:
        logger.warning("ElevenLabs authorization could not start")
        raise HTTPException(503, "Could not start ElevenLabs sign-in. Please try again later.") from None


@router.delete("", status_code=204, dependencies=[Depends(configured)])
async def disconnect_account(owner: str = Depends(session_owner)):
    try:
        await connect.revoke_token(
            settings.ELEVENLABS_CONNECTOR, subject=ConnectUserTokenSubject(id=owner),
            options=elevenlabs.options(),
        )
        return Response(status_code=204)
    except Exception:
        logger.warning("ElevenLabs disconnect failed")
        raise HTTPException(503, "Could not disconnect ElevenLabs. Please try again later.") from None
