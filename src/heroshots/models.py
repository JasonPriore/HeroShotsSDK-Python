"""Lightweight response wrapper.

The API returns plain JSON. :class:`AttrDict` wraps dict responses so callers can
use either ``result["video_url"]`` or ``result.video_url`` and still treat the
object as an ordinary dict. ``/api/v1`` billing metadata is exposed under ``_meta``.
"""

from __future__ import annotations

from typing import Any


class AttrDict(dict):
    """A dict that also supports attribute access (recursively)."""

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError as exc:  # pragma: no cover - mirrors AttributeError contract
            raise AttributeError(name) from exc

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


def wrap(value: Any) -> Any:
    """Recursively wrap dicts (and dicts inside lists) as :class:`AttrDict`."""
    if isinstance(value, AttrDict):
        return value
    if isinstance(value, dict):
        return AttrDict({k: wrap(v) for k, v in value.items()})
    if isinstance(value, list):
        return [wrap(v) for v in value]
    return value
