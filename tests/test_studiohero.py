"""StudioHero portal parity: storyboard -> render fields, voices, montage, downloads."""

import json

import pytest
import responses

from heroshots import HeroShotsClient, ValidationError, __version__

BASE = "https://api.test"


def jwt_client():
    return HeroShotsClient(BASE, token="jwt", auto_relogin=False)


def ok(data):
    return {"success": True, "data": data}


def body_of(call):
    return json.loads(call.request.body)


def storyboard():
    return {
        "duration_seconds": 30,
        "optimized_prompt": "OPTIMIZED PROMPT",
        "storyboard_board_image_url": "https://cdn/board.png",
        "segments": [
            {
                "index": 1,
                "visual_prompt": "seg 1 visual",
                "seedance_prompt": "seg 1 seedance",
                "voiceover_text": "Ciao a tutti.",
                "script_sequence": {
                    "reference_frames": [
                        {"role": "start", "image_url": "https://cdn/f1.png"},
                        {"role": "mid", "image_url": "https://cdn/f1.png"},
                        {"role": "end", "image_url": ""},
                    ],
                    "control_frame": {"image_url": "https://cdn/c1.png"},
                    "voice_cast": [
                        {"role_id": "soggetto", "label_it": "Soggetto", "spoken_it": "Ciao a tutti."},
                        {"role": "narratore", "text": "Scopri la novità.", "tts_text": "[warm] Scopri la novità."},
                    ],
                },
            },
            {
                "index": 2,
                "seedance_prompt": "seg 2 seedance",
                "script_sequence": {
                    "voice_cast": [
                        {"key": "subject", "spoken_it": "Ciao a tutti."},
                        {"role_id": "VO", "spoken_it": "Solo da noi."},
                    ],
                },
            },
            {
                "index": 3,
                "visual_prompt": "seg 3 visual",
                "script_sequence": {"spoken_it": "Nessuna battuta"},
            },
        ],
    }


# -- 1. start(storyboard=...) ---------------------------------------------------


@responses.activate
def test_start_storyboard_sends_portal_fields_not_raw_storyboard():
    responses.post(f"{BASE}/api/v1/long-video/start", json=ok({"job_id": 7}), status=202)
    jwt_client().longvideo.start(product_image_url="https://cdn/p.jpg", storyboard=storyboard())
    body = body_of(responses.calls[-1])
    assert "storyboard" not in body
    assert body["custom_prompt"] == "OPTIMIZED PROMPT"
    assert body["studiohero_segment_prompts"] == ["seg 1 visual", "seg 2 seedance", "seg 3 visual"]
    assert body["studiohero_segment_reference_image_urls"] == [
        ["https://cdn/f1.png", "https://cdn/c1.png"], [], [],
    ]
    assert body["duration_seconds"] == 30
    assert body["product_image_url"] == "https://cdn/p.jpg"


@responses.activate
def test_start_storyboard_explicit_kwargs_win_and_wait_payload_accepted():
    responses.post(f"{BASE}/api/v1/long-video/start", json=ok({"job_id": 7}), status=202)
    jwt_client().longvideo.start(
        storyboard={"status": "done", "storyboard": storyboard()},
        custom_prompt="mine",
        duration_seconds=45,
        studiohero_segment_prompts=["a", "b", "c"],
    )
    body = body_of(responses.calls[-1])
    assert body["custom_prompt"] == "mine"
    assert body["duration_seconds"] == 45
    assert body["studiohero_segment_prompts"] == ["a", "b", "c"]
    assert "storyboard" not in body


@responses.activate
def test_start_storyboard_omits_segment_refs_when_no_frames():
    responses.post(f"{BASE}/api/v1/long-video/start", json=ok({"job_id": 7}), status=202)
    sb = {"optimized_prompt": "p", "segments": [{"visual_prompt": "v1"}, {"visual_prompt": "v2"}]}
    jwt_client().longvideo.start(storyboard=sb)
    body = body_of(responses.calls[-1])
    assert "studiohero_segment_reference_image_urls" not in body
    assert body["studiohero_segment_prompts"] == ["v1", "v2"]


@responses.activate
def test_start_accepts_montage_and_voiceover_cast():
    responses.post(f"{BASE}/api/v1/long-video/start", json=ok({"job_id": 7}), status=202)
    cast = {"subject_1": {"label": "Soggetto", "role_type": "subject", "voice_id": "v1", "text": "x", "tts_text": "x"}}
    jwt_client().longvideo.start(
        image_url="https://cdn/p.jpg",
        montage={"brief": "b", "logo_mode": "off"},
        voiceover_cast=cast,
        language_code="it",
    )
    body = body_of(responses.calls[-1])
    assert body["montage"] == {"brief": "b", "logo_mode": "off"}
    assert body["voiceover_cast"] == cast
    assert body["tts_voice_id"] == "v1"
    assert body["language_code"] == "it"


