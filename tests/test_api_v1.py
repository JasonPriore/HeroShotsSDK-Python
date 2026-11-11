"""Public API (/api/v1) coverage: API-key auth, new resources, downloads, retries."""

import json

import pytest
import responses

from heroshots import BillingError, ForbiddenError, HeroShotsClient, HeroShotsError

BASE = "https://api.test"
KEY = "lz_live_test"


def api_client(**kw):
    return HeroShotsClient(BASE, api_key=KEY, auto_relogin=False, **kw)


def ok(data, meta=None):
    body = {"success": True, "data": data}
    if meta is not None:
        body["meta"] = meta
    return body


def last_json():
    return json.loads(responses.calls[-1].request.body)


@responses.activate
def test_api_key_is_sent_as_bearer_with_user_agent():
    responses.get(f"{BASE}/api/v1/me", json=ok({"user": {"id": 1}, "credits_remaining": {"hs_credits": 3}}))
    client = api_client()
    assert client.uses_api_key
    out = client.me()
    req = responses.calls[-1].request
    assert req.headers["Authorization"] == f"Bearer {KEY}"
    assert req.headers["User-Agent"].startswith("heroshots-python/")
    assert out["user"]["id"] == 1


def test_api_key_from_env(monkeypatch):
    monkeypatch.setenv("HEROSHOTS_API_KEY", "lz_live_env")
    assert HeroShotsClient(BASE).token == "lz_live_env"


@responses.activate
def test_balance_with_api_key_reads_v1_me():
    responses.get(
        f"{BASE}/api/v1/me",
        json=ok({"user": {"id": 1, "currency_credit": 50.0, "currency_billing_type": "debit"},
                 "credits_remaining": {"hs_credits": 10, "currency_credit": 50.0}}),
    )
    out = api_client().balance()
    assert out == {"hs_credits": 10, "currency_credit": 50.0, "wallet_balance": 50.0, "billing_type": "debit"}


@responses.activate
def test_free_plan_api_key_maps_to_forbidden():
    responses.get(
        f"{BASE}/api/v1/me",
        json={"success": False, "error": {"code": "plan_not_allowed",
                                          "message": "API access is not available on the Free plan."}},
        status=403,
    )
    with pytest.raises(ForbiddenError) as exc:
        api_client().account.me()
    assert exc.value.code == "plan_not_allowed"


@responses.activate
def test_vat_validation_maps_to_billing_error():
    responses.post(
        f"{BASE}/api/v1/video/generate",
        json={"success": False, "error": {"code": "wallet_vat_validation_required", "message": "VAT"}},
        status=402,
    )
    with pytest.raises(BillingError):
        api_client().videos.generate(image_url="https://x/p.jpg", duration_seconds=15)


@responses.activate
def test_429_is_retried_then_succeeds(monkeypatch):
    monkeypatch.setattr("heroshots.client.time.sleep", lambda s: None)
    responses.get(f"{BASE}/api/v1/health", status=429, headers={"Retry-After": "1"})
    responses.get(f"{BASE}/api/v1/health", json=ok({"status": "ok"}))
    out = api_client().account.health()
    assert out["status"] == "ok"
    assert len(responses.calls) == 2
    assert "Authorization" not in responses.calls[-1].request.headers


@responses.activate
def test_local_path_with_api_key_raises_clear_error(tmp_path):
    img = tmp_path / "p.png"
    img.write_bytes(b"x")
    with pytest.raises(HeroShotsError, match="public https"):
        api_client().images.generate(str(img))
    assert len(responses.calls) == 0


@responses.activate
def test_image_download_returns_bytes_and_writes_file(tmp_path):
    responses.get(f"{BASE}/api/v1/image/42/download", body=b"\xff\xd8jpeg", content_type="image/jpeg")
    responses.get(f"{BASE}/api/v1/video/43/download", body=b"mp4data", content_type="video/mp4")
    client = api_client()
    assert client.images.download(42) == b"\xff\xd8jpeg"
    saved = client.videos.download(43, tmp_path / "out" / "v.mp4")
    assert open(saved, "rb").read() == b"mp4data"


@responses.activate
def test_video_status_uses_v1_and_provider_param():
    responses.get(f"{BASE}/api/v1/video/status/t9", json=ok({"status": "processing"}))
    out = api_client().videos.status("t9", provider="byteplus")
    assert out["status"] == "processing"
    assert responses.calls[-1].request.url.endswith("/api/v1/video/status/t9?provider=byteplus")


