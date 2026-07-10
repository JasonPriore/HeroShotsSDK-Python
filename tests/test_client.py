"""Transport, auth, envelope and error-mapping tests (mocked HTTP)."""

import json

import pytest
import responses

from heroshots import (
    Client,
    HeroShotsClient,
    NotFoundError,
    RateLimitError,
    TokenExpiredError,
    ValidationError,
)

BASE = "https://api.test"


def make_client(token="tok"):
    return HeroShotsClient(BASE, token=token, auto_relogin=False)


@responses.activate
def test_login_stores_token():
    responses.post(
        f"{BASE}/api/auth/login",
        json={"token": "jwt-123", "user_id": 7, "account_type": "brand"},
        status=200,
    )
    client = Client.from_login("a@b.com", "pw", base_url=BASE)
    assert client.token == "jwt-123"
    # Bearer header is attached on the next call.
    responses.get(f"{BASE}/api/auth/me", json={"user_id": 7}, status=200)
    client.me()
    assert responses.calls[-1].request.headers["Authorization"] == "Bearer jwt-123"


@responses.activate
def test_v1_envelope_is_unwrapped():
    responses.post(
        f"{BASE}/api/v1/image/generate",
        json={"success": True, "data": {"generation_id": "g1", "status": "pending"},
              "meta": {"credits_remaining": 5}},
        status=200,
    )
    client = make_client()
    out = client.images.generate(product_image_url="https://x/p.jpg")
    assert out["generation_id"] == "g1"
    assert out.generation_id == "g1"  # attribute access
    assert out["_meta"]["credits_remaining"] == 5


@responses.activate
def test_portal_response_is_bare():
    responses.get(
        f"{BASE}/api/auth/stats",
        json={
            "hs_credits": 120,
            "total_credits_used": 30,
            "current_month_generations": 4,
            "plan": {"wallet_balance": 9.5, "template_id": "free"},
            "recent_generations": [{"id": 1}],
            "offered_plans": [{"id": 1}],
        },
        status=200,
    )
    client = make_client()
    out = client.balance()
    assert out["hs_credits"] == 120
    assert out["plan"]["wallet_balance"] == 9.5
    assert out.wallet_balance == 9.5
    assert out.current_month_generations == 4
    assert "recent_generations" not in out
    assert "offered_plans" not in out
    assert "data" not in out


@responses.activate
def test_stats_returns_raw_account_stats():
    responses.get(
        f"{BASE}/api/auth/stats",
        json={
            "hs_credits": 120,
            "plan": {"wallet_balance": 9.5},
            "recent_generations": [{"id": 1}],
            "offered_plans": [{"id": 1}],
        },
        status=200,
    )
    out = make_client().stats()
    assert out["recent_generations"][0]["id"] == 1
    assert out["offered_plans"][0]["id"] == 1


@responses.activate
def test_error_envelope_maps_to_exception():
    responses.post(
        f"{BASE}/video/storyboard/candidates",
        json={"success": False, "error": {"code": "validation_error", "message": "custom_prompt is required"}},
        status=400,
    )
    client = make_client()
    with pytest.raises(ValidationError) as exc:
        client.storyboard.candidates(custom_prompt="", duration_seconds=30,
                                     product_image_url="https://x/p.jpg")
    assert exc.value.code == "validation_error"
    assert exc.value.status == 400


@responses.activate
def test_404_maps_to_not_found():
    responses.get(
        f"{BASE}/video/storyboard/status/missing",
        json={"success": False, "error": {"code": "not_found", "message": "expired"}},
        status=404,
    )
    with pytest.raises(NotFoundError):
        make_client().storyboard.status("missing")


@responses.activate
def test_429_maps_to_rate_limit():
    responses.get(f"{BASE}/api/auth/stats", body="too many", status=429)
    with pytest.raises(RateLimitError):
        make_client().balance()


@responses.activate
def test_auto_relogin_on_token_expired():
    # First call: expired. Re-login. Retry: ok.
    responses.get(
        f"{BASE}/api/auth/me",
        json={"success": False, "error": {"code": "token_expired", "message": "expired"}},
        status=401,
    )
    responses.post(f"{BASE}/api/auth/login", json={"token": "fresh"}, status=200)
    responses.get(f"{BASE}/api/auth/me", json={"user_id": 1}, status=200)

    client = HeroShotsClient(BASE, token="stale", email="a@b.com", password="pw")
    out = client.me()
    assert out["user_id"] == 1
    assert client.token == "fresh"


@responses.activate
def test_token_expired_raises_without_credentials():
    responses.get(
        f"{BASE}/api/auth/me",
        json={"success": False, "error": {"code": "token_expired", "message": "expired"}},
        status=401,
    )
    with pytest.raises(TokenExpiredError):
        make_client().me()