# -- 2. download absolute URLs --------------------------------------------------


@responses.activate
def test_download_absolute_cdn_url_without_token(tmp_path):
    url = "https://cdn.example.com/long_video/final.mp4"
    responses.get(url, body=b"mp4")
    client = HeroShotsClient(BASE, token="jwt", managed_user_id=9, auto_relogin=False)
    saved = client.download(url, tmp_path / "v.mp4")
    assert open(saved, "rb").read() == b"mp4"
    req = responses.calls[-1].request
    assert req.url == url
    assert "Authorization" not in req.headers
    assert "X-Managed-User-Id" not in req.headers


@responses.activate
def test_download_absolute_url_on_api_host_sends_token():
    url = f"{BASE}/image/proxy/long_video/5/final.mp4"
    responses.get(url, body=b"mp4")
    assert jwt_client().download(url) == b"mp4"
    assert responses.calls[-1].request.headers["Authorization"] == "Bearer jwt"


@responses.activate
def test_download_other_scheme_or_port_is_not_the_api_host():
    responses.get("http://api.test/x.mp4", body=b"a")
    responses.get("https://api.test:8443/x.mp4", body=b"b")
    client = jwt_client()
    client.download("http://api.test/x.mp4")
    assert "Authorization" not in responses.calls[-1].request.headers
    client.download("https://api.test:8443/x.mp4")
    assert "Authorization" not in responses.calls[-1].request.headers


@responses.activate
def test_download_relative_path_still_prefixes_base_url():
    responses.get(f"{BASE}/api/v1/video/3/download", body=b"v")
    assert jwt_client().download("/api/v1/video/3/download") == b"v"
    assert responses.calls[-1].request.headers["Authorization"] == "Bearer jwt"


# -- 3. montage -----------------------------------------------------------------


@responses.activate
def test_montage_posts_fields_and_returns_needs_export():
    responses.post(f"{BASE}/api/auth/long-video/5/montage",
                   json={"job_id": 5, "status": "segments_ready", "needs_export": True}, status=200)
    out = jwt_client().longvideo.montage(5, brief="Sconto 20%", language_code="it", logo_mode="end_only",
                                         inserts=[{"url": "https://cdn/app.png", "label": "App"}])
    assert out["needs_export"] is True
    assert body_of(responses.calls[-1]) == {
        "brief": "Sconto 20%", "language_code": "it", "logo_mode": "end_only",
        "inserts": [{"url": "https://cdn/app.png", "label": "App"}],
    }


@responses.activate
def test_montage_without_fields_sends_empty_object():
    responses.post(f"{BASE}/api/auth/long-video/5/montage", json={"status": "captioning"}, status=202)
    assert jwt_client().longvideo.montage(5)["status"] == "captioning"
    assert body_of(responses.calls[-1]) == {}


@responses.activate
def test_montage_available():
    responses.get(f"{BASE}/api/auth/studio/montage-availability", json={"available": True})
    assert jwt_client().longvideo.montage_available() is True


@responses.activate
def test_render_waits_for_montage_done(monkeypatch):
    monkeypatch.setattr("heroshots.resources.longvideo.time.sleep", lambda s: None)
    status = f"{BASE}/api/v1/long-video/status/5"
    m = {"montage_requested": True}
    responses.get(status, json=ok({"status": "segments_ready", **m, "montage_pending": True}))
    responses.post(f"{BASE}/api/auth/long-video/5/export", json={"status": "concatenating"}, status=202)
    responses.get(status, json=ok({"status": "concatenating", **m, "montage_pending": True}))
    # Short gap: the export is done, the auto-edit has not started yet.
    responses.get(status, json=ok({"status": "done", "final_video_url": "https://cdn/final.mp4",
                                   **m, "montage_pending": True, "montage_done": False}))
    responses.get(status, json=ok({"status": "captioning", "final_video_url": "https://cdn/final.mp4",
                                   **m, "montage_pending": True, "montage_progress": {"stage": "render"}}))
    responses.get(status, json=ok({"status": "done", "final_video_url": "https://cdn/final.mp4",
                                   "captioned_final_video_url": "https://cdn/montage.mp4",
                                   **m, "montage_pending": False, "montage_done": True}))
    out = jwt_client().longvideo.render(5, interval=0, timeout=5)
    assert out["captioned_final_video_url"] == "https://cdn/montage.mp4"
    assert out["montage_done"] is True
    assert len([c for c in responses.calls if "/status/" in c.request.url]) == 5


