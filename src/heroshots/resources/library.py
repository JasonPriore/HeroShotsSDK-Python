"""Library: product assets, collections, backgrounds, categories (/api/v1)."""

from __future__ import annotations

from typing import Any, Optional, Union

from . import Resource, compact

Id = Union[int, str]


class Assets(Resource):
    """Product assets (``/api/v1/assets``)."""

    def list(self, *, category_id: Optional[Id] = None) -> dict[str, Any]:
        """GET /api/v1/assets."""
        return self._get("/api/v1/assets", params=compact({"category_id": category_id}) or None)

    def create(
        self,
        name: str,
        primary_image: Any,
        *,
        category_id: Optional[Id] = None,
        product_description: Optional[str] = None,
        product_details: Optional[str] = None,
    ) -> dict[str, Any]:
        """POST /api/v1/assets (multipart) -> new product asset.

        ``primary_image`` is a path, bytes or open binary file.
        """
        fields = compact(
            {
                "name": name,
                "category_id": category_id,
                "product_description": product_description,
                "product_details": product_details,
            }
        )
        return self._post(
            "/api/v1/assets",
            data={k: str(v) for k, v in fields.items()},
            files=self._client._multipart_file(primary_image, "primary_image"),
        )

    def import_amazon(self, url: str, *, language_code: Optional[str] = None) -> dict[str, Any]:
        """POST /api/v1/assets/import-amazon -> asset draft from an Amazon product URL."""
        return self._post(
            "/api/v1/assets/import-amazon", json=compact({"url": url, "language_code": language_code})
        )

    def get(self, asset_id: Id) -> dict[str, Any]:
        """GET /api/v1/assets/<id>."""
        return self._get(f"/api/v1/assets/{asset_id}")

    def update(self, asset_id: Id, **fields: Any) -> dict[str, Any]:
        """PATCH /api/v1/assets/<id> -> name, category_id, product_description..."""
        return self._patch(f"/api/v1/assets/{asset_id}", json=fields)

    def delete(self, asset_id: Id) -> dict[str, Any]:
        """DELETE /api/v1/assets/<id>."""
        return self._delete(f"/api/v1/assets/{asset_id}")

    def add_image(self, asset_id: Id, file: Any) -> dict[str, Any]:
        """POST /api/v1/assets/<id>/images (multipart ``file``) -> extra product photo."""
        return self._post(
            f"/api/v1/assets/{asset_id}/images", files=self._client._multipart_file(file)
        )

    def remove_image(self, asset_id: Id, image_id: Id) -> dict[str, Any]:
        """DELETE /api/v1/assets/<id>/images/<image_id>."""
        return self._delete(f"/api/v1/assets/{asset_id}/images/{image_id}")


