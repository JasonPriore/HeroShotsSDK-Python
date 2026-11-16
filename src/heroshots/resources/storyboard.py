"""StudioHero storyboard intelligence (portal JWT only).

This is the creative brain the web app uses: brief suggestions -> selectable
candidates (+ the recommended one) -> full storyboard (async) -> deferred 4K
reference frames (async) -> optional board / revision. Feed the resulting
storyboard into ``client.longvideo.start_from_storyboard`` (the portal's render).

Request fields the portal sends with every storyboard call (pass them as keyword
arguments, they are forwarded verbatim):

* ``video_type``: ``"ugc"`` | ``"cinema"`` | ``"spot_tv"`` | ``"sas_software"``
* ``ugc_style``: ``"amateur"`` | ``"top_creator"``
* ``look_mode``: ``"current"`` (keep the subject's outfit) or ``"custom"`` with
  ``look_description``
* ``ratio``, ``resolution``, ``language_code`` (default ``"it"``), ``still_life``,
  ``reference_video_url``, ``video_provider``
* ``storyboard_reference_frames_required`` / ``storyboard_board_required``: whether
  the 4K reference frames / the storyboard board are part of the flow
* inputs: ``product_image_url``, ``subject_image_url``, ``avatar_id`` +
  ``avatar_view_type`` (a real view: ``fullbody``, ``mezzo_busto``, ``closeup``...),
  ``avatar_image_set``, ``additional_product_image_urls``, ``background_image_url``,
  ``body_posture_image_url``, ``brand_logo_url`` + ``brand_logo_mode``
  (``in_video`` | ``end_only`` | ``off``), ``product_box_closed_url`` /
  ``product_box_open_url``, ``extra_products`` (``[{"image_url", "box_closed_url"?,
  "box_open_url"?}]``)
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from . import Resource
from .. import _polling, _studiohero
from ..errors import ValidationError

# Valid durations accepted by the backend storyboard endpoints.
DURATIONS = (6, 8, 12, 15, 30, 45, 60)


class Storyboard(Resource):
    def brief_suggestions(
        self,
        product_image_url: Optional[str] = None,
        subject_image_url: Optional[str] = None,
        **payload: Any,
    ) -> list[str]:
        """POST /video/storyboard/brief-suggestions -> list of ``{title, brief, pros, cons}``.

        Pass ``brief["brief"]`` as ``custom_prompt`` to :meth:`candidates`.
        """
        body = self._image_body(product_image_url, subject_image_url, payload)
        resp = self._post("/video/storyboard/brief-suggestions", json=body)
        return resp.get("suggestions", resp) if isinstance(resp, dict) else resp

    def candidates(
        self,
        custom_prompt: str,
        duration_seconds: int,
        product_image_url: Optional[str] = None,
        subject_image_url: Optional[str] = None,
        *,
        async_storyboard: bool = False,
        **payload: Any,
    ) -> Any:
        """POST /video/storyboard/candidates -> selectable concept candidates.

        Set ``async_storyboard=True`` to get a ``{job_id}`` instead (poll with
        :meth:`wait`); otherwise returns the candidates inline.
        """
        body = self._image_body(product_image_url, subject_image_url, payload)
        body.update(custom_prompt=custom_prompt, duration_seconds=duration_seconds)
        if async_storyboard:
            body["async_storyboard"] = True
        resp = self._post("/video/storyboard/candidates", json=body)
        if isinstance(resp, dict) and "candidates" in resp:
            return resp["candidates"]
        return resp

    def generate(
        self,
        custom_prompt: str,
        duration_seconds: int,
        selected_candidate: Optional[dict] = None,
        product_image_url: Optional[str] = None,
        subject_image_url: Optional[str] = None,
        *,
        async_storyboard: bool = True,
        defer_reference_frames: bool = True,
        **payload: Any,
    ) -> dict[str, Any]:
        """POST /video/storyboard -> storyboard (async by default -> ``{job_id}``)."""
        body = self._image_body(product_image_url, subject_image_url, payload)
        body.update(
            custom_prompt=custom_prompt,
            duration_seconds=duration_seconds,
            async_storyboard=async_storyboard,
            defer_reference_frames=defer_reference_frames,
        )
        if selected_candidate is not None:
            body["selected_candidate"] = selected_candidate
        return self._post("/video/storyboard", json=body)

    def frames(
        self,
        storyboard: dict,
        product_image_url: Optional[str] = None,
        subject_image_url: Optional[str] = None,
        *,
        async_storyboard: bool = True,
        **payload: Any,
    ) -> dict[str, Any]:
        """POST /video/storyboard/frames -> renders deferred 4K reference frames.

        Sends the storyboard's ``segments`` (what the backend reads). The finished
        job (:meth:`wait`) carries the result under ``frames``
        (``{segments, reference_image_urls}``): use :meth:`merge` to put the frames
        back into the storyboard.
        """
        sb = _studiohero.unwrap_storyboard(storyboard)
        body = self._image_body(product_image_url, subject_image_url, payload)
        body.setdefault("segments", sb.get("segments") or [])
        if sb.get("selected_candidate") is not None:
            body.setdefault("selected_candidate", sb["selected_candidate"])
        if sb.get("duration_seconds"):
            body.setdefault("duration_seconds", sb["duration_seconds"])
        body["async_storyboard"] = async_storyboard
        return self._post("/video/storyboard/frames", json=body)

    def board(
        self,
        storyboard: dict,
        product_image_url: Optional[str] = None,
        subject_image_url: Optional[str] = None,
        *,
        async_storyboard: bool = True,
        **payload: Any,
    ) -> dict[str, Any]:
        """POST /video/storyboard/board -> the storyboard board image (async -> ``{job_id}``).

        The finished job carries ``board`` (``{storyboard_board_image_url, ...}``):
        :meth:`merge` adds it to the storyboard, and
        ``longvideo.start_from_storyboard`` sends it as the first reference image.
        """
        sb = _studiohero.unwrap_storyboard(storyboard)
        body = self._image_body(product_image_url, subject_image_url, payload)
        body.setdefault("segments", sb.get("segments") or [])
        if sb.get("selected_candidate") is not None:
            body.setdefault("selected_candidate", sb["selected_candidate"])
        if sb.get("duration_seconds"):
            body.setdefault("duration_seconds", sb["duration_seconds"])
        body.setdefault("storyboard_board_required", True)
        body["async_storyboard"] = async_storyboard
        return self._post("/video/storyboard/board", json=body)

    def recommend(
        self,
        kind: str,
        options: list,
        product_image_url: Optional[str] = None,
        subject_image_url: Optional[str] = None,
        *,
        chosen_brief: Optional[str] = None,
        **payload: Any,
    ) -> dict[str, Any]:
        """POST /video/storyboard/recommend -> ``{recommended_index, reason}``.

        ``kind`` is ``"brief"`` (``options`` = the brief suggestions) or
        ``"concept"`` (``options`` = the candidates; pass the chosen brief as
        ``chosen_brief``). Options can be strings, ``{title, text}``, brief
        suggestions or concept candidates (turned into ``{title, text}`` like the
        portal). Send the same fields as the storyboard call (``custom_prompt``,
        ``duration_seconds``, ``ratio``, ``video_type``, ``ugc_style``,
        ``language_code``...).
        """
        if kind not in ("brief", "concept"):
            raise ValidationError("recommend(kind): kind must be 'brief' or 'concept'", code="validation_error")
        body = self._image_body(product_image_url, subject_image_url, payload)
        body["kind"] = kind
        body["options"] = [_studiohero.recommend_option(item) for item in options or []]
        if chosen_brief:
            body["chosen_brief"] = chosen_brief
        return self._post("/video/storyboard/recommend", json=body)

    def revise(self, revision_request: str, custom_prompt: str, duration_seconds: int,
               storyboard: dict, **payload: Any) -> dict[str, Any]:
        """POST /video/storyboard/revise -> the revised storyboard (the response is the storyboard)."""
        body = {
            "revision_request": revision_request,
            "custom_prompt": custom_prompt,
            "duration_seconds": duration_seconds,
            "storyboard": storyboard,
            **payload,
        }
        return self._post("/video/storyboard/revise", json=body)

    def status(self, job_id: str) -> dict[str, Any]:
        """GET /video/storyboard/status/<job_id>."""
        return self._get(f"/video/storyboard/status/{job_id}")

    def wait(
        self,
        job_id: str,
        *,
        interval: float = 3.0,
        timeout: float = 300.0,
        on_progress: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> dict[str, Any]:
        """Poll a storyboard/frames job until ``done``/``failed``.

        ``on_progress`` receives each status payload (storyboard frame jobs expose
        ``frames_partial`` for progressive rendering).
        """
        return _polling.wait(
            lambda: self.status(job_id),
            terminal_ok=_polling.STORYBOARD_OK,
            terminal_fail=_polling.STORYBOARD_FAIL,
            interval=interval,
            timeout=timeout,
            on_progress=on_progress,
        )

    # -- portal helpers (no HTTP) ---------------------------------------------
    @staticmethod
    def merge(storyboard: dict, result: dict) -> dict[str, Any]:
        """Storyboard with the result of a :meth:`frames` or :meth:`board` job applied.

        ``result`` is the :meth:`wait` payload (``frames`` / ``board`` / ``storyboard``
        key) or the inner result. Returns a new dict.
        """
        sb = _studiohero.unwrap_storyboard(storyboard)
        res: Any = result if isinstance(result, dict) else {}
        if isinstance(res.get("frames"), dict):
            res = res["frames"]
        elif isinstance(res.get("board"), dict):
            res = res["board"]
        elif isinstance(res.get("storyboard"), dict) and "segments" not in res:
            return dict(res["storyboard"])
        segments = res.get("segments")
        if isinstance(segments, list) and segments:
            sb["segments"] = segments
            sb["reference_image_urls"] = res.get("reference_image_urls") or sb.get("reference_image_urls")
            sb["reference_frames_deferred"] = False
        board_url = str(res.get("storyboard_board_image_url") or "").strip()
        if board_url:
            sb["storyboard_board_enabled"] = res.get("storyboard_board_enabled") is not False
            sb["storyboard_board_deferred"] = False
            sb["storyboard_board_image_url"] = board_url
            sb["storyboard_board_duration_seconds"] = (
                res.get("storyboard_board_duration_seconds") or sb.get("duration_seconds")
            )
        return sb

    @staticmethod
    def segment_prompts(storyboard: dict) -> list[str]:
        """``studiohero_segment_prompts``: each segment's ``visual_prompt`` (or ``seedance_prompt``)."""
        return _studiohero.segment_prompts(storyboard)

    @staticmethod
    def segment_reference_image_urls(storyboard: dict) -> list[list[str]]:
        """``studiohero_segment_reference_image_urls``: reference + control frame URLs per segment."""
        return _studiohero.segment_reference_image_urls(storyboard)

    @staticmethod
    def voice_roles(storyboard: dict) -> list[dict[str, str]]:
        """Speaking roles (``[{key, label, role_type, text, tts_text}]``): pick a voice for each ``key``."""
        return _studiohero.voice_roles(storyboard)

    @staticmethod
    def voice_cast(storyboard: dict, voice_ids: Any = None) -> dict[str, dict[str, str]]:
        """``voiceover_cast`` for the render: ``{role_key: {label, role_type, voice_id, text, tts_text}}``.

        ``voice_ids``: one voice id for every role, or ``{role_key: voice_id}``.
        Voice ids come from ``client.audio.voices()``.
        """
        return _studiohero.voice_cast(storyboard, voice_ids)

    @staticmethod
    def missing_voice_roles(storyboard: dict, voice_ids: Any = None) -> list[str]:
        """Speaking roles without a voice (the portal refuses to render until there are none)."""
        return _studiohero.missing_voice_roles(storyboard, voice_ids)

    # -- creative helpers -----------------------------------------------------
    def subject_measurements(self, **payload: Any) -> dict[str, Any]:
        """POST /subject/estimate-measurements."""
        return self._post("/subject/estimate-measurements", json=payload)

    def analyze_product(self, **payload: Any) -> dict[str, Any]:
        """POST /product/analyze."""
        return self._post("/product/analyze", json=payload)

    def creativity(self, **payload: Any) -> dict[str, Any]:
        """POST /creativity/generate."""
        return self._post("/creativity/generate", json=payload)

    # -- internal -------------------------------------------------------------
    def _image_body(
        self,
        product_image_url: Optional[str],
        subject_image_url: Optional[str],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        body = dict(payload)
        if product_image_url is not None:
            body["product_image_url"] = self._resolve_image(product_image_url, "products")
        if subject_image_url is not None:
            body["subject_image_url"] = self._resolve_image(subject_image_url, "subjects")
        if "image_url" in body:
            body["image_url"] = self._resolve_image(body["image_url"], "references")
        return body