@responses.activate
def test_wait_keeps_polling_a_done_job_while_montage_runs():
    status = f"{BASE}/api/v1/long-video/status/5"
    responses.get(status, json=ok({"status": "done", "final_video_url": "https://cdn/f.mp4",
                                   "montage_requested": True, "montage_pending": True}))
    responses.get(status, json=ok({"status": "captioning", "montage_requested": True, "montage_pending": True}))
    responses.get(status, json=ok({"status": "done", "final_video_url": "https://cdn/f.mp4",
                                   "captioned_final_video_url": "https://cdn/m.mp4",
                                   "montage_requested": True, "montage_done": True}))
    out = jwt_client().longvideo.wait(5, interval=0, timeout=5)
    assert out["captioned_final_video_url"] == "https://cdn/m.mp4"


@responses.activate
def test_render_returns_when_montage_failed():
    status = f"{BASE}/api/v1/long-video/status/5"
    responses.get(status, json=ok({"status": "done", "final_video_url": "https://cdn/f.mp4",
                                   "montage_requested": True, "montage_pending": False, "montage_done": False,
                                   "montage_report": {"error": "boom"}}))
    out = jwt_client().longvideo.render(5, interval=0, timeout=5)
    assert out["final_video_url"] == "https://cdn/f.mp4"
    assert out["montage_report"]["error"] == "boom"
    assert not [c for c in responses.calls if c.request.url.endswith("/export")]


# -- 4. voices ------------------------------------------------------------------


def test_voice_roles_merge_and_normalise():
    client = jwt_client()
    roles = client.storyboard.voice_roles(storyboard())
    assert [r["key"] for r in roles] == ["subject_1", "voice_over"]
    subject, narrator = roles
    assert subject == {"key": "subject_1", "label": "Soggetto", "role_type": "subject",
                       "text": "Ciao a tutti.", "tts_text": "Ciao a tutti. Ciao a tutti."}
    assert narrator["role_type"] == "narrator"
    assert narrator["label"] == "Narratore"
    assert narrator["text"] == "Scopri la novità. Solo da noi."
    assert narrator["tts_text"] == "[warm] Scopri la novità. Solo da noi."


def test_voice_cast_with_one_voice_or_per_role():
    client = jwt_client()
    cast = client.storyboard.voice_cast(storyboard(), "voice-A")
    assert set(cast) == {"subject_1", "voice_over"}
    assert all(row["voice_id"] == "voice-A" for row in cast.values())
    cast = client.storyboard.voice_cast(storyboard(), {"subject_1": "s", "voice_over": "n"})
    assert cast["subject_1"]["voice_id"] == "s" and cast["voice_over"]["voice_id"] == "n"
    assert client.storyboard.missing_voice_roles(storyboard(), {"subject_1": "s"}) == ["voice_over"]


def test_voice_cast_legacy_fallbacks():
    client = jwt_client()
    by_role = {"segments": [{"script_sequence": {"spoken_by_role_it": {"soggetto_2": "Io!", "narrator": "Lui."}}}]}
    roles = client.storyboard.voice_roles(by_role)
    assert [(r["key"], r["text"]) for r in roles] == [("subject_2", "Io!"), ("voice_over", "Lui.")]
    assert roles[0]["label"] == "Soggetto 2"
    spoken = {"segments": [{"script_sequence": {"spoken_it": "\"Prova questo.\""}},
                           {"voiceover_text": "Davvero."}]}
    roles = client.storyboard.voice_roles(spoken)
    assert roles == [{"key": "subject_1", "label": "Soggetto", "role_type": "subject",
                      "text": "Prova questo. Davvero.", "tts_text": "Prova questo. Davvero."}]
    assert client.storyboard.voice_roles({"segments": [{"voiceover_text": "none"}]}) == []


def test_clean_spoken_text_drops_cues_and_production_notes():
    from heroshots._studiohero import clean_spoken_text

    assert clean_spoken_text("(0s-5s on-camera) Ciao! Shot plan: close up") == "Ciao!"
    assert clean_spoken_text("Soggetto: \"Eccomi\"") == "Eccomi"