@responses.activate
def test_longvideo_start_and_regenerate_segment():
    responses.post(f"{BASE}/api/v1/long-video/start", json=ok({"job_id": 5, "status": "queued"}), status=202)
    responses.post(f"{BASE}/api/v1/long-video/5/segments/1/regenerate", json=ok({"job_id": 5}))
    client = api_client()
    job = client.longvideo.start("https://x/p.jpg", custom_prompt="spot", duration_seconds=30)
    assert job["job_id"] == 5
    body = json.loads(responses.calls[0].request.body)
    assert body == {"ratio": "16:9", "resolution": "1080p", "image_url": "https://x/p.jpg",
                    "custom_prompt": "spot", "duration_seconds": 30}
    client.longvideo.regenerate_segment(5, 1, comment="slower", cascade=True)
    assert last_json() == {"comment": "slower", "cascade": True}


@responses.activate
def test_stilllife_start_uses_v1():
    responses.post(f"{BASE}/api/v1/stilllife-video/start", json=ok({"task_id": 8}), status=202)
    out = api_client().stilllife.start("https://x/p.jpg", "https://x/bg.jpg", custom_prompt="slow orbit")
    assert out["task_id"] == 8
    assert last_json()["custom_prompt"] == "slow orbit"
    assert "detail_image_url" not in last_json()


@responses.activate
def test_generations_iterate_walks_pages():
    responses.get(f"{BASE}/api/v1/generations", json=ok({"generations": [{"id": 1}], "page": 1, "pages": 2}))
    responses.get(f"{BASE}/api/v1/generations", json=ok({"generations": [{"id": 2}], "page": 2, "pages": 2}))
    ids = [g["id"] for g in api_client().generations.iterate(type="video", per_page=1)]
    assert ids == [1, 2]
    assert "type=video" in responses.calls[0].request.url


@responses.activate
def test_pricing_quote_and_catalog():
    responses.post(f"{BASE}/api/v1/pricing/quote", json=ok({"total_eur": "15.00"}))
    responses.get(f"{BASE}/api/v1/pricing/catalog", json=ok({"video": {}}))
    client = api_client()
    assert client.pricing.quote("video", duration_seconds=15)["total_eur"] == "15.00"
    assert last_json() == {"call_type": "video", "duration_seconds": 15}
    assert "video" in client.pricing.catalog()


@responses.activate
def test_usage_rights_quote_get_and_post():
    responses.get(f"{BASE}/api/v1/image/7/usage-rights/quote", json={"delta_eur": "3.00"})
    responses.post(f"{BASE}/api/v1/image/7/usage-rights/quote", json={"delta_eur": "5.00"})
    client = api_client()
    a = client.images.usage_rights_quote(7, usage_rights_type="paid_digital", usage_rights_duration="6_months")
    assert a["delta_eur"] == "3.00"
    assert "usage_rights_type=paid_digital" in responses.calls[0].request.url
    b = client.images.usage_rights_quote(7, [{"type": "broadcast", "duration": "2_years"}])
    assert b["delta_eur"] == "5.00"


@responses.activate
def test_avatar_edit_endpoints():
    responses.patch(f"{BASE}/api/v1/avatar/3", json={"success": True})
    responses.post(f"{BASE}/api/v1/avatar/3/image-set", json=ok({"mode": "generated"}))
    responses.post(f"{BASE}/api/v1/avatar/3/outfit", json=ok({}), status=202)
    responses.post(f"{BASE}/api/v1/avatar/3/regenerate-view", json={"success": True}, status=202)
    client = api_client()
    client.avatars.update(3, name="Giulia")
    assert last_json() == {"name": "Giulia"}
    client.avatars.set_image_set(3, "generated")
    assert last_json() == {"mode": "generated"}
    client.avatars.change_outfit(3, [{"slot": "top", "image_url": "https://x/t.jpg"}])
    assert last_json() == {"items": [{"slot": "top", "image_url": "https://x/t.jpg"}]}
    client.avatars.regenerate_view(3, "closeup")
    assert last_json() == {"view_type": "closeup"}


@responses.activate
def test_bulk_upload_images_is_multipart_and_wait_returns_final():
    responses.post(f"{BASE}/api/v1/bulk/b1/images", json={"uploaded": 2, "items": []}, status=201)
    responses.get(f"{BASE}/api/v1/bulk/b1", json={"id": "b1", "status": "processing"})
    responses.get(f"{BASE}/api/v1/bulk/b1", json={"id": "b1", "status": "partially_completed"})
    client = api_client()
    out = client.bulk.upload_images("b1", [b"one", b"two"])
    assert out["uploaded"] == 2
    body = responses.calls[-1].request.body
    assert body.count(b'name="files"') == 2
    final = client.bulk.wait("b1", interval=0, timeout=5)
    assert final["status"] == "partially_completed"


@responses.activate
def test_bulk_download_generated_filters_items():
    responses.get(f"{BASE}/api/v1/bulk/b1/download-generated", body=b"PK", content_type="application/zip")
    assert api_client().bulk.download_generated("b1", item_ids=[1, 2]) == b"PK"
    assert responses.calls[-1].request.url.endswith("item_ids=1%2C2")


