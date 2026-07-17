# heroshots (Python SDK)

High-level Python client for the HeroShots / StudioHero platform, authenticated
with a **portal JWT or API key**. Covers the full JWT/API-key reachable API
surface.

## Install

```bash
pip install heroshots          # from a registry
pip install -e ".[dev]"        # local dev (runs the test suite)
```

Requires Python 3.9+. Only runtime dependency: `requests`.

## Authenticate

```python
from heroshots import Client

# Email/password login (recommended): stores the JWT, auto re-logins on expiry.
# Base URL defaults to https://app.heroshots.ai.
client = Client.from_login("dev@partner.com", "secret")

# Or reuse an existing token.
client = Client(token="eyJ...")
```

## Agency act-as

Agency API keys can operate as a managed brand by passing the `managed_user_id`
returned by the managed-client provisioning API. The SDK adds
`X-Managed-User-Id` to authenticated requests.

```python
from heroshots import Client

client = Client(token="lz_live_YOUR_AGENCY_KEY", managed_user_id=12345)
job = client.images.generate(product_image_url="https://example.com/product.jpg")

# Switch target brand later, or pass None to clear it.
client.with_managed_user(67890)
```

## Usage

```python
# Local file paths are auto-uploaded to hosted URLs.
briefs = client.storyboard.brief_suggestions(
    product_image_url="product.jpg", subject_image_url="model.jpg",
    duration_seconds=30, language_code="it",
)

candidates = client.storyboard.candidates(
    custom_prompt=briefs[0], duration_seconds=30,
    product_image_url="product.jpg", subject_image_url="model.jpg",
)

job = client.storyboard.generate(
    custom_prompt=briefs[0], duration_seconds=30, selected_candidate=candidates[0],
    product_image_url="product.jpg", subject_image_url="model.jpg",
)
sb = client.storyboard.wait(job["job_id"])           # polls until done/failed

vjob = client.longvideo.start(image_url="product.jpg", storyboard=sb["storyboard"])
final = client.longvideo.wait(vjob["job_id"])
print(final["final_video_url"])                       # also: final.final_video_url
```

Responses support both `result["key"]` and `result.key` access. `/api/v1`
billing metadata is under `result["_meta"]`.

## Guide

For step-by-step examples organized by use case, read the full guide:
[GUIDE.md](https://github.com/JasonPriore/HeroShotsSDK-Python/blob/main/GUIDE.md).

## Resources

`uploads` · `images` · `videos` · `longvideo` · `stilllife` · `storyboard` ·
`avatars`

Plus on the client: `login()`, `me()`, `balance()`, `stats()`.

Every method maps 1:1 to an endpoint; pass extra backend fields as keyword
arguments (they are forwarded verbatim).

## Errors

```python
from heroshots import ValidationError, TokenExpiredError, RateLimitError

try:
    client.storyboard.candidates(custom_prompt="", duration_seconds=30,
                                 product_image_url="p.jpg")
except ValidationError as e:
    print(e.code, e.message, e.details)
```

## Test

```bash
pytest          # offline, mocked HTTP
```

## Billing

Generations cost credits. Check remaining credits with `client.balance()`
(`hs_credits` + `wallet_balance`). Use `client.stats()` for the full raw
`/api/auth/stats` payload, including recent generations and offered plans. See
`examples/full_storyboard_flow.py`.
