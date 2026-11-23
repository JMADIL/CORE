"""Bind platform request headers to the SDK without leaking across requests."""
from vercel.headers import HeadersContext, headers_from_asgi_scope


class VercelRequestContext:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        # The container ASGI server does not install the native Python runtime's
        # SDK context. OIDC is carried by the platform's per-request headers.
        with HeadersContext(headers_from_asgi_scope(scope)).use():
            await self.app(scope, receive, send)
