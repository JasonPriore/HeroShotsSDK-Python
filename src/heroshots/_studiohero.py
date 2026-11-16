"""StudioHero helpers: turn a storyboard into the fields the web portal sends.

Pure functions (no HTTP). They mirror the StudioHero web app (``src/App.jsx`` and
``src/utils/studioHeroVoiceCast.js`` in the portal) so that an SDK render is the
same request the portal makes:

* :func:`segment_prompts` -> ``studiohero_segment_prompts``
* :func:`segment_reference_image_urls` -> ``studiohero_segment_reference_image_urls``
* :func:`voice_roles` / :func:`voice_cast` -> ``voiceover_cast`` (one voice per role)
* :func:`storyboard_start_fields` -> the storyboard part of ``/long-video/start``
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Mapping, Optional, Union

# Avatar views the render accepts as ``avatar_view_type`` (backend avatar_prompt.py).
# "avatar" is not a view: the render answers "Selected avatar view is not available".
AVATAR_VIEW_TYPES = (
    "fullbody", "profile_left", "profile_right", "mezzo_busto", "closeup",
    "ear", "wrist", "feet", "bust_only", "legs_lower",
)
LOGO_MODES = ("in_video", "end_only", "off")
VIDEO_TYPES = ("ugc", "cinema", "spot_tv", "sas_software")
UGC_STYLES = ("amateur", "top_creator")

VoiceIds = Union[str, Mapping[str, str], None]

_EMPTY_LINE_RE = re.compile(
    r"^(?:nessuna\s+(?:battuta|frase)(?:\s+\S+)*|nessun(?:a)?\s+(?:voce|dialogo|parlato)(?:\s+\S+)*"
    r"|no\s+(?:spoken|dialogue|voiceover)(?:\s+\S+)*|none|n/a|-)\.?$",
    re.IGNORECASE,
)
_PRODUCTION_CONTROL_RE = re.compile(
    r"(?:^|\s+)(?:speak the line once\b|deliver the narration once\b"
    r"|timeline(?:\s*&\s*action plan|\s+directives)?\b|shot plan\b|speech\s*&\s*synchronization rule\b"
    r"|control frame target\b|seedance controls\s*:|refs\s*:|invariant\s*:|situational sound design\b"
    r"|guardrails\s*:|quality constraints\s*:|audio\s*/\s*lip-sync plan\s*:)",
    re.IGNORECASE,
)
# Timing / camera cues inside a spoken line: "(0s-5s on-camera) Line."
_INLINE_CUE_RE = re.compile(
    r"[\[(]\s*(?:\d+(?:[.,]\d+)?\s*s?\s*(?:-|–|—|to)\s*\d+(?:[.,]\d+)?\s*s(?:ec(?:onds?)?)?\b[^)\]\n]{0,40}"
    r"|(?:on|off)[\s-]*camera\b[^)\]\n]{0,30})[\])]\s*[:\-–—]?\s*",
    re.IGNORECASE,
)
_ORPHAN_CAMERA_CUE_RE = re.compile(r"^\s*(?:on|off)[\s-]*camera\s*[)\]]\s*[:\-–—]?\s*", re.IGNORECASE)
_ROLE_PREFIX_RE = re.compile(
    r"^[\"“'‘]?\s*(?:soggetto|subject|narratore|narrator|voice[ -]?over)(?:\s+\d+)?\s*:\s*[\"“'‘]?",
    re.IGNORECASE,
)
_ROLE_LABELS = {
    "subject_1": "Soggetto",
    "subject_2": "Soggetto 2",
    "subject_3": "Soggetto 3",
    "voice_over": "Narratore",
    "narrator": "Narratore",
}


# -- storyboard shape ----------------------------------------------------------


def unwrap_storyboard(storyboard: Any) -> dict:
    """Accept the storyboard itself or the ``storyboard.wait()`` payload (``{"storyboard": {...}}``)."""
    if not isinstance(storyboard, Mapping):
        return {}
    inner = storyboard.get("storyboard")
    if "segments" not in storyboard and isinstance(inner, Mapping):
        return dict(inner)
    return dict(storyboard)


def _segments(storyboard: Any) -> list:
    segments = unwrap_storyboard(storyboard).get("segments")
    return [s for s in segments if isinstance(s, Mapping)] if isinstance(segments, list) else []


def _sequence(segment: Mapping) -> Mapping:
    seq = segment.get("script_sequence")
    return seq if isinstance(seq, Mapping) else {}


def dedupe_urls(urls: Iterable[Any], *, allow_data_urls: bool = False) -> list[str]:
    """Trimmed, non-empty, first-seen order; ``data:`` URLs dropped (as the portal does)."""
    out: list[str] = []
    for url in urls:
        clean = str(url or "").strip()
        if not clean or clean in out:
            continue
        if not allow_data_urls and clean.lower().startswith("data:"):
            continue
        out.append(clean)
    return out


def segment_prompts(storyboard: Any) -> list[str]:
    """``visual_prompt`` (or ``seedance_prompt``) of every segment, empty ones skipped."""
    out = []
    for seg in _segments(storyboard):
        prompt = seg.get("visual_prompt") or seg.get("seedance_prompt")
        if prompt:
            out.append(prompt)
    return out


def segment_reference_image_urls(storyboard: Any) -> list[list[str]]:
    """Per segment: its ``reference_frames[].image_url`` plus ``control_frame.image_url``."""
    out = []
    for seg in _segments(storyboard):
        seq = _sequence(seg)
        urls: list[Any] = []
        frames = seq.get("reference_frames")
        for frame in frames if isinstance(frames, list) else []:
            if isinstance(frame, Mapping) and frame.get("image_url"):
                urls.append(frame["image_url"])
        control = seq.get("control_frame")
        if isinstance(control, Mapping) and control.get("image_url"):
            urls.append(control["image_url"])
        out.append(dedupe_urls(urls))
    return out


def storyboard_start_fields(storyboard: Any) -> dict[str, Any]:
    """The storyboard part of a portal render.

    ``custom_prompt`` (the storyboard's ``optimized_prompt``),
    ``studiohero_segment_prompts``, ``studiohero_segment_reference_image_urls``
    (only when at least one segment has frames) and ``duration_seconds``.
    """
    sb = unwrap_storyboard(storyboard)
    fields: dict[str, Any] = {}
    if sb.get("optimized_prompt"):
        fields["custom_prompt"] = sb["optimized_prompt"]
    prompts = segment_prompts(sb)
    if prompts:
        fields["studiohero_segment_prompts"] = prompts
    refs = segment_reference_image_urls(sb)
    if any(refs):
        fields["studiohero_segment_reference_image_urls"] = refs
    if sb.get("duration_seconds"):
        fields["duration_seconds"] = sb["duration_seconds"]
    return fields


# -- voice cast ----------------------------------------------------------------


def has_spoken_text(value: Any) -> bool:
    clean = str(value or "").strip()
    return bool(clean) and not _EMPTY_LINE_RE.match(clean)


def clean_spoken_text(value: Any) -> str:
    """Spoken line without production notes, timing cues, role prefix or wrapping quotes."""
    clean = str(value or "").strip()
    marker = _PRODUCTION_CONTROL_RE.search(clean)
    if marker:
        clean = clean[: marker.start()].strip()
    clean = _INLINE_CUE_RE.sub(" ", clean).strip()
    clean = _ORPHAN_CAMERA_CUE_RE.sub("", clean, count=1)
    clean = _ROLE_PREFIX_RE.sub("", clean, count=1)
    clean = re.sub(r"\s+", " ", clean)
    clean = re.sub(r"^[\"“'‘]+|[\"”'’]+$", "", clean)
    return clean.strip()


def role_key(value: Any, fallback: str = "subject_1") -> str:
    """Normalise a role id: ``""``/subject/soggetto -> subject_1, narrator/vo/... -> voice_over."""
    clean = re.sub(r"[\s-]+", "_", str(value or "").strip().lower())
    if not clean:
        return fallback
    if clean in ("subject", "soggetto"):
        return "subject_1"
    if clean in ("voiceover", "voice_over", "narrator", "narratore", "vo"):
        return "voice_over"
    match = re.match(r"^(?:subject|soggetto)_?(\d+)$", clean)
    if match:
        return f"subject_{match.group(1)}"
    return clean


def _role_key_from_label(label: Any) -> str:
    clean = str(label or "").lower()
    if "2" in clean:
        return "subject_2"
    if "3" in clean:
        return "subject_3"
    if "voice" in clean or "narrator" in clean or "narratore" in clean:
        return "voice_over"
    return "subject_1"


def _role_type(key: str) -> str:
    return "narrator" if key in ("voice_over", "narrator") else "subject"


def _fallback_label(key: str) -> str:
    if key in _ROLE_LABELS:
        return _ROLE_LABELS[key]
    match = re.match(r"^subject_(\d+)$", key)
    if match:
        return "Soggetto" if match.group(1) == "1" else f"Soggetto {match.group(1)}"
    return key


def _entry(raw: Any, fallback_index: int = 1) -> Optional[dict]:
    if not isinstance(raw, Mapping):
        return None
    key = role_key(raw.get("role_id") or raw.get("role") or raw.get("key"), f"subject_{fallback_index}")
    text = clean_spoken_text(raw.get("spoken_it") or raw.get("text") or raw.get("spoken_text"))
    if not has_spoken_text(text):
        return None
    label = str(raw.get("label_it") or raw.get("label") or _fallback_label(key)).strip() or _fallback_label(key)
    role_type = str(raw.get("role_type") or _role_type(key)).strip() or _role_type(key)
    return {
        "key": key,
        "label": label,
        "role_type": role_type,
        "text": text,
        "tts_text": clean_spoken_text(raw.get("tts_text")) or text,
    }


def _canonical_voiceover(value: Any) -> str:
    text = re.sub(r"(?:^|\s)(?:\(\d+\)|\d+[.)])\s*", "\n", str(value or ""))
    lines = []
    for line in re.split(r"\r?\n", text):
        line = re.sub(r"^[-*]\s*", "", line.strip()).strip()
        if len(line) >= 2 and line[0] in "\"'“‘" and line[-1] in "\"'”’":
            line = line[1:-1].strip()
        if line:
            lines.append(line)
    return clean_spoken_text(" ".join(lines))


def _text_key(value: Any) -> str:
    return re.sub(r"[\W_]+", " ", str(value or "").lower()).strip()


def _reconcile_single_role(segment: Mapping, entries: list) -> list:
    """A single role whose line is a cut of the segment's voiceover_text speaks the whole text."""
    if len(entries) != 1:
        return entries
    canonical = _canonical_voiceover(segment.get("voiceover_text"))
    canonical_key, current_key = _text_key(canonical), _text_key(entries[0]["text"])
    if not canonical_key or not current_key or len(canonical_key) <= len(current_key) or current_key not in canonical_key:
        return entries
    tags = re.match(r"^\s*((?:\[[^\]\r\n]{1,80}\]\s*)+)", str(entries[0].get("tts_text") or ""))
    tts = f"{tags.group(1).strip()} {canonical}" if tags else canonical
    return [{**entries[0], "text": canonical, "tts_text": tts}]


def _segment_entries(segment: Mapping) -> list:
    seq = _sequence(segment)
    cast = seq.get("voice_cast")
    if isinstance(cast, list):
        entries = [e for e in (_entry(raw, i + 1) for i, raw in enumerate(cast)) if e]
        if entries:
            return _reconcile_single_role(segment, entries)
    entries = []
    by_role = seq.get("spoken_by_role_it")
    if isinstance(by_role, Mapping):
        for key, text in by_role.items():
            entry = _entry({"role_id": key, "label_it": _fallback_label(role_key(key)), "spoken_it": text})
            if entry:
                entries.append(entry)
    else:
        fallback = str(seq.get("spoken_it") or segment.get("voiceover_text") or "").strip()
        if has_spoken_text(fallback):
            key = _role_key_from_label(seq.get("speaker_label_it"))
            entry = _entry({"role_id": key, "label_it": _fallback_label(key), "spoken_it": fallback})
            if entry:
                entries.append(entry)
    return _reconcile_single_role(segment, entries)


def _role_rank(role: dict) -> int:
    if role["key"] == "voice_over" or role["role_type"] == "narrator":
        return 900
    match = re.match(r"^subject_(\d+)$", role["key"])
    return int(match.group(1)) if match else 500


def voice_roles(storyboard: Any) -> list[dict[str, str]]:
    """Speaking roles of a storyboard, merged across segments.

    Each item: ``{"key", "label", "role_type", "text", "tts_text"}`` (``key`` is
    e.g. ``subject_1`` or ``voice_over``). Subjects first, the narrator last.
    """
    merged: dict[str, dict] = {}
    for seg in _segments(storyboard):
        for entry in _segment_entries(seg):
            role = merged.setdefault(
                entry["key"],
                {"key": entry["key"], "label": entry["label"], "role_type": entry["role_type"],
                 "texts": [], "tts_texts": []},
            )
            role["texts"].append(entry["text"])
            role["tts_texts"].append(entry["tts_text"] or entry["text"])
    roles = []
    for role in merged.values():
        texts: list[str] = []
        for text in role["texts"]:
            if has_spoken_text(text) and text not in texts:
                texts.append(text)
        text = " ".join(texts)
        if not has_spoken_text(text):
            continue
        roles.append({
            "key": role["key"],
            "label": role["label"],
            "role_type": role["role_type"],
            "text": text,
            "tts_text": " ".join(t for t in role["tts_texts"] if has_spoken_text(t)) or text,
        })
    roles.sort(key=lambda r: (_role_rank(r), r["label"]))
    return roles


def _voice_for(voice_ids: VoiceIds, key: str) -> str:
    if isinstance(voice_ids, Mapping):
        return str(voice_ids.get(key) or "").strip()
    return str(voice_ids or "").strip()


def voice_cast(storyboard: Any, voice_ids: VoiceIds = None) -> dict[str, dict[str, str]]:
    """``voiceover_cast`` for ``/long-video/start``: ``{role_key: {label, role_type, voice_id, text, tts_text}}``.

    ``voice_ids`` is one voice id for every role, or a mapping ``{role_key: voice_id}``
    (see :func:`voice_roles` for the keys). Roles without a voice get ``voice_id=""``.
    """
    return {
        role["key"]: {
            "label": role["label"],
            "role_type": role["role_type"],
            "voice_id": _voice_for(voice_ids, role["key"]),
            "text": role["text"],
            "tts_text": role["tts_text"] or role["text"],
        }
        for role in voice_roles(storyboard)
    }


def missing_voice_roles(storyboard: Any, voice_ids: VoiceIds = None) -> list[str]:
    """Role keys that speak in the storyboard but have no voice in ``voice_ids``."""
    return [r["key"] for r in voice_roles(storyboard) if not _voice_for(voice_ids, r["key"])]


def first_voice_id(cast: Any) -> Optional[str]:
    """Voice of the first role of a ``voiceover_cast`` mapping (the portal's ``tts_voice_id``)."""
    if isinstance(cast, Mapping):
        rows = list(cast.values())
    elif isinstance(cast, list):
        rows = cast
    else:
        return None
    for row in rows:
        if isinstance(row, Mapping) and str(row.get("voice_id") or "").strip():
            return str(row["voice_id"]).strip()
    return None


# -- recommendation options ----------------------------------------------------


def recommend_option(item: Any) -> dict[str, str]:
    """``{title, text}`` from a string, a brief suggestion (``{title, brief}``) or a concept candidate."""
    if not isinstance(item, Mapping):
        return {"title": "", "text": str(item or "")}
    title = str(item.get("title") or "")
    if item.get("text"):
        return {"title": title, "text": str(item["text"])}
    if item.get("brief"):
        return {"title": title, "text": str(item["brief"])}
    parts = [item.get("logline"), item.get("visual_direction")]
    clip_plan = item.get("clip_plan")
    if isinstance(clip_plan, list):
        parts.extend(clip_plan)
    return {"title": title, "text": " · ".join(str(p) for p in parts if p)}


__all__ = [
    "AVATAR_VIEW_TYPES",
    "LOGO_MODES",
    "UGC_STYLES",
    "VIDEO_TYPES",
    "clean_spoken_text",
    "dedupe_urls",
    "first_voice_id",
    "missing_voice_roles",
    "recommend_option",
    "role_key",
    "segment_prompts",
    "segment_reference_image_urls",
    "storyboard_start_fields",
    "unwrap_storyboard",
    "voice_cast",
    "voice_roles",
]
