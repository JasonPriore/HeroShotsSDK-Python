# heroshots (Python SDK)

Python client for the HeroShots / StudioHero API. Works with a **B2B API key**
(`lz_live_...`) or a **portal login (JWT)** and covers the whole public
`/api/v1` surface plus the StudioHero storyboard flow.

## Install

```bash
pip install heroshots          # from PyPI
pip install -e ".[dev]"        # local dev (runs the test suite)
```

Requires Python 3.9+. Only runtime dependency: `requests`.

## Authenticate

```python
from heroshots import Client

# API key (server-to-server). Also read from HEROSHOTS_API_KEY.
client = Client(api_key="lz_live_...")

# Portal login: stores the JWT and logs in again automatically when it expires.
client = Client.from_login("dev@partner.com", "secret")
```

Base URL defaults to `https://app.heroshots.ai` (override with `base_url=` or
`HEROSHOTS_BASE_URL`).

| Endpoints | API key | Portal JWT |
|---|---|---|
| `/api/v1/*`: images, videos, long video, still life, avatars, bulk, library, generations, pricing, agency, brand | ✅ | ✅ |
| Storyboard (StudioHero), voices, uploads, image candidates, long-video export (final cut) and auto-edit, still-life background edits, BYO legal documents | ❌ | ✅ |

- API keys are **refused on the Free plan** (`ForbiddenError`, code
  `plan_not_allowed`), except for agency accounts.
- **Local file paths** are uploaded automatically only with a portal JWT. With
  an API key pass public `https://` URLs (the SDK raises a clear error otherwise).

## Quick start

```python
client = Client(api_key="lz_live_...")

print(client.balance())                       # {'hs_credits': 10, 'wallet_balance': 50.0, ...}
print(client.pricing.quote("video", duration_seconds=15))

job = client.videos.generate(
    product_image_url="https://example.com/product.jpg",
    avatar_id=42,
    custom_prompt="slow dolly-in, soft studio light",
    duration_seconds=15,
)
done = client.videos.wait(job["video_id"])
print(done["video_url"])
```

Responses support both `result["key"]` and `result.key`. `/api/v1` billing
metadata (charges, credits left) is under `result["_meta"]`.

## Resources

