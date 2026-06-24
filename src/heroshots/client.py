"""HeroShots API client.

Authenticates with a **portal JWT** (``Authorization: Bearer <token>``). The token
is obtained from ``POST /api/auth/login`` (HS256, 7-day TTL, no refresh endpoint -
re-login to renew). The client transparently handles the two response envelope
styles used by the backend:

* ``/api/v1/*``        -> ``{"success", "data", "meta"}`` -> unwrapped to ``data``
* everything else      -> bare JSON, returned as-is
"""

from __future__ import annotations

import os
from typing import Any, BinaryIO, Optional

import requests

from .errors import error_from_response, TokenExpiredError
from .models import wrap
from .resources.avatars import Avatars
from .resources.images import Images
from .resources.longvideo import LongVideo
from .resources.stilllife import StillLife
from .resources.storyboard import Storyboard
from .resources.uploads import Uploads
from .resources.videos import Videos

DEFAULT_TIMEOUT = 120.0
DEFAULT_BASE_URL = "https://app.heroshots.ai"


class HeroShotsClient:
    """Entry point for the HeroShots API.

    Example::

        client = HeroShotsClient.from_login("dev@partner.com", "...")
        client.storyboard.brief_suggestions(product_image_url="https://.../p.jpg")
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        *,
        email: Optional[str] = None,
        password: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        session: Optional[requests.Session] = None,
        auto_relogin: bool = True,
    ) -> None:
        base_url = base_url or os.environ.get("HEROSHOTS_BASE_URL") or DEFAULT_BASE_URL
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._email = email
        self._password = password
        self._auto_relogin = auto_relogin
        self.timeout = timeout
        self.session = session or requests.Session()

        # Resource namespaces.
        self.avatars = Avatars(self)
        self.images = Images(self)
        self.longvideo = LongVideo(self)
        self.stilllife = StillLife(self)
        self.storyboard = Storyboard(self)
        self.uploads = Uploads(self)
        self.videos = Videos(self)

    # -- construction helpers -------------------------------------------------

    @classmethod
    def from_login(
        cls,
        email: str,
        password: str,
        *,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        auto_relogin: bool = True,
    ) -> "HeroShotsClient":
        """Create a client and log in with email/password in one step.

        ``base_url`` defaults to https://app.heroshots.ai.
        """
        client = cls(
            base_url,
            email=email,
            password=password,
            timeout=timeout,
            auto_relogin=auto_relogin,
        )
        client.login(email, password)
        return client

    # -- auth -----------------------------------------------------------------

    def login(self, email: str, password: str) -> dict[str, Any]:
        """POST /api/auth/login -> stores and returns the JWT + profile."""
        data = self.request(
            "POST",
            "/api/auth/login",
            json={"email": email, "password": password},
            auth=False,
        )
        self.token = data.get("token")
        self._email, self._password = email, password
        return data

    def me(self) -> dict[str, Any]:
        """GET /api/auth/me -> current authenticated profile."""
        return self.request("GET", "/api/auth/me")

    def balance(self) -> dict[str, Any]:
        """GET /api/auth/stats -> account balance.

        Includes ``hs_credits``, ``total_credits_used`` and ``plan.wallet_balance``.
        """
        return self.request("GET", "/api/auth/stats")

    # -- transport ------------------------------------------------------------

    def request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, Any]] = None,
        files: Optional[dict[str, Any]] = None,
        data: Optional[dict[str, Any]] = None,
        auth: bool = True,
        unwrap: Optional[bool] = None,
        _retried: bool = False,
    ) -> Any:
        """Perform an HTTP request and return decoded JSON (or raise ``ApiError``).

        ``unwrap`` controls envelope handling; when ``None`` it is inferred from the
        path (``/api/v1/*`` responses are wrapped in ``{"success","data","meta"}``).
        """
        url = self.base_url + path
        headers: dict[str, str] = {}
        if auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        resp = self.session.request(
            method.upper(),
            url,
            headers=headers,
            json=json,
            params=params,
            files=files,
            data=data,
            timeout=self.timeout,
        )

        body: Any = None
        if resp.content:
            try:
                body = resp.json()
            except ValueError:
                body = None

        if not resp.ok:
            err = error_from_response(resp.status_code, body)
            # One automatic re-login attempt on an expired token.
            if (
                isinstance(err, TokenExpiredError)
                and self._auto_relogin
                and not _retried
                and self._email
                and self._password
            ):
                self.login(self._email, self._password)
                return self.request(
                    method,
                    path,
                    json=json,
                    params=params,
                    files=files,
                    data=data,
                    auth=auth,
                    unwrap=unwrap,
                    _retried=True,
                )
            raise err

        if unwrap is None:
            unwrap = path.startswith("/api/v1/")
        if unwrap and isinstance(body, dict) and "data" in body:
            data_part = body.get("data")
            meta = body.get("meta")
            if isinstance(data_part, dict) and meta is not None:
                # Surface billing/credits metadata without losing the typed shape.
                data_part.setdefault("_meta", meta)
            return wrap(data_part)
        return wrap(body)

    @staticmethod
    def _multipart_file(file: "str | BinaryIO", field: str = "file") -> dict[str, Any]:
        """Build a ``files=`` dict for ``requests`` from a path or open file object."""
        if isinstance(file, str):
            return {field: open(file, "rb")}  # noqa: SIM115 - requests closes it
        return {field: file}
