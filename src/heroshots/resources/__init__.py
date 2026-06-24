"""Resource namespaces for the HeroShots client."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, Optional

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

        Pass-through for ``None`` and existing http(s) URLs. Lets every generation
        method accept local paths anywhere a ``*_image_url`` is expected.
        """
        if not value:
            return value
        if value.startswith("http://") or value.startswith("https://"):
            return value
        if os.path.exists(value):
            return self._client.uploads.image(value, folder=folder)["public_url"]
        return value
