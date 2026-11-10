"""Avatars (API key or portal JWT, /api/v1/avatar)."""

from __future__ import annotations

import os
from typing import Any, Optional, Union

from . import Resource, compact

AvatarId = Union[int, str]

# Photo views accepted by the avatar endpoints.
VIEW_TYPES = ("closeup", "fullbody", "profile", "back", "profile_left", "profile_right", "mez")


class Avatars(Resource):
    # -- read ---------------------------------------------------------------------
    def list(self, **params: Any) -> dict[str, Any]:
        """GET /api/v1/avatar/list -> ``{avatars, total, page, pages, counts, ...}``.

        Filters: ``gender``, ``nationality``, ``min_age``, ``max_age``,
        ``avatar_type``, ``category_id``, ``q``, ``tab``, ``page``, ``per_page``.
        """
        return self._get("/api/v1/avatar/list", params=compact(params) or None)

    def get(self, avatar_id: AvatarId) -> dict[str, Any]:
        """GET /api/v1/avatar/<id>."""
        return self._get(f"/api/v1/avatar/{avatar_id}")

    def consent_document(
        self,
        avatar_id: AvatarId,
        dest: Optional[Union[str, os.PathLike]] = None,
        *,
        kind: Optional[str] = None,
    ) -> Union[bytes, str]:
        """GET /api/v1/avatar/<id>/consent-document -> signed consent (DOCX bytes or file)."""
        params = {"kind": kind} if kind else None
        return self._client.download(f"/api/v1/avatar/{avatar_id}/consent-document", dest, params=params)

    # -- create ---------------------------------------------------------------------
    def generate(self, name: Optional[str] = None, **payload: Any) -> dict[str, Any]:
        """POST /api/v1/avatar/generate -> new avatar (AI or from ``image_url``).

        AI: ``generate_with_ai=True`` + ``prompt`` (and ``gender``, ``age``,
        ``nationality``, body measurements). Real person: ``image_url`` plus
        ``release_doc_url``, ``id_doc_url``, ``model_email``, ``model_dob``.
        """
        body = dict(payload)
        if name is not None:
            body["name"] = name
        if "image_url" in body:
            body["image_url"] = self._resolve_image(body["image_url"], "avatars")
        return self._post("/api/v1/avatar/generate", json=body)

    def create_from_steps(
        self, name: str, images_by_view: dict[str, str], **payload: Any
    ) -> dict[str, Any]:
        """POST /api/v1/avatar/create-from-steps -> avatar from one photo per view."""
        views = {k: self._resolve_image(v, "avatars") for k, v in images_by_view.items()}
        return self._post(
            "/api/v1/avatar/create-from-steps",
            json={"name": name, "images_by_view": views, **payload},
        )

    def improve_prompt(self, prompt: str, **payload: Any) -> dict[str, Any]:
        """POST /api/v1/avatar/improve-prompt -> ``{improved_prompt}``."""
        return self._post("/api/v1/avatar/improve-prompt", json={"prompt": prompt, **payload})

    def analyze_attributes(self, prompt: str) -> dict[str, Any]:
        """POST /api/v1/avatar/analyze-attributes -> gender/age/nationality inferred from text."""
        return self._post("/api/v1/avatar/analyze-attributes", json={"prompt": prompt})

    # -- edit ---------------------------------------------------------------------
    def update(self, avatar_id: AvatarId, **fields: Any) -> dict[str, Any]:
        """PATCH /api/v1/avatar/<id> -> name, age, gender, nationality, measurements..."""
        return self._patch(f"/api/v1/avatar/{avatar_id}", json=fields)

    def delete(self, avatar_id: AvatarId) -> dict[str, Any]:
        """DELETE /api/v1/avatar/<id>."""
        return self._delete(f"/api/v1/avatar/{avatar_id}")

    def upload_view(self, avatar_id: AvatarId, view_type: str, image_url: str) -> dict[str, Any]:
        """POST /api/v1/avatar/<id>/upload-view -> add/replace one photo view."""
        return self._post(
            f"/api/v1/avatar/{avatar_id}/upload-view",
            json={"view_type": view_type, "image_url": self._resolve_image(image_url, "avatars")},
        )

    def regenerate_view(
        self,
        avatar_id: AvatarId,
        view_type: str,
        *,
        prompt: Optional[str] = None,
        output_style: Optional[str] = None,
    ) -> dict[str, Any]:
        """POST /api/v1/avatar/<id>/regenerate-view (async, 202)."""
        body = compact({"view_type": view_type, "prompt": prompt, "output_style": output_style})
        return self._post(f"/api/v1/avatar/{avatar_id}/regenerate-view", json=body)

    def regenerate_variants(
        self, avatar_id: AvatarId, *, output_style: Optional[str] = None
    ) -> dict[str, Any]:
        """POST /api/v1/avatar/<id>/regenerate-variants (async, 202)."""
        body = compact({"output_style": output_style})
        return self._post(f"/api/v1/avatar/{avatar_id}/regenerate-variants", json=body)

    def generated_version(
        self,
        avatar_id: AvatarId,
        *,
        prompt: Optional[str] = None,
        extra_reference_urls: Optional[list[str]] = None,
        output_style: Optional[str] = None,
    ) -> dict[str, Any]:
        """POST /api/v1/avatar/<id>/generated-version -> AI version of a photo avatar (async)."""
        body = compact(
            {
                "prompt": prompt,
                "extra_reference_urls": extra_reference_urls,
                "output_style": output_style,
            }
        )
        return self._post(f"/api/v1/avatar/{avatar_id}/generated-version", json=body)

    def set_image_set(self, avatar_id: AvatarId, mode: str) -> dict[str, Any]:
        """POST /api/v1/avatar/<id>/image-set -> use ``original`` or ``generated`` photos."""
        return self._post(f"/api/v1/avatar/{avatar_id}/image-set", json={"mode": mode})

    def generate_sheet(
        self,
        avatar_id: AvatarId,
        *,
        force: Optional[bool] = None,
        prompt: Optional[str] = None,
        output_style: Optional[str] = None,
    ) -> dict[str, Any]:
        """POST /api/v1/avatar/<id>/generate-avatar-sheet (``force=True`` regenerates)."""
        body = compact({"force": force, "prompt": prompt, "output_style": output_style})
        return self._post(f"/api/v1/avatar/{avatar_id}/generate-avatar-sheet", json=body)

    def generate_voice(
        self,
        avatar_id: AvatarId,
        *,
        generation_note: Optional[str] = None,
        force: Optional[bool] = None,
    ) -> dict[str, Any]:
        """POST /api/v1/avatar/<id>/generate-voice -> avatar voice (async, 202)."""
        body = compact({"generation_note": generation_note, "force": force})
        return self._post(f"/api/v1/avatar/{avatar_id}/generate-voice", json=body)

    # -- outfit ---------------------------------------------------------------------
    def resolve_outfit_link(self, url: str) -> dict[str, Any]:
        """POST /api/v1/avatar/outfit/resolve-link -> ``{url, title, image_urls}``."""
        return self._post("/api/v1/avatar/outfit/resolve-link", json={"url": url})

    def change_outfit(
        self,
        avatar_id: AvatarId,
        items: list[dict[str, Any]],
        *,
        regenerate_views: Optional[bool] = None,
    ) -> dict[str, Any]:
        """POST /api/v1/avatar/<id>/outfit -> dress the avatar (1-6 items).

        Each item: ``slot`` (hat | top | belt | pants | shoes | accessories) plus
        one of ``image_url``, ``link_url`` (shop page) or ``description``.
        ``regenerate_views`` defaults to True on the server.
        """
        body = compact({"items": items, "regenerate_views": regenerate_views})
        return self._post(f"/api/v1/avatar/{avatar_id}/outfit", json=body)

    def restore_outfit(self, avatar_id: AvatarId) -> dict[str, Any]:
        """POST /api/v1/avatar/<id>/outfit/restore -> undo the last outfit change."""
        return self._post(f"/api/v1/avatar/{avatar_id}/outfit/restore", json={})