| Namespace | What it does |
|---|---|
| `client.account` | `me()`, `health()` |
| `client.images` | `generate`, `status`, `wait`, `download`, `generate_background`, `usage_rights_quote`, `usage_rights_upgrade`, `analyze_edit_region`, `candidates`, `select_candidate` |
| `client.videos` | `generate`, `status`, `wait`, `download` |
| `client.longvideo` | `start`, `start_from_storyboard` (the portal's render), `status`, `wait` (until `segments_ready`), `regenerate_segment`, `export`, `render` (final cut + auto-edit, portal JWT), `montage`, `montage_available`, `montage_settled`, `view` |
| `client.stilllife` | `start`, `status`, `wait`, `preview_background`, `change_background`, `change_background_status` |
| `client.storyboard` | `brief_suggestions`, `candidates`, `recommend`, `generate`, `frames`, `board`, `revise`, `status`, `wait`, `merge`, `segment_prompts`, `segment_reference_image_urls`, `voice_roles`, `voice_cast`, `missing_voice_roles`, `subject_measurements`, `analyze_product`, `creativity` |
| `client.audio` | `voices` (voice ids for the voiceover, portal JWT) |
| `client.avatars` | `list`, `get`, `generate`, `create_from_steps`, `update`, `delete`, `upload_view`, `regenerate_view`, `regenerate_variants`, `generated_version`, `set_image_set`, `generate_sheet`, `generate_voice`, `resolve_outfit_link`, `change_outfit`, `restore_outfit`, `improve_prompt`, `analyze_attributes`, `consent_document` |
| `client.bulk` | `list`, `create`, `get`, `update`, `delete`, `upload_images`, `start`, `wait`, `regenerate_item`, `regenerate_all`, `cancel_item`, `remove_item`, `replace_product`, `previews`, `attempts`, `select_attempt`, `download_item`, `download_product`, `download_generated` |
| `client.generations` | `list`, `iterate` |
| `client.pricing` | `catalog`, `quote`, `video_packages_catalog`, `video_packages_quote`, `usage_rights_rules` |
| `client.assets` · `client.collections` · `client.backgrounds` · `client.categories` | product library (CRUD) |
| `client.uploads` | `image`, `consent_document`, `reference_audio` |
| `client.legal` | `byo_status`, `manleva_template`, `liberatoria_template`, `upload_manleva`, `attach_liberatoria` |
| `client.agency` | managed brands: `clients`, `client`, `invite_client`, `create_client`, `update_client`, `topup`, `resend_invite`, `claim_invite`, termination |
| `client.brand` | the brand side of an agency relationship |

On the client: `login()`, `me()`, `balance()`, `stats()`, `with_managed_user()`,
`download()`, `request()`.

Every method maps 1:1 to an endpoint; extra backend fields can be passed as
keyword arguments and are forwarded verbatim.

## StudioHero: the portal flow (portal JWT)

```python
client = Client.from_login("dev@partner.com", "secret")
product = client.uploads.image("product.jpg", folder="products")["public_url"]
subject = client.uploads.image("model.jpg", folder="subjects")["public_url"]
common = dict(product_image_url=product, subject_image_url=subject, duration_seconds=30,
              ratio="9:16", language_code="it", video_type="ugc", ugc_style="top_creator",
              look_mode="current")

briefs = client.storyboard.brief_suggestions(**common)            # [{title, brief, ...}]
best = client.storyboard.recommend("brief", briefs, **common)      # {recommended_index, reason}
brief = briefs[best["recommended_index"]]["brief"]

concepts = client.storyboard.candidates(custom_prompt=brief, **common)
pick = client.storyboard.recommend("concept", concepts, custom_prompt=brief,
                                   chosen_brief=brief, **common)["recommended_index"]

job = client.storyboard.generate(custom_prompt=brief, selected_candidate=concepts[pick], **common)
sb = client.storyboard.wait(job["job_id"])["storyboard"]
if sb.get("reference_frames_deferred"):                            # 4K reference frames
    frames = client.storyboard.wait(client.storyboard.frames(sb, **common)["job_id"], timeout=900)
    sb = client.storyboard.merge(sb, frames)

voices = client.audio.voices()["voices"]                           # [{voice_id, name, ...}]
voice_ids = {role["key"]: voices[0]["voice_id"] for role in client.storyboard.voice_roles(sb)}

vjob = client.longvideo.start_from_storyboard(
    sb, product_image_url=product, subject_image_url=subject,
    voice_id=voice_ids, language_code="it", montage=True, brief=brief, ratio="9:16",
)
final = client.longvideo.render(vjob["job_id"])                    # clips -> export -> auto-edit
client.download(final.get("captioned_final_video_url") or final["final_video_url"], "out/spot.mp4")
```

`start_from_storyboard` sends what the portal sends: the inputs (avatar with a
real `avatar_view_type` such as `fullbody` / `mezzo_busto` / `closeup`, extra
product views, `product_box_closed_url` / `product_box_open_url`,
`extra_products`, `brand_logo_url` + `brand_logo_mode`), `custom_prompt` = the
storyboard's `optimized_prompt`, the per-segment prompts and reference frames,
`reference_image_urls`, `voiceover_cast` + `tts_voice_id` + `language_code` and
`montage`. The auto-edited video is `captioned_final_video_url`;
`final_video_url` stays the plain cut. Storyboard request fields:
`video_type` (`ugc` | `cinema` | `spot_tv` | `sas_software`), `ugc_style`
(`amateur` | `top_creator`), `look_mode` (`current`), `language_code`,
`storyboard_reference_frames_required`, `storyboard_board_required`.

## Agency act-as

```python
client = Client(api_key="lz_live_AGENCY_KEY", managed_user_id=12345)
client.images.generate("https://example.com/product.jpg", avatar_id=7)
client.with_managed_user(67890)   # switch brand; None clears it
```

## Downloads

```python
data = client.images.download(log_id)                 # bytes
path = client.videos.download(log_id, "out/spot.mp4")  # saved to disk
zip_path = client.bulk.download_generated(bulk_id, "out/bulk.zip")
client.download(job["final_video_url"], "out/final.mp4")  # absolute URLs work too
```

The token is sent only when the URL points at the API host (`base_url`), never
to a third-party CDN.

## Errors

```python
from heroshots import BillingError, ForbiddenError, RateLimitError, ValidationError

try:
    client.videos.generate(image_url="https://example.com/p.jpg", duration_seconds=15)
except BillingError as e:          # no payment method / billing details (VAT) missing
    print(e.code, e.message)
except RateLimitError as e:        # already retried max_retries times
    print("retry after", e.retry_after)
```

HTTP 429 is retried automatically (`max_retries=2`, honours `Retry-After`).

## Guide

Step-by-step examples by use case (Italian):
[GUIDE.md](https://github.com/JasonPriore/HeroShotsSDK-Python/blob/main/GUIDE.md).
Changes per version: [CHANGELOG.md](./CHANGELOG.md).

## Test

```bash
pytest          # offline, mocked HTTP
```
