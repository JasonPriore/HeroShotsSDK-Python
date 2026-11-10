"""Bulk image generation (API key or portal JWT, /api/v1/bulk).

Flow: ``create`` -> ``upload_images`` (one item per product photo) -> ``start``
-> ``wait`` -> ``download_generated`` (zip) or per-item ``download_item``.
"""

from __future__ import annotations

import os
import time
from typing import Any, Callable, Iterable, Optional, Union

from . import Resource, compact
from .._polling import TimeoutError as PollTimeoutError

BulkId = Union[int, str]
Dest = Optional[Union[str, os.PathLike]]

BULK_DONE = ("completed", "partially_completed", "failed")


class Bulk(Resource):
    def list(self) -> Any:
        """GET /api/v1/bulk -> your bulks."""
        return self._get("/api/v1/bulk")

    def create(
        self, *, prompt: Optional[str] = None, avatar_id: Optional[int] = None, **fields: Any
    ) -> dict[str, Any]:
        """POST /api/v1/bulk -> new draft bulk."""
        return self._post("/api/v1/bulk", json=compact({"prompt": prompt, "avatar_id": avatar_id, **fields}))

    def get(self, bulk_id: BulkId) -> dict[str, Any]:
        """GET /api/v1/bulk/<id> -> status, progress and items."""
        return self._get(f"/api/v1/bulk/{bulk_id}")

    def update(self, bulk_id: BulkId, **fields: Any) -> dict[str, Any]:
        """PATCH /api/v1/bulk/<id> -> prompt, avatar_id, view_type, avatar_image_set..."""
        return self._patch(f"/api/v1/bulk/{bulk_id}", json=fields)

    def delete(self, bulk_id: BulkId) -> dict[str, Any]:
        """DELETE /api/v1/bulk/<id>."""
        return self._delete(f"/api/v1/bulk/{bulk_id}")

    def upload_images(self, bulk_id: BulkId, files: Iterable[Any]) -> dict[str, Any]:
        """POST /api/v1/bulk/<id>/images (multipart ``files``) -> ``{uploaded, items}``.

        ``files`` are paths, bytes or open binary files.
        """
        parts = [("files", self._client._file_tuple(f, "image")) for f in files]
        return self._post(f"/api/v1/bulk/{bulk_id}/images", files=parts)

    def remove_item(self, bulk_id: BulkId, item_id: BulkId) -> dict[str, Any]:
        """DELETE /api/v1/bulk/<id>/items/<item_id>."""
        return self._delete(f"/api/v1/bulk/{bulk_id}/items/{item_id}")

    def replace_product(self, bulk_id: BulkId, item_id: BulkId, file: Any) -> dict[str, Any]:
        """POST /api/v1/bulk/<id>/items/<item_id>/replace-product (multipart ``file``)."""
        return self._post(
            f"/api/v1/bulk/{bulk_id}/items/{item_id}/replace-product",
            files=self._client._multipart_file(file),
        )

    def start(self, bulk_id: BulkId) -> dict[str, Any]:
        """POST /api/v1/bulk/<id>/start -> begins generation for every item."""
        return self._post(f"/api/v1/bulk/{bulk_id}/start")

    def cancel_item(self, bulk_id: BulkId, item_id: BulkId) -> dict[str, Any]:
        """POST /api/v1/bulk/<id>/items/<item_id>/cancel."""
        return self._post(f"/api/v1/bulk/{bulk_id}/items/{item_id}/cancel")

    def regenerate_item(
        self,
        bulk_id: BulkId,
        item_id: BulkId,
        *,
        prompt_override: Optional[str] = None,
        verify_until_ok: Optional[bool] = None,
        refine_last: Optional[bool] = None,
    ) -> dict[str, Any]:
        """POST /api/v1/bulk/<id>/items/<item_id>/regenerate."""
        body = compact(
            {
                "prompt_override": prompt_override,
                "verify_until_ok": verify_until_ok,
                "refine_last": refine_last,
            }
        )
        return self._post(f"/api/v1/bulk/{bulk_id}/items/{item_id}/regenerate", json=body)

    def regenerate_all(self, bulk_id: BulkId) -> dict[str, Any]:
        """POST /api/v1/bulk/<id>/regenerate-all."""
        return self._post(f"/api/v1/bulk/{bulk_id}/regenerate-all")

    def previews(self, bulk_id: BulkId) -> dict[str, Any]:
        """GET /api/v1/bulk/<id>/items/previews -> base64 previews per item."""
        return self._get(f"/api/v1/bulk/{bulk_id}/items/previews")

    def attempts(self, bulk_id: BulkId, item_id: BulkId) -> dict[str, Any]:
        """GET /api/v1/bulk/<id>/items/<item_id>/attempts."""
        return self._get(f"/api/v1/bulk/{bulk_id}/items/{item_id}/attempts")

    def select_attempt(self, bulk_id: BulkId, item_id: BulkId, attempt_index: int) -> dict[str, Any]:
        """POST /api/v1/bulk/<id>/items/<item_id>/attempts/select -> make it the official result."""
        return self._post(
            f"/api/v1/bulk/{bulk_id}/items/{item_id}/attempts/select",
            json={"attempt_index": attempt_index},
        )

    def download_product(self, bulk_id: BulkId, item_id: BulkId, dest: Dest = None) -> Union[bytes, str]:
        """GET /api/v1/bulk/<id>/items/<item_id>/download-product -> uploaded product image."""
        return self._client.download(f"/api/v1/bulk/{bulk_id}/items/{item_id}/download-product", dest)

    def download_item(self, bulk_id: BulkId, item_id: BulkId, dest: Dest = None) -> Union[bytes, str]:
        """GET /api/v1/bulk/<id>/items/<item_id>/download -> generated image."""
        return self._client.download(f"/api/v1/bulk/{bulk_id}/items/{item_id}/download", dest)

    def download_generated(
        self,
        bulk_id: BulkId,
        dest: Dest = None,
        *,
        item_ids: Optional[Iterable[BulkId]] = None,
    ) -> Union[bytes, str]:
        """GET /api/v1/bulk/<id>/download-generated -> zip of generated images."""
        params = {"item_ids": ",".join(str(i) for i in item_ids)} if item_ids else None
        return self._client.download(f"/api/v1/bulk/{bulk_id}/download-generated", dest, params=params)

    def wait(
        self,
        bulk_id: BulkId,
        *,
        interval: float = 10.0,
        timeout: float = 3600.0,
        on_progress: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> dict[str, Any]:
        """Poll until the bulk is ``completed``, ``partially_completed`` or ``failed``.

        Unlike single jobs, a failed bulk is returned (not raised): check
        ``status`` and the per-item results.
        """
        deadline = time.monotonic() + timeout
        while True:
            bulk = self.get(bulk_id)
            if on_progress is not None:
                on_progress(bulk)
            status = str(bulk.get("status") or "").lower()
            if status in BULK_DONE:
                return bulk
            if time.monotonic() >= deadline:
                raise PollTimeoutError(
                    f"bulk did not finish within {timeout:.0f}s (last status={status!r})"
                )
            time.sleep(interval)
