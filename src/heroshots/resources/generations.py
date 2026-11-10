"""Generation history (API key or portal JWT, /api/v1/generations)."""

from __future__ import annotations

from typing import Any, Iterator, Optional, Union

from . import Resource, compact


class Generations(Resource):
    def list(
        self,
        *,
        type: Optional[str] = None,  # noqa: A002 - mirrors the API field
        page: Optional[int] = None,
        per_page: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        collection_id: Optional[Union[int, str]] = None,
        generated_by_user_id: Optional[Union[int, str]] = None,
        **params: Any,
    ) -> dict[str, Any]:
        """GET /api/v1/generations -> ``{generations, total, page, per_page, pages}``.

        ``type`` filters images or videos (``"image"`` / ``"video"``).
        """
        query = compact(
            dict(
                type=type,
                page=page,
                per_page=per_page,
                date_from=date_from,
                date_to=date_to,
                collection_id=collection_id,
                generated_by_user_id=generated_by_user_id,
                **params,
            )
        )
        return self._get("/api/v1/generations", params=query or None)

    def iterate(self, *, per_page: int = 50, **filters: Any) -> Iterator[dict[str, Any]]:
        """Yield every generation across all pages (``page`` in filters is ignored)."""
        filters.pop("page", None)
        page = 1
        while True:
            resp = self.list(page=page, per_page=per_page, **filters)
            for item in resp.get("generations") or []:
                yield item
            pages = resp.get("pages") or 1
            if page >= pages:
                return
            page += 1
