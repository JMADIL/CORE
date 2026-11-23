"""Owner-only shared ElevenLabs setup. Never prints provider tokens or API keys.

Run: uv run --project backend python scripts/connect_shared_elevenlabs.py
Then authorize the returned one-time link. Use --check to verify the grant.
"""
import argparse
import asyncio

from vercel import connect
from vercel.connect import ConnectUserTokenSubject, UserAuthorizationRequiredError, AuthorizationPendingError

from core.config import settings
from core.integrations.elevenlabs import SCOPES, SHARED_SUBJECT, options


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
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
