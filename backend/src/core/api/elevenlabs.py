"""Browser-owned ElevenLabs consent, status and disconnect endpoints."""
import logging
import hashlib
import secrets
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Header, HTTPException, Response
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


def personal_management_only():
    if settings.ELEVENLABS_SHARED_ACCOUNT:
        raise HTTPException(403, "The shared account is managed by Core's owner.")


@router.get("")
async def connection_status(response: Response, owner: str = Depends(session_owner)):
    response.headers["Cache-Control"] = "no-store"
    mode = "shared" if settings.ELEVENLABS_SHARED_ACCOUNT else "personal"
    if not elevenlabs.enabled():
        return {"enabled": False, "connected": False, "mode": mode}
    try:
        await elevenlabs.provider_token(owner, force_refresh=True)
        return {"enabled": True, "connected": True, "mode": mode}
    except (UserAuthorizationRequiredError, AuthorizationPendingError):
        return {"enabled": True, "connected": False, "mode": mode}
    except Exception as error:
        logger.warning("ElevenLabs connection status unavailable (%s)", type(error).__name__)
        raise HTTPException(503, "Could not check ElevenLabs. Please try again later.") from None


@router.post("/connect", dependencies=[Depends(configured), Depends(personal_management_only)])
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
    except Exception as error:
        logger.warning("ElevenLabs authorization could not start (%s)", type(error).__name__)
        raise HTTPException(503, "Could not start ElevenLabs sign-in. Please try again later.") from None


@router.post("/owner-connect", dependencies=[Depends(configured)])
async def owner_connect(response: Response, x_core_setup_key: str = Header(default="")):
    # Only an operator holding the random setup key can initiate shared consent.
    # Store its hash, never the key, on the deployment. Visitor tokens do not grant access.
    expected = settings.ELEVENLABS_OWNER_SETUP_HASH
    if not settings.ELEVENLABS_SHARED_ACCOUNT or len(expected) != 64:
        raise HTTPException(404, "Owner setup is disabled.")
    if not x_core_setup_key or not secrets.compare_digest(hashlib.sha256(x_core_setup_key.encode()).hexdigest(), expected):
        raise HTTPException(403, "Owner setup credentials are required.")
    response.headers["Cache-Control"] = "no-store"
    try:
        authorization = await connect.start_authorization(
            settings.ELEVENLABS_CONNECTOR,
            subject=ConnectUserTokenSubject(id=elevenlabs.SHARED_SUBJECT),
            scopes=elevenlabs.SCOPES, device_code=True, options=elevenlabs.options(),
        )
        return {"url": authorization.url, "device_code": authorization.device_code}
    except Exception as error:
        logger.warning("Shared ElevenLabs setup unavailable (%s)", type(error).__name__)
        raise HTTPException(503, "Could not start owner authorization. Please try again later.") from None


@router.delete("", status_code=204, dependencies=[Depends(configured), Depends(personal_management_only)])
async def disconnect_account(owner: str = Depends(session_owner)):
    try:
        await connect.revoke_token(
            settings.ELEVENLABS_CONNECTOR, subject=ConnectUserTokenSubject(id=owner),
            options=elevenlabs.options(),
        )
        return Response(status_code=204)
    except Exception as error:
        logger.warning("ElevenLabs disconnect failed (%s)", type(error).__name__)
        raise HTTPException(503, "Could not disconnect ElevenLabs. Please try again later.") from None
