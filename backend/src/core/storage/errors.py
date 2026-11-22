"""Storage failures independent of HTTP or any particular transport."""


class SessionError(Exception):
    """Base error for session operations."""


class SessionAccessDenied(SessionError):
    """The caller does not own this session."""


class SessionBusy(SessionError):
    """An active request holds the session lease."""


class RateLimitExceeded(SessionError):
    """The request budget has been exhausted."""


class SessionCapacityExceeded(SessionError):
    """The session store has reached its configured capacity."""
