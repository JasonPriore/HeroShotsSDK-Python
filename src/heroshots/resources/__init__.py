"""Resource namespaces for the HeroShots client."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, Optional

from ..errors import HeroShotsError

if TYPE_CHECKING:  # pragma: no cover
    from ..client import HeroShotsClient


class Resource:
    """Base class holding a back-reference to the client."""

    def __init__(self, client: "HeroShotsClient") -> None:
        self._client = client

    # Convenience proxies so resource code stays terse.
    def _get(self, path: str, **kw: Any) -> Any:
        return self._client.request("GET", path, **kw)

    def _post(self, path: str, **kw: Any) -> Any:
        return self._client.request("POST", path, **kw)

    def _patch(self, path: str, **kw: Any) -> Any:
        return self._client.request("PATCH", path, **kw)

    def _put(self, path: str, **kw: Any) -> Any:
        return self._client.request("PUT", path, **kw)

    def _delete(self, path: str, **kw: Any) -> Any:
        return self._client.request("DELETE", path, **kw)

    def _resolve_image(self, value: Optional[str], folder: str = "references") -> Optional[str]:
        """If ``value`` is a local file path, upload it and return the hosted URL.

        Pass-through for ``None``, URLs and anything that is not an existing file.
        Uploading needs a portal JWT: with an API key, pass public ``https://`` URLs.
        """
        if not value or not isinstance(value, str):
            return value
        if value.startswith(("http://", "https://", "data:")):
            return value
        if os.path.exists(value):
            if self._client.uses_api_key:
                raise HeroShotsError(
                    f"Cannot upload local file {value!r} with an API key: /upload/image "
                    "accepts only a portal login. Pass a public https:// URL instead, "
                    "or use Client.from_login()."
                )
            return self._client.uploads.image(value, folder=folder)["public_url"]
        return value


def compact(payload: dict[str, Any]) -> dict[str, Any]:
    """Drop ``None`` values so optional keyword arguments are not sent."""
    return {k: v for k, v in payload.items() if v is not None}
