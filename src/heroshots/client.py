"""HeroShots API client.

Authenticates with a **B2B API key** (``lz_live_...``) or a **portal JWT**, both
sent as ``Authorization: Bearer <token>``. Portal JWTs come from
``POST /api/auth/login`` (HS256, 7-day TTL, no refresh endpoint - the client
re-logs in once on ``token_expired`` when it knows the credentials).

Which credential works where:

* ``/api/v1/*`` (images, videos, long video, still life, avatars, library, bulk,
  pricing, agency, brand) accepts **both** API keys and portal JWTs.
* Portal routes (storyboard, uploads, image candidates, still-life background
  edits, legal) accept **only** a portal JWT.
* API keys are refused on the Free plan (``plan_not_allowed``), except for
  agency accounts.

Response envelopes:

* ``/api/v1/*``        -> ``{"success", "data", "meta"}`` -> unwrapped to ``data``
  (``meta`` is kept under ``data["_meta"]``)
* everything else      -> bare JSON, returned as-is
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, BinaryIO, Optional, Union

import requests

from .errors import ApiError, RateLimitError, TokenExpiredError, error_from_response
from .models import wrap
from .resources.account import Account
from .resources.agency import Agency
from .resources.avatars import Avatars
from .resources.brand import Brand
from .resources.bulk import Bulk
from .resources.generations import Generations
from .resources.images import Images
from .resources.legal import Legal
from .resources.library import Assets, Backgrounds, Categories, Collections
from .resources.longvideo import LongVideo
from .resources.pricing import Pricing
from .resources.stilllife import StillLife
from .resources.storyboard import Storyboard
from .resources.uploads import Uploads
from .resources.videos import Videos

DEFAULT_TIMEOUT = 120.0
DEFAULT_BASE_URL = "https://app.heroshots.ai"
DEFAULT_MAX_RETRIES = 2
API_KEY_PREFIX = "lz_"

FileInput = Union[str, os.PathLike, bytes, BinaryIO]


def _sdk_version() -> str:
    from . import __version__

    return __version__


class HeroShotsClient:
    """Entry point for the HeroShots API.

    Example::

        client = HeroShotsClient(api_key="lz_live_...")
        job = client.images.generate("https://.../product.jpg", avatar_id=12)
        done = client.images.wait(job["generation_id"])
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        *,
        api_key: Optional[str] = None,
        email: Optional[str] = None,
        password: Optional[str] = None,
        managed_user_id: Optional[Union[str, int]] = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        session: Optional[requests.Session] = None,
        auto_relogin: bool = True,
    ) -> None:
        base_url = base_url or os.environ.get("HEROSHOTS_BASE_URL") or DEFAULT_BASE_URL
        self.base_url = base_url.rstrip("/")
        self.token = token or api_key or os.environ.get("HEROSHOTS_API_KEY") or None
        self.managed_user_id = managed_user_id
        self._email = email
        self._password = password
        self._auto_relogin = auto_relogin
        self.timeout = timeout
        self.max_retries = max(0, int(max_retries))
        self.session = session or requests.Session()

        # Account / auth helpers.
        self.account = Account(self)
        # Generation.
        self.images = Images(self)
        self.videos = Videos(self)
        self.longvideo = LongVideo(self)
        self.stilllife = StillLife(self)
        self.storyboard = Storyboard(self)
        self.avatars = Avatars(self)
        self.bulk = Bulk(self)
        self.generations = Generations(self)
        self.pricing = Pricing(self)
        # Library.
        self.assets = Assets(self)
        self.collections = Collections(self)
        self.backgrounds = Backgrounds(self)
        self.categories = Categories(self)
        # Files, compliance, relationships.
        self.uploads = Uploads(self)
        self.legal = Legal(self)
        self.agency = Agency(self)
        self.brand = Brand(self)

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

    @property
    def uses_api_key(self) -> bool:
        """True when the bearer is a B2B API key (``lz_live_...``), not a portal JWT."""
        return bool(self.token) and str(self.token).startswith(API_KEY_PREFIX)

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
        """Current account.

        With an API key: ``GET /api/v1/me`` (``{user, credits_remaining}``).
        With a portal JWT: ``GET /api/auth/me`` (full portal profile).
        """
        if self.uses_api_key:
            return self.account.me()
        return self.request("GET", "/api/auth/me")

    def stats(self) -> dict[str, Any]:
        """GET /api/auth/stats -> full raw portal stats (portal JWT only)."""
        return self.request("GET", "/api/auth/stats")

    def balance(self) -> dict[str, Any]:
        """Compact credit/wallet view.

        Always contains ``hs_credits`` and ``wallet_balance`` when the backend
        reports them. With an API key it reads ``/api/v1/me`` (``currency_credit``
        is the wallet in EUR); with a portal JWT it reads ``/api/auth/stats`` and
        also returns plan and usage counters.
        """
        if self.uses_api_key:
            me = self.account.me()
            credits = me.get("credits_remaining") if isinstance(me, dict) else None
            credits = credits if isinstance(credits, dict) else {}
            user = me.get("user") if isinstance(me, dict) else None
            user = user if isinstance(user, dict) else {}
            out: dict[str, Any] = {}
            if "hs_credits" in credits:
                out["hs_credits"] = credits["hs_credits"]
            wallet = credits.get("currency_credit", user.get("currency_credit"))
            if wallet is not None:
                out["currency_credit"] = wallet
                out["wallet_balance"] = wallet
            if "currency_billing_type" in user:
                out["billing_type"] = user["currency_billing_type"]
            return wrap(out)

        stats = self.stats()
        plan = stats.get("plan") if isinstance(stats, dict) else {}
        if not isinstance(plan, dict):
            plan = {}

        keys = [
            "hs_credits",
            "total_credits_used",
            "total_cost_charged",
            "current_month_cost",
            "current_month_generations",
            "total_generations",
            "video_package_credits_remaining",
            "free_preview_videos_remaining",
            "use_wallet",
        ]
        out = {key: stats[key] for key in keys if isinstance(stats, dict) and key in stats}

        plan_keys = [
            "wallet_balance",
            "template_id",
            "billing_type",
            "output_resolution",
            "has_watermark",
            "offered_plan_id",
            "monthly_price",
        ]
        compact_plan = {key: plan[key] for key in plan_keys if key in plan}
        if compact_plan:
            out["plan"] = compact_plan
        if "wallet_balance" in compact_plan:
            out["wallet_balance"] = compact_plan["wallet_balance"]

        return wrap(out)

    def with_managed_user(self, managed_user_id: Optional[Union[str, int]]) -> "HeroShotsClient":
        """Set the managed brand target for agency act-as requests (``None`` clears it)."""
        self.managed_user_id = managed_user_id
        return self

    # -- transport ------------------------------------------------------------

    def request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[Any] = None,
        params: Optional[dict[str, Any]] = None,
        files: Optional[Any] = None,
        data: Optional[dict[str, Any]] = None,
        auth: bool = True,
        unwrap: Optional[bool] = None,
        raw: bool = False,
        _retried: bool = False,
    ) -> Any:
        """Perform an HTTP request and return decoded JSON (or raise ``ApiError``).

        ``unwrap`` controls envelope handling; when ``None`` it is inferred from the
        path (``/api/v1/*`` responses are wrapped in ``{"success","data","meta"}``).
        ``raw=True`` returns the response body as ``bytes`` (file downloads).
        """
        url = self.base_url + path
        headers: dict[str, str] = {"User-Agent": f"heroshots-python/{_sdk_version()}"}
        if not raw:
            headers["Accept"] = "application/json"
        if auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if auth and self.managed_user_id is not None:
            headers["X-Managed-User-Id"] = str(self.managed_user_id)
        if params:
            params = {k: v for k, v in params.items() if v is not None}

        attempt = 0
        while True:
            resp = self.session.request(
                method.upper(),
                url,
                headers=headers,
                json=json,
                params=params or None,
                files=files,
                data=data,
                timeout=self.timeout,
            )
            # 429 means the request was not processed: safe to retry, also for POST.
            # Multipart bodies are not retried (file handles are already consumed).
            if resp.status_code == 429 and attempt < self.max_retries and files is None:
                attempt += 1
                time.sleep(_retry_delay(resp, attempt))
                continue
            break

        if not resp.ok:
            body = _json_or_none(resp)
            err = error_from_response(resp.status_code, body)
            if isinstance(err, RateLimitError):
                err.retry_after = _retry_after_seconds(resp)
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
                    raw=raw,
                    _retried=True,
                )
            raise err

        if raw:
            return resp.content

        body = _json_or_none(resp)
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

    def download(
        self,
        path: str,
        dest: Optional[Union[str, os.PathLike]] = None,
        *,
        params: Optional[dict[str, Any]] = None,
    ) -> Union[bytes, str]:
        """GET a binary endpoint. Returns ``bytes``, or writes ``dest`` and returns its path."""
        content = self.request("GET", path, params=params, raw=True)
        if dest is None:
            return content
        target = Path(dest)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return str(target)

    @staticmethod
    def _file_tuple(file: FileInput, default_name: str = "file") -> Any:
        """Normalise a path / bytes / file object into a ``requests`` file value."""
        if isinstance(file, (str, os.PathLike)):
            p = Path(file)
            return (p.name, open(p, "rb"))  # noqa: SIM115 - requests reads it
        if isinstance(file, (bytes, bytearray)):
            return (default_name, bytes(file))
        name = getattr(file, "name", None)
        name = os.path.basename(name) if isinstance(name, str) else default_name
        return (name, file)

    @classmethod
    def _multipart_file(cls, file: FileInput, field: str = "file") -> dict[str, Any]:
        """Build a ``files=`` dict for ``requests`` from a path, bytes or open file."""
        return {field: cls._file_tuple(file)}


def _json_or_none(resp: requests.Response) -> Any:
    if not resp.content:
        return None
    try:
        return resp.json()
    except ValueError:
        return None


def _retry_after_seconds(resp: requests.Response) -> Optional[float]:
    value = resp.headers.get("Retry-After")
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None


def _retry_delay(resp: requests.Response, attempt: int) -> float:
    after = _retry_after_seconds(resp)
    if after is not None:
        return min(after, 60.0)
    return min(2.0 ** (attempt - 1), 30.0)


__all__ = ["HeroShotsClient", "DEFAULT_BASE_URL", "DEFAULT_TIMEOUT", "ApiError"]