@responses.activate
def test_asset_create_is_multipart():
    responses.post(f"{BASE}/api/v1/assets", json={"id": 9, "name": "Bag"}, status=201)
    out = api_client().assets.create("Bag", b"img", category_id=4)
    assert out["id"] == 9
    body = responses.calls[-1].request.body
    assert b'name="primary_image"' in body
    assert b'name="category_id"' in body


@responses.activate
def test_collections_and_categories():
    responses.post(f"{BASE}/api/v1/collections/2/generations", json=ok({}))
    responses.post(f"{BASE}/api/v1/categories/selected", json=ok({}))
    client = api_client()
    client.collections.add_generation(2, "15")
    assert last_json() == {"log_id": 15}
    client.categories.set_selected(["1", 2])
    assert last_json() == {"category_ids": [1, 2]}


@responses.activate
def test_agency_act_as_and_topup():
    responses.post(f"{BASE}/api/v1/agency/managed-clients/4/topup", json={"ok": True})
    responses.post(f"{BASE}/api/v1/image/generate", json=ok({"generation_id": "g"}), status=202)
    client = api_client()
    client.agency.topup(4, 25.0)
    assert last_json() == {"amount": 25.0}
    client.with_managed_user(77).images.generate("https://x/p.jpg", avatar_id=1)
    assert responses.calls[-1].request.headers["X-Managed-User-Id"] == "77"


@responses.activate
def test_legal_templates_download_and_attach():
    responses.get(f"{BASE}/api/legal/byo/liberatoria-template", body=b"DOCX")
    responses.post(f"{BASE}/api/legal/byo/10/avatars", json={"ok": True})
    client = HeroShotsClient(BASE, token="jwt", auto_relogin=False)
    assert client.legal.liberatoria_template() == b"DOCX"
    client.legal.attach_liberatoria(10, 3, release_doc_url="r", id_doc_url="i",
                                    model_email="m@x.com", model_dob="1990-01-01")
    assert last_json()["avatar_id"] == 3


@responses.activate
def test_bulk_download_generated_accepts_string_ids():
    responses.get(f"{BASE}/api/v1/bulk/b1/download-generated", body=b"PK")
    api_client().bulk.download_generated("b1", item_ids="3,4")
    assert responses.calls[-1].request.url.endswith("item_ids=3%2C4")


@responses.activate
def test_longvideo_wait_stops_at_segments_ready():
    responses.get(f"{BASE}/api/v1/long-video/status/5", json=ok({"job_id": 5, "status": "generating"}))
    responses.get(f"{BASE}/api/v1/long-video/status/5",
                  json=ok({"job_id": 5, "status": "segments_ready", "final_video_url": None,
                           "segments": [{"index": 1, "video_url": "https://cdn/1.mp4"}]}))
    out = api_client().longvideo.wait(5, interval=0, timeout=5)
    assert out["status"] == "segments_ready"
    assert out["segments"][0]["video_url"].endswith("1.mp4")


@responses.activate
def test_longvideo_render_exports_then_waits_for_final(monkeypatch):
    monkeypatch.setattr("heroshots.resources.longvideo.time.sleep", lambda s: None)
    responses.get(f"{BASE}/api/v1/long-video/status/5", json=ok({"status": "segments_ready"}))
    responses.post(f"{BASE}/api/auth/long-video/5/export", json={"job_id": 5, "status": "concatenating"}, status=202)
    responses.get(f"{BASE}/api/v1/long-video/status/5", json=ok({"status": "concatenating"}))
    responses.get(f"{BASE}/api/v1/long-video/status/5",
                  json=ok({"status": "done", "final_video_url": "https://cdn/final.mp4"}))
    client = HeroShotsClient(BASE, token="jwt", auto_relogin=False)
    out = client.longvideo.render(5, interval=0, timeout=5)
    assert out["final_video_url"].endswith("final.mp4")
    export_call = [c for c in responses.calls if c.request.url.endswith("/export")][0]
    assert json.loads(export_call.request.body) == {}


@responses.activate
def test_invalid_or_expired_token_triggers_relogin():
    responses.post(f"{BASE}/api/auth/long-video/5/export",
                   json={"success": False, "error": {"code": "invalid_or_expired_token", "message": "x"}},
                   status=401)
    responses.post(f"{BASE}/api/auth/login", json={"token": "fresh"})
    responses.post(f"{BASE}/api/auth/long-video/5/export", json={"status": "concatenating"}, status=202)
    client = HeroShotsClient(BASE, token="stale", email="a@b.com", password="pw")
    assert client.longvideo.export(5)["status"] == "concatenating"
    assert client.token == "fresh"


@responses.activate
def test_login_rejects_non_string_credentials():
    from heroshots import ValidationError

    client = HeroShotsClient(BASE)
    with pytest.raises(ValidationError):
        client.login("a@b.com", {"password": "x"})
    with pytest.raises(ValidationError):
        client.login("", "pw")
    assert len(responses.calls) == 0
