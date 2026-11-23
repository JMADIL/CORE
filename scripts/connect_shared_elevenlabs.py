"""Owner-only shared ElevenLabs setup. Never prints provider tokens or API keys.

Run: uv run --project backend python scripts/connect_shared_elevenlabs.py
Then authorize the returned one-time link. Use --check to verify the grant.
"""
import argparse
import asyncio
import os
from urllib.parse import urlsplit

import httpx
from dotenv import dotenv_values

from vercel import connect
from vercel.connect import ConnectUserTokenSubject, UserAuthorizationRequiredError, AuthorizationPendingError

from core.config import REPOSITORY_ROOT, settings
from core.integrations.elevenlabs import SCOPES, SHARED_SUBJECT, options


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--remote', help='Live Core origin; creates consent in its deployment environment')
    args = parser.parse_args()
    if args.remote:
        origin = args.remote.rstrip('/')
        parsed = urlsplit(origin)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.path or parsed.query or parsed.fragment:
            raise SystemExit('--remote must be an HTTPS origin.')
        if args.check:
            raise SystemExit('Check the live ElevenLabs dialog for production status.')
        key = os.environ.get('ELEVENLABS_OWNER_SETUP_KEY') or dotenv_values(REPOSITORY_ROOT / '.env').get('ELEVENLABS_OWNER_SETUP_KEY')
        if not key:
            raise SystemExit('Set the private ELEVENLABS_OWNER_SETUP_KEY locally; configure its SHA-256 as ELEVENLABS_OWNER_SETUP_HASH on the deployment.')
        async with httpx.AsyncClient(timeout=45, follow_redirects=False) as client:
            response = await client.post(origin + '/backend/api/integrations/elevenlabs/owner-connect', headers={'X-Core-Setup-Key': key})
        if response.status_code != 200:
            raise SystemExit(f'Owner setup returned HTTP {response.status_code}; check the deployment configuration.')
        result = response.json()
        print('Production owner authorization URL:', result['url'])
        print('One-time confirmation code:', result.get('device_code'))
        return
    if not settings.ELEVENLABS_CONNECTOR:
        raise SystemExit('Configure ELEVENLABS_CONNECTOR first.')
    subject = ConnectUserTokenSubject(id=SHARED_SUBJECT)
    try:
        await connect.get_token(settings.ELEVENLABS_CONNECTOR, subject=subject, scopes=SCOPES,
                                options=options(force_refresh=True))
        print('Shared ElevenLabs account is authorized. Provider credentials remain in Vercel Connect.')
    except (UserAuthorizationRequiredError, AuthorizationPendingError):
        if args.check:
            raise SystemExit('Shared account is not authorized yet.')
        authorization = await connect.start_authorization(
            settings.ELEVENLABS_CONNECTOR, subject=subject, scopes=SCOPES,
            device_code=True, options=options(),
        )
        print('Owner authorization URL:', authorization.url)
        if authorization.device_code:
            print('One-time confirmation code:', authorization.device_code)
        print('Sign in with the account whose credits you want visitors to use. Then run this script with --check.')


if __name__ == '__main__':
    asyncio.run(main())
