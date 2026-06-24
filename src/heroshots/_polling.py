"""Generic async-job polling helper.

The backend has three async surfaces with **inconsistent** terminal-state names:

* storyboard jobs and long-video jobs:  success = ``done``,       fail = ``failed``
* single video / image status:          success = ``succeeded``,  fail = ``failed``

Each resource passes the right state sets to :func:`wait`.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Iterable, Optional

from .errors import ProviderError, HeroShotsError


class TimeoutError(HeroShotsError):
    """Polling exceeded the allotted timeout."""


# Default terminal states, lower-cased for comparison.
STORYBOARD_OK = ("done", "succeeded", "completed")
STORYBOARD_FAIL = ("failed", "error", "cancelled", "canceled")
MEDIA_OK = ("succeeded", "done", "completed")
MEDIA_FAIL = ("failed", "error", "cancelled", "canceled")


def wait(
    get_fn: Callable[[], dict[str, Any]],
    *,
    terminal_ok: Iterable[str] = STORYBOARD_OK,
    terminal_fail: Iterable[str] = STORYBOARD_FAIL,
    status_key: str = "status",
    interval: float = 3.0,
    timeout: float = 600.0,
    on_progress: Optional[Callable[[dict[str, Any]], None]] = None,
) -> dict[str, Any]:
    """Poll ``get_fn`` until the job reaches a terminal state.

    Returns the final status payload on success. Raises :class:`ProviderError`
    on a failed job and :class:`TimeoutError` if the deadline passes.
    """
    ok = {s.lower() for s in terminal_ok}
    fail = {s.lower() for s in terminal_fail}
    deadline = time.monotonic() + timeout
    while True:
        payload = get_fn()
        if on_progress is not None:
            on_progress(payload)
        status = str(payload.get(status_key) or "").lower()
        if status in ok:
            return payload
        if status in fail:
            err = payload.get("error") or {}
            if isinstance(err, dict):
                raise ProviderError(
                    err.get("message") or f"job {status}",
                    code=err.get("code") or "provider_error",
                    details=err if err else None,
                )
            raise ProviderError(str(err) or f"job {status}", code="provider_error")
        if time.monotonic() >= deadline:
            raise TimeoutError(f"job did not finish within {timeout:.0f}s (last status={status!r})")
        time.sleep(interval)
