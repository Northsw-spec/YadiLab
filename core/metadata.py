"""Read-only metadata for a future local bootstrap API and window shell."""

from . import identity


def public_metadata() -> dict[str, str]:
    """Always derive the visible title from the one canonical declaration."""
    return {"appDisplayName": identity.APP_DISPLAY_NAME}