class Collections(Resource):
    """Collections of generations (``/api/v1/collections``)."""

    def list(self, **params: Any) -> dict[str, Any]:
        """GET /api/v1/collections."""
        return self._get("/api/v1/collections", params=compact(params) or None)

    def create(
        self, name: str, *, description: Optional[str] = None, cover: Any = None
    ) -> dict[str, Any]:
        """POST /api/v1/collections (JSON, or multipart when a ``cover`` file is given)."""
        fields = compact({"name": name, "description": description})
        if cover is not None:
            return self._post(
                "/api/v1/collections",
                data=fields,
                files=self._client._multipart_file(cover, "cover"),
            )
        return self._post("/api/v1/collections", json=fields)

    def get(self, collection_id: Id) -> dict[str, Any]:
        """GET /api/v1/collections/<id>."""
        return self._get(f"/api/v1/collections/{collection_id}")

    def update(
        self,
        collection_id: Id,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        cover: Any = None,
    ) -> dict[str, Any]:
        """PATCH /api/v1/collections/<id> (multipart when a ``cover`` file is given)."""
        fields = compact({"name": name, "description": description})
        path = f"/api/v1/collections/{collection_id}"
        if cover is not None:
            return self._patch(path, data=fields, files=self._client._multipart_file(cover, "cover"))
        return self._patch(path, json=fields)

    def delete(self, collection_id: Id) -> dict[str, Any]:
        """DELETE /api/v1/collections/<id>."""
        return self._delete(f"/api/v1/collections/{collection_id}")

    def generations(self, collection_id: Id, **params: Any) -> dict[str, Any]:
        """GET /api/v1/collections/<id>/generations."""
        return self._get(
            f"/api/v1/collections/{collection_id}/generations", params=compact(params) or None
        )

    def add_generation(self, collection_id: Id, log_id: Id) -> dict[str, Any]:
        """POST /api/v1/collections/<id>/generations."""
        return self._post(
            f"/api/v1/collections/{collection_id}/generations", json={"log_id": int(log_id)}
        )

    def remove_generation(self, collection_id: Id, log_id: Id) -> dict[str, Any]:
        """DELETE /api/v1/collections/<id>/generations/<log_id>."""
        return self._delete(f"/api/v1/collections/{collection_id}/generations/{log_id}")

    def move_generation(self, collection_id: Id, log_id: Id, target_collection_id: Id) -> dict[str, Any]:
        """PATCH /api/v1/collections/<id>/generations/<log_id>/move."""
        return self._patch(
            f"/api/v1/collections/{collection_id}/generations/{log_id}/move",
            json={"target_collection_id": int(target_collection_id)},
        )

    def available_generations(self, collection_id: Id, **params: Any) -> dict[str, Any]:
        """GET /api/v1/collections/<id>/available-generations (``limit``, ``offset``)."""
        return self._get(
            f"/api/v1/collections/{collection_id}/available-generations",
            params=compact(params) or None,
        )


class Backgrounds(Resource):
    """Saved background images (``/api/v1/backgrounds``)."""

    def list(self, **params: Any) -> dict[str, Any]:
        """GET /api/v1/backgrounds (``limit``, ``offset``, ``q``)."""
        return self._get("/api/v1/backgrounds", params=compact(params) or None)

    def create(
        self,
        *,
        file: Any = None,
        image_url: Optional[str] = None,
        name: Optional[str] = None,
        source: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> dict[str, Any]:
        """POST /api/v1/backgrounds -> save a background from a ``file`` or ``image_url``."""
        fields = compact({"name": name, "source": source, "prompt": prompt, "image_url": image_url})
        if file is not None:
            return self._post(
                "/api/v1/backgrounds", data=fields, files=self._client._multipart_file(file)
            )
        return self._post("/api/v1/backgrounds", json=fields)

    def get(self, background_id: Id) -> dict[str, Any]:
        """GET /api/v1/backgrounds/<id>."""
        return self._get(f"/api/v1/backgrounds/{background_id}")

    def update(self, background_id: Id, **fields: Any) -> dict[str, Any]:
        """PATCH /api/v1/backgrounds/<id> (e.g. ``name``)."""
        return self._patch(f"/api/v1/backgrounds/{background_id}", json=fields)

    def delete(self, background_id: Id) -> dict[str, Any]:
        """DELETE /api/v1/backgrounds/<id>."""
        return self._delete(f"/api/v1/backgrounds/{background_id}")


class Categories(Resource):
    """Product categories (``/api/v1/categories``)."""

    def list(self) -> Any:
        """GET /api/v1/categories -> active categories."""
        return self._get("/api/v1/categories")

    def selected(self) -> dict[str, Any]:
        """GET /api/v1/categories/selected -> categories chosen for this account."""
        return self._get("/api/v1/categories/selected")

    def set_selected(self, category_ids: list[Id]) -> dict[str, Any]:
        """POST /api/v1/categories/selected."""
        return self._post(
            "/api/v1/categories/selected", json={"category_ids": [int(c) for c in category_ids]}
        )
