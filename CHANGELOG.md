# Changelog

## 0.3.0

Aligned with the current HeroShots API (OpenAPI 1.1.0) and with the Node and PHP SDKs.

### Fixed
- Long video and still-life video now call `/api/v1/long-video/*` and
  `/api/v1/stilllife-video/*`. The old `/api/auth/long-video/start|status` and
  `/api/auth/stilllife-video/start|status` routes were removed from the backend
  on 2026-07-16, so 0.2.x returned 404 for these calls.
- `images.download()` returns the file (bytes, or saved to a path) instead of
  trying to decode it as JSON.
- `balance()` and `me()` work with an API key (they read `/api/v1/me`;
  `/api/auth/*` accepts only a portal login).
- `videos.status()` uses `/api/v1/video/status/{id}`, which accepts API keys.

### Added
- `api_key=` option and `HEROSHOTS_API_KEY` env var; `client.uses_api_key`.
- Automatic retry on HTTP 429 (`max_retries=2`, honours `Retry-After`);
  `RateLimitError.retry_after`.
- `BillingError` for `no_payment_method` and `wallet_vat_validation_required`;
  `plan_change_locked` maps to `ConflictError`.
- New namespaces: `account`, `generations`, `pricing`, `bulk`, `assets`,
  `collections`, `backgrounds`, `categories`, `legal`, `agency`, `brand`.
- Avatars: update, delete, upload/regenerate views, variants, generated version,
  image set, avatar sheet, voice, outfit (resolve link, change, restore),
  improve prompt, analyze attributes, create from steps, consent document.
- Images: background generation, usage-rights quote/upgrade, edit-region analysis.
- Videos: `download()`. Long video: `regenerate_segment()`.
- Uploads: `consent_document()`, `reference_audio()`.
- `User-Agent: heroshots-python/<version>` header.

### Changed
- Uploading a local file path with an API key now raises a clear error
  (`/upload/image` accepts only a portal login): pass public URLs instead.