@responses.activate
def test_audio_voices():
    payload = {"configured": True, "voices": [{"voice_id": "v1", "name": "Giulia", "category": "premade",
                                               "labels": {}, "description": "", "preview_url": ""}]}
    responses.get(f"{BASE}/audio/voices", json=payload)
    out = jwt_client().audio.voices()
    assert out["voices"][0]["voice_id"] == "v1"
    assert responses.calls[-1].request.method == "GET"


# -- 5. recommend ---------------------------------------------------------------


@responses.activate
def test_recommend_concept_builds_portal_options():
    responses.post(f"{BASE}/video/storyboard/recommend", json={"recommended_index": 1, "reason": "best fit"})
    candidates = [
        {"title": "A", "logline": "la", "visual_direction": "va", "clip_plan": ["c1", "c2"]},
        {"title": "B", "logline": "lb"},
    ]
    out = jwt_client().storyboard.recommend(
        "concept", candidates, product_image_url="https://cdn/p.jpg",
        chosen_brief="il brief", duration_seconds=30, video_type="ugc",
    )
    assert out["recommended_index"] == 1
    body = body_of(responses.calls[-1])
    assert body["kind"] == "concept"
    assert body["options"] == [{"title": "A", "text": "la · va · c1 · c2"}, {"title": "B", "text": "lb"}]
    assert body["chosen_brief"] == "il brief"
    assert body["product_image_url"] == "https://cdn/p.jpg"
    assert body["video_type"] == "ugc"


@responses.activate
def test_recommend_brief_options_from_suggestions():
    responses.post(f"{BASE}/video/storyboard/recommend", json={"recommended_index": 0, "reason": "r"})
    jwt_client().storyboard.recommend("brief", [{"title": "T", "brief": "B1"}, "B2"])
    assert body_of(responses.calls[-1])["options"] == [{"title": "T", "text": "B1"}, {"title": "", "text": "B2"}]
    assert "chosen_brief" not in body_of(responses.calls[-1])


def test_recommend_rejects_unknown_kind():
    with pytest.raises(ValidationError):
        jwt_client().storyboard.recommend("logo", ["a", "b"])


# -- frames / board / merge -----------------------------------------------------


@responses.activate
def test_frames_and_board_send_segments():
    responses.post(f"{BASE}/video/storyboard/frames", json={"job_id": "f1"}, status=202)
    responses.post(f"{BASE}/video/storyboard/board", json={"job_id": "b1"}, status=202)
    client = jwt_client()
    sb = storyboard()
    client.storyboard.frames({"storyboard": sb}, product_image_url="https://cdn/p.jpg")
    body = body_of(responses.calls[0])
    assert body["segments"] == sb["segments"]
    assert body["async_storyboard"] is True and body["duration_seconds"] == 30
    client.storyboard.board(sb, video_type="ugc")
    body = body_of(responses.calls[1])
    assert body["segments"] == sb["segments"]
    assert body["storyboard_board_required"] is True


def test_merge_frames_and_board_results():
    client = jwt_client()
    sb = {"duration_seconds": 30, "segments": [{"index": 1}], "reference_frames_deferred": True}
    frames_job = {"status": "done", "frames": {"segments": [{"index": 1, "script_sequence": {
        "reference_frames": [{"image_url": "https://cdn/f.png"}]}}], "reference_image_urls": ["https://cdn/f.png"]}}
    merged = client.storyboard.merge(sb, frames_job)
    assert merged["reference_frames_deferred"] is False
    assert merged["reference_image_urls"] == ["https://cdn/f.png"]
    assert client.storyboard.segment_reference_image_urls(merged) == [["https://cdn/f.png"]]
    merged = client.storyboard.merge(merged, {"status": "done", "board": {"storyboard_board_image_url": "https://cdn/b.png"}})
    assert merged["storyboard_board_image_url"] == "https://cdn/b.png"
    assert merged["storyboard_board_duration_seconds"] == 30
    assert sb["segments"] == [{"index": 1}]  # input untouched


# -- 6. start_from_storyboard ---------------------------------------------------


