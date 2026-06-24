"""Resource-level tests: paths, verbs, multipart, polling, auto-upload."""

import io

import pytest
import responses

from heroshots import HeroShotsClient, ProviderError
from heroshots._polling import TimeoutError as PollTimeoutError

BASE = "https://api.test"


def make_client():
    return HeroShotsClient(BASE, token="tok", auto_relogin=False)


@responses.activate
def test_upload_image_sends_multipart_file():
    responses.post(
        f"{BASE}/upload/image",
        json={"public_url": "https://cdn/x.jpg", "filename": "x.jpg", "folder": "products"},
        status=200,
    )
    client = make_client()
    out = client.uploads.image(io.BytesIO(b"bytes"), folder="products")
    assert out["public_url"] == "https://cdn/x.jpg"
    body = responses.calls[-1].request.body
    # requests encodes multipart; the field name must be "file".
    assert b'name="file"' in body
    assert b'name="folder"' in body


@responses.activate
def test_storyboard_brief_suggestions_returns_list():
    responses.post(
        f"{BASE}/video/storyboard/brief-suggestions",
        json={"suggestions": ["a", "b", "c"]},
        status=200,
    )
    out = make_client().storyboard.brief_suggestions(product_image_url="https://x/p.jpg")
    assert out == ["a", "b", "c"]


@responses.activate
def test_storyboard_wait_succeeds_on_done():
    responses.get(
        f"{BASE}/video/storyboard/status/j1",
        json={"job_id": "j1", "status": "queued"},
        status=200,
    )
    responses.get(
        f"{BASE}/video/storyboard/status/j1",
        json={"job_id": "j1", "status": "done", "storyboard": {"segments": []}},
        status=200,
    )
    out = make_client().storyboard.wait("j1", interval=0, timeout=5)
    assert out["status"] == "done"


@responses.activate
def test_wait_raises_provider_error_on_failed():
    responses.get(
        f"{BASE}/api/auth/long-video/status/9",
        json={"job_id": 9, "status": "failed", "error": {"code": "provider_error", "message": "boom"}},
        status=200,
    )
    with pytest.raises(ProviderError) as exc:
        make_client().longvideo.wait(9, interval=0, timeout=5)
    assert "boom" in str(exc.value)


@responses.activate
def test_video_wait_uses_succeeded_terminal():
    responses.get(
        f"{BASE}/video/status/t1",
        json={"task_id": "t1", "status": "succeeded", "video_url": "https://cdn/v.mp4"},
        status=200,
    )
    out = make_client().videos.wait("t1", interval=0, timeout=5)
    assert out["video_url"].endswith("v.mp4")


@responses.activate
def test_wait_times_out():
    responses.get(
        f"{BASE}/video/storyboard/status/slow",
        json={"job_id": "slow", "status": "queued"},
        status=200,
    )
    with pytest.raises(PollTimeoutError):
        make_client().storyboard.wait("slow", interval=0, timeout=0)


@responses.activate
def test_local_path_autouploads_before_generate(tmp_path):
    img = tmp_path / "p.png"
    img.write_bytes(b"\x89PNG\r\n")
    responses.post(
        f"{BASE}/upload/image",
        json={"public_url": "https://cdn/up.png", "filename": "p.png", "folder": "products"},
        status=200,
    )
    responses.post(
        f"{BASE}/api/v1/image/generate",
        json={"success": True, "data": {"generation_id": "g", "status": "pending"}, "meta": {}},
        status=200,
    )
    out = make_client().images.generate(product_image_url=str(img))
    assert out["generation_id"] == "g"
    # The generate body must reference the hosted URL, not the local path.
    gen_body = responses.calls[-1].request.body
    assert b"https://cdn/up.png" in gen_body


@responses.activate
def test_avatars_list_uses_v1():
    responses.get(
        f"{BASE}/api/v1/avatar/list",
        json={"success": True, "data": {"avatars": [{"id": 1}]}, "meta": {}},
        status=200,
    )
    out = make_client().avatars.list()
    assert len(out["avatars"]) == 1
