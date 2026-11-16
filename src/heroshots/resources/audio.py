"""Voices for the video voiceover (portal JWT only)."""

from __future__ import annotations

from typing import Any

from . import Resource


class Audio(Resource):
    def voices(self) -> dict[str, Any]:
        """GET /audio/voices -> ``{configured, voices: [{voice_id, name, category, labels, description, preview_url}]}``.

        The voices the StudioHero voice picker offers. Pass a ``voice_id`` (one, or
        one per speaking role) to ``longvideo.start_from_storyboard(voice_id=...)``
        or ``storyboard.voice_cast()``. ``configured`` is false (and ``voices``
        empty) when no voice provider is set up.
        """
        return self._get("/audio/voices")
