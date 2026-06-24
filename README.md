# heroshots (Python SDK)

High-level Python client for the HeroShots / StudioHero platform, authenticated
with a **portal JWT**. Covers the full JWT-reachable API surface.

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

## Resources

`uploads` · `images` · `videos` · `longvideo` · `stilllife` · `storyboard` ·
`avatars`

Plus on the client: `login()`, `me()`, `balance()`.

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
(`hs_credits` + `plan.wallet_balance`). See `examples/full_storyboard_flow.py`.