@responses.activate
def test_start_from_storyboard_builds_portal_render_body():
    responses.post(f"{BASE}/api/v1/long-video/start", json=ok({"job_id": 9}), status=202)
    jwt_client().longvideo.start_from_storyboard(
        {"status": "done", "storyboard": storyboard()},
        product_image_url="https://cdn/p.jpg",
        subject_image_url="https://cdn/s.jpg",
        avatar_id=12,
        avatar_view_type="mezzo_busto",
        additional_product_image_urls=["https://cdn/p2.jpg", "https://cdn/p.jpg"],
        product_box_closed_url="https://cdn/box-c.jpg",
        product_box_open_url="https://cdn/box-o.jpg",
        extra_products=[{"image_url": "https://cdn/b.jpg"}],
        brand_logo_url="https://cdn/logo.png",
        brand_logo_mode="in_video",
        voice_id={"subject_1": "v-sub", "voice_over": "v-nar"},
        language_code="it",
        montage=True,
        brief="Il mio brief",
        ratio="9:16",
        resolution="720p",
    )
    body = body_of(responses.calls[-1])
    assert body["product_image_url"] == "https://cdn/p.jpg"
    assert body["subject_image_url"] == "https://cdn/s.jpg"
    assert body["avatar_id"] == 12 and body["avatar_view_type"] == "mezzo_busto"
    assert body["additional_product_image_urls"] == ["https://cdn/p2.jpg", "https://cdn/p.jpg"]
    assert body["product_box_closed_url"] == "https://cdn/box-c.jpg"
    assert body["product_box_open_url"] == "https://cdn/box-o.jpg"
    assert body["extra_products"] == [{"image_url": "https://cdn/b.jpg"}]
    assert body["brand_logo_url"] == "https://cdn/logo.png" and body["brand_logo_mode"] == "in_video"
    assert body["custom_prompt"] == "OPTIMIZED PROMPT"
    assert body["duration"] == 30 and body["duration_seconds"] == 30
    assert body["ratio"] == "9:16" and body["resolution"] == "720p"
    assert body["studiohero_segment_prompts"] == ["seg 1 visual", "seg 2 seedance", "seg 3 visual"]
    assert body["studiohero_segment_reference_image_urls"][0] == ["https://cdn/f1.png", "https://cdn/c1.png"]
    assert body["reference_image_urls"] == [
        "https://cdn/board.png", "https://cdn/p.jpg", "https://cdn/p2.jpg", "https://cdn/s.jpg",
    ]
    assert body["voiceover_cast"]["subject_1"]["voice_id"] == "v-sub"
    assert body["voiceover_cast"]["voice_over"]["voice_id"] == "v-nar"
    assert body["tts_voice_id"] == "v-sub"
    assert body["language_code"] == "it"
    assert body["montage"] == {"brief": "Il mio brief", "language_code": "it",
                               "logo_url": "https://cdn/logo.png", "logo_mode": "in_video"}
    assert "storyboard" not in body


@responses.activate
def test_start_from_storyboard_logo_end_only_asks_outro_and_extra_kwargs_win():
    responses.post(f"{BASE}/api/v1/long-video/start", json=ok({"job_id": 9}), status=202)
    jwt_client().longvideo.start_from_storyboard(
        storyboard(), product_image_url="https://cdn/p.jpg",
        brand_logo_url="https://cdn/logo.png", brand_logo_mode="end_only",
        captions=True, custom_prompt="override",
    )
    body = body_of(responses.calls[-1])
    assert body["montage"] == {"kind": "outro", "language_code": "it",
                               "logo_url": "https://cdn/logo.png", "logo_mode": "end_only"}
    assert body["captions"] is True
    assert body["custom_prompt"] == "override"
    assert "voiceover_cast" not in body and "tts_voice_id" not in body


@responses.activate
def test_start_from_storyboard_montage_dict_keeps_explicit_fields():
    responses.post(f"{BASE}/api/v1/long-video/start", json=ok({"job_id": 9}), status=202)
    jwt_client().longvideo.start_from_storyboard(
        storyboard(), product_image_url="https://cdn/p.jpg", language_code="en",
        montage={"brief": "Only this", "logo_mode": "off"},
    )
    assert body_of(responses.calls[-1])["montage"] == {"brief": "Only this", "logo_mode": "off", "language_code": "en"}


def test_start_from_storyboard_rejects_avatar_view_avatar_and_missing_voices():
    client = jwt_client()
    with pytest.raises(ValidationError):
        client.longvideo.start_from_storyboard(storyboard(), avatar_id=3, avatar_view_type="avatar")
    with pytest.raises(ValidationError) as exc:
        client.longvideo.start_from_storyboard(storyboard(), voice_id={"subject_1": "v"})
    assert "voice_over" in str(exc.value)
    with pytest.raises(ValidationError):
        client.longvideo.start_from_storyboard({"segments": []})


def test_version_is_0_4_0():
    assert __version__ == "0.4.0"
