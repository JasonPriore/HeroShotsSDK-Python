# HeroShots SDK — Guida per casi d'uso

Guida operativa all'SDK Python (`heroshots`), organizzata per **caso d'uso**. Ogni
sezione ha codice commentato passo-passo e un **esempio di risultato** (l'output
che ti aspetti). Per le firme complete dei metodi vedi il [README](./README.md).

L'SDK copre tutta l'API pubblica `/api/v1` più il flusso StudioHero:

| Caso d'uso | Risorsa |
|---|---|
| Foto (immagine prodotto, anche still-life), sfondi AI, diritti d'uso | `images` |
| Video corto | `videos` |
| Video lungo (multi-segmento), rigenerare un segmento | `longvideo` |
| Still-life video | `stilllife` |
| Studio Hero (storyboard, tutte le fasi) | `storyboard` + `longvideo` |
| Avatar: lista, creazione, modifica, outfit, voce, avatar sheet | `avatars` |
| Generazione in serie (bulk) | `bulk` |
| Storico generazioni e download dei file | `generations`, `images.download`, `videos.download` |
| Listino e preventivi | `pricing` |
| Libreria: prodotti, collezioni, sfondi, categorie | `assets`, `collections`, `backgrounds`, `categories` |
| Liberatorie per avatar di persone reali (BYO) | `legal` + `uploads.consent_document` |
| Agenzie: brand gestiti | `agency` (+ `brand` lato brand) |
| Balance e account | `client.balance()`, `client.me()`, `client.stats()` |
| Caricare file → URL ospitato | `uploads` |

---

## Indice
- [0. Setup e concetti](#0-setup-e-concetti)
- [0.1 Agenzie: selezionare il brand/utente gestito](#01-agenzie-selezionare-il-brandutente-gestito)
- [1. Balance](#1-balance)
- [2. Foto](#2-foto)
- [3. Video corto](#3-video-corto)
- [4. Still-life video](#4-still-life-video)
- [5. Video lungo](#5-video-lungo)
- [6. Studio Hero — tutte le fasi](#6-studio-hero--tutte-le-fasi)
- [7. Avatar](#7-avatar)
- [8. Listino e preventivi](#8-listino-e-preventivi)
- [9. Storico e download](#9-storico-e-download)
- [10. Generazione in serie (bulk)](#10-generazione-in-serie-bulk)
- [11. Libreria](#11-libreria)
- [12. Avatar di persone reali (BYO)](#12-avatar-di-persone-reali-byo)
- [13. Agenzie: brand gestiti](#13-agenzie-brand-gestiti)
- [Gestione errori](#gestione-errori)

---

## 0. Setup e concetti

```python
from heroshots import Client

# A) API key (server-to-server). Si può anche mettere in HEROSHOTS_API_KEY.
client = Client(api_key="lz_live_...")

# B) Login con email/password: salva il JWT e rifà il login alla scadenza (7 giorni).
client = Client.from_login("dev@partner.com", "secret")
# Il base URL è https://app.heroshots.ai (default, non serve passarlo).
```

**Quale credenziale usare.** Tutti gli endpoint `/api/v1` (foto, video, video
lunghi, still-life, avatar, bulk, libreria, storico, listino, agenzie) accettano
sia l'API key sia il JWT. Storyboard, upload di file, candidati immagine, cambio
sfondo dello still-life e documenti legali accettano **solo il JWT** del login.
Sul **piano Free le API key sono rifiutate** (`ForbiddenError`, codice
`plan_not_allowed`), tranne per le agenzie.

Quattro concetti validi per tutto l'SDK:

1. **Upload automatico (solo con login).** Ovunque si passi un'immagine puoi dare
   un **path locale**: l'SDK lo carica e usa l'URL ospitato. Gli URL `http(s)`
   passano invariati. Con l'API key l'upload non è permesso: passa URL pubblici.
2. **Job asincroni.** Le generazioni ritornano un `job_id`/`task_id`/`generation_id`;
   chiama `wait(...)` per attendere il completamento (gestisce gli stati terminali).
3. **Costo.** Ogni generazione consuma crediti: controlla con `client.balance()`,
   chiedi il prezzo prima con `client.pricing.quote(...)`.
4. **Troppe richieste.** Le risposte 429 vengono ritentate da sole (2 volte,
   rispettando `Retry-After`).

> Le risposte permettono sia `res["chiave"]` sia `res.chiave`. I metadati di
> billing degli endpoint `/api/v1` sono sotto `res["_meta"]`.

---

## 0.1 Agenzie: selezionare il brand/utente gestito

Se usi una **API key agenzia**, prima scegli il brand/utente gestito su cui vuoi
operare. Il valore è il `managed_user_id` restituito dalla creazione/lista dei
managed client. Dopo averlo impostato, usi gli stessi metodi di generazione delle
sezioni successive: l'SDK aggiunge `X-Managed-User-Id` alle richieste autenticate.

```python
from heroshots import Client

client = Client(
    token="lz_live_YOUR_AGENCY_KEY",
    managed_user_id=12345,  # brand/utente gestito selezionato
)

# Da qui in poi le generazioni vengono eseguite come quel brand.
# Con l'API key passa URL pubblici (l'upload di file locali richiede il login).
gen = client.images.generate(
    product_image_url="https://example.com/product.jpg",
    still_life=True,
    aspect_ratio="1:1",
)

# Per passare a un altro brand gestito senza ricreare il client:
client.with_managed_user(67890)
v = client.videos.generate("https://example.com/product.jpg", custom_prompt="slow dolly-in")

# Per tornare a chiamate senza act-as:
client.with_managed_user(None)
```

La key agenzia deve avere `agency:act_as` e gli scope richiesti dalla route di
generazione. Lo stato della relazione e gli scope vengono validati dall'API.

---

## 1. Balance

Consulta i crediti residui prima di generare.

```python
bal = client.balance()   # API key: GET /api/v1/me · login: GET /api/auth/stats

print("HS credits:", bal["hs_credits"])
print("Wallet:", bal["wallet_balance"], "€")

# Solo con login: la risposta completa (recent_generations, piani, flag):
stats = client.stats()
```

**Esempio di risultato:**
```json
{
  "hs_credits": 1240,
  "wallet_balance": 48.5,
  "total_credits_used": 360,
  "plan": { "wallet_balance": 48.5, "template_id": "scale", "output_resolution": "4K" }
}
```

---

## 2. Foto

Genera un'immagine prodotto. Per uno scatto **still-life** (solo prodotto, senza
soggetto) passa `still_life=True` e ometti il soggetto.

```python
# Con soggetto (path locali caricati in automatico).
gen = client.images.generate(
    product_image_url="product.jpg",
    subject_image_url="model.jpg",
    ratio="4:5",
)

# Oppure still-life (solo prodotto):
gen = client.images.generate("product.jpg", still_life=True, ratio="1:1")

# Attende il completamento e legge l'immagine.
done = client.images.wait(gen["generation_id"])
print(done["images"][0]["url"])
```

**Esempio di risultato (`done`):**
```json
{
  "generation_id": "img_9f2a",
  "status": "succeeded",
  "images": [{ "url": "https://cdn.heroshots.ai/out/img_9f2a_0.png", "width": 2048, "height": 2560 }],
  "_meta": { "credits_remaining": { "hs_credits": 1232 } }
}
```

---

## 3. Video corto

Animazione breve a partire da un'immagine.

```python
v = client.videos.generate(
    "product.jpg",
    custom_prompt="slow dolly-in, soft studio light",
    ratio="16:9",
    resolution="1080p",
)

done = client.videos.wait(v.get("task_id") or v.get("video_id"))   # succeeded/failed
print(done["video_url"])
```

**Esempio di risultato (`done`):**
```json
{ "task_id": "vid_5c1e", "status": "succeeded", "video_url": "https://cdn.heroshots.ai/out/vid_5c1e.mp4" }
```

---

## 4. Still-life video

Video di prodotto su sfondo, con eventuale cambio sfondo.

```python
task = client.stilllife.start(
    product_url="product.jpg",
    background_url="background.jpg",
    custom_prompt="rotating pedestal, luxury feel",
    duration_seconds=5,
)

done = client.stilllife.wait(task["task_id"])
print(done.get("video_url"))

# (Opzionale, solo con login) prova e applica un nuovo sfondo:
client.stilllife.change_background(task["task_id"], background_url="bg2.jpg")
```

**Esempio di risultato (`done`):**
```json
{ "task_id": "sl_77b0", "status": "succeeded", "video_url": "https://cdn.heroshots.ai/out/sl_77b0.mp4" }
```

---

## 5. Video lungo

Pipeline multi-segmento. Puoi avviarla da una semplice immagine + prompt, oppure
da uno storyboard di Studio Hero (vedi §6).

```python
job = client.longvideo.start(
    image_url="product.jpg",
    custom_prompt="30s ad, three beats: reveal, detail, logo",
    ratio="16:9",
    resolution="1080p",
    duration_seconds=30,          # 30, 45 o 60
)

final = client.longvideo.wait(job["job_id"])   # success = "done"
print(final["final_video_url"])

# Rifare un solo segmento (e, con cascade=True, quelli dopo):
client.longvideo.regenerate_segment(job["job_id"], 1, comment="più lento", cascade=True)
```

**Esempio di risultato (`final`):**
```json
{
  "job_id": 812,
  "status": "done",
  "segment_count": 3,
  "completed_count": 3,
  "segments": [
    { "index": 0, "status": "done", "video_url": "https://cdn/.../seg0.mp4" },
    { "index": 1, "status": "done", "video_url": "https://cdn/.../seg1.mp4" },
    { "index": 2, "status": "done", "video_url": "https://cdn/.../seg2.mp4" }
  ],
  "final_video_url": "https://cdn.heroshots.ai/out/long_812.mp4"
}
```

---

## 6. Studio Hero — tutte le fasi

Il flusso creativo completo del web app: brief → candidati → storyboard →
reference frame 4K → (revisione) → render video lungo.

```python
# --- Fase 0: referenze (path locali → URL ospitati) ---
product = client.uploads.image("product.jpg", folder="products")["public_url"]
subject = client.uploads.image("model.jpg", folder="subjects")["public_url"]
duration = 30

# --- Fase 1: brief suggeriti dall'AI a partire dalle immagini ---
briefs = client.storyboard.brief_suggestions(
    product_image_url=product, subject_image_url=subject,
    duration_seconds=duration, language_code="it",
)
brief = briefs[0]                      # es. l'utente sceglie il primo

# --- Fase 2: concept candidati → se ne sceglie uno ---
candidates = client.storyboard.candidates(
    custom_prompt=brief, duration_seconds=duration,
    product_image_url=product, subject_image_url=subject,
    ratio="16:9", language_code="it",
)
selected = candidates[0]

# --- Fase 3: storyboard completo (async, frame differiti) ---
job = client.storyboard.generate(
    custom_prompt=brief, duration_seconds=duration, selected_candidate=selected,
    product_image_url=product, subject_image_url=subject,
)
sb = client.storyboard.wait(job["job_id"])          # status = "done"
storyboard = sb.get("storyboard") or sb.get("result")

# --- Fase 4: reference frame 4K (async, con progresso) ---
fjob = client.storyboard.frames(storyboard, product_image_url=product, subject_image_url=subject)
frames = client.storyboard.wait(
    fjob["job_id"],
    on_progress=lambda d: print("  frame pronti:", len(d.get("frames_partial") or {})),
)
storyboard = frames.get("storyboard") or storyboard

# --- Fase 5 (opzionale): revisione ---
# rev = client.storyboard.revise("Rendi il segmento 2 più lento", brief, duration, storyboard)
# storyboard = rev.get("storyboard") or storyboard

# --- Fase 6: render video lungo dallo storyboard ---
vjob = client.longvideo.start(image_url=product, storyboard=storyboard, ratio="16:9")
final = client.longvideo.wait(vjob["job_id"])
print(final["final_video_url"])
```

**Esempio di risultato per fase:**

Fase 1 — `brief_suggestions` →
```json
["Spot dinamico urban per il lancio sneaker",
 "Mood luxury slow-motion con focus sul materiale",
 "Storytelling lifestyle: dalla città al primo piano prodotto"]
```

Fase 2 — `candidates` (un elemento) →
```json
{
  "title": "Urban Drop",
  "angle": "energia di strada, taglio rapido",
  "clips": [{ "beat": "reveal", "action": "..." }, { "beat": "detail", "action": "..." }],
  "speaker": "voiceover maschile, tono hype",
  "payoff": "logo + claim finale"
}
```

Fase 3 — `wait(job["job_id"])` →
```json
{
  "job_id": "sb_4d10", "status": "done",
  "storyboard": {
    "segments": [
      { "index": 0, "visual_prompt": "...", "frame_prompt": "...", "image_url": null },
      { "index": 1, "visual_prompt": "...", "frame_prompt": "...", "image_url": null }
    ],
    "reference_frames_pending": true
  }
}
```

Fase 4 — `wait(fjob["job_id"])` (i frame diventano URL) →
```json
{
  "job_id": "fr_88a1", "status": "done",
  "storyboard": { "segments": [
    { "index": 0, "image_url": "https://cdn/.../seg0_start.png" },
    { "index": 1, "image_url": "https://cdn/.../seg1_start.png" }
  ] }
}
```

Fase 6 — `final` → vedi [§5](#5-video-lungo) (`final_video_url`).

> Vedi `examples/full_storyboard_flow.py` per lo script completo eseguibile.

---

## 7. Avatar

```python
# Lista (tuoi + default), con filtri.
data = client.avatars.list(gender="female", per_page=20)
for a in data["avatars"]:
    print(a["id"], a["name"])

one = client.avatars.get(42)

# Nuovo avatar AI.
gen = client.avatars.generate(
    "Aria",
    generate_with_ai=True,
    prompt="donna 30 anni, capelli scuri, sguardo deciso",
    gender="female",
)

# Modifiche.
client.avatars.update(42, name="Aria 2", age=31)
client.avatars.set_image_set(42, "generated")          # usa le foto generate
client.avatars.regenerate_view(42, "closeup")          # rifà una vista (async)
client.avatars.generate_voice(42, generation_note="voce calda, italiana")

# Outfit (slot: hat, top, belt, pants, shoes, accessories), max 6 capi.
found = client.avatars.resolve_outfit_link("https://shop.example.com/giacca")
client.avatars.change_outfit(42, items=[
    {"slot": "top", "image_url": found["image_urls"][0], "title": found.get("title")},
    {"slot": "shoes", "link_url": "https://shop.example.com/sneakers"},
    {"slot": "hat", "description": "berretto di lana nero"},
])
client.avatars.restore_outfit(42)                      # annulla l'ultimo cambio
```

**Esempio di risultato (`data`):**
```json
{
  "avatars": [
    { "id": 42, "name": "Aria", "image_url": "https://cdn/.../42.png" },
    { "id": 7,  "name": "Default Male 01", "is_default": true, "image_url": "https://cdn/.../d7.png" }
  ],
  "total": 2, "page": 1, "pages": 1
}
```

---

## 8. Listino e preventivi

```python
catalog = client.pricing.catalog()                         # prezzi del tuo piano
q = client.pricing.quote("video", duration_seconds=30)      # costo prima di generare
pk = client.pricing.video_packages_quote("growth")          # pacchetti video
```

---

## 9. Storico e download

```python
page = client.generations.list(type="video", per_page=20)
for g in client.generations.iterate(type="image"):          # tutte le pagine
    print(g["id"])

client.images.download(1234, "out/foto.jpg")    # stesso watermark/risoluzione della generazione
client.videos.download(1235, "out/spot.mp4")
raw = client.images.download(1234)              # senza dest: ritorna i bytes
```

---

## 10. Generazione in serie (bulk)

```python
bulk = client.bulk.create(prompt="modella in studio, luce morbida", avatar_id=42)
client.bulk.upload_images(bulk["id"], ["p1.jpg", "p2.jpg", "p3.jpg"])
client.bulk.start(bulk["id"])
final = client.bulk.wait(bulk["id"])            # completed / partially_completed / failed
client.bulk.download_generated(bulk["id"], "out/bulk.zip")
```

---

## 11. Libreria

```python
asset = client.assets.create("Borsa Milano", "borsa.jpg", category_id=3)
client.assets.add_image(asset["id"], "borsa_retro.jpg")

col = client.collections.create("Primavera 2027")
client.collections.add_generation(col["id"], 1234)

client.backgrounds.create(image_url="https://example.com/bg.jpg", name="Spiaggia")
cats = client.categories.list()
```

---

## 12. Avatar di persone reali (BYO)

Solo con login. Il brand firma una volta la manleva; per ogni persona servono
liberatoria firmata e documento d'identità.

```python
status = client.legal.byo_status()                       # can_create_byo, ...
client.legal.manleva_template("manleva.docx")
client.legal.liberatoria_template("liberatoria.docx")

release = client.uploads.consent_document("liberatoria_firmata.pdf")["public_url"]
id_doc = client.uploads.consent_document("carta_identita.jpg")["public_url"]

client.legal.attach_liberatoria(
    tenant_id, avatar_id,
    release_doc_url=release, id_doc_url=id_doc,
    model_email="model@example.com", model_dob="1995-04-12",
)
```

---

## 13. Agenzie: brand gestiti

```python
client = Client(api_key="lz_live_AGENCY_KEY")
clients = client.agency.clients()["clients"]
rel = client.agency.invite_client("brand@example.com")
client.agency.topup(rel["id"], 50.0)                     # EUR dal wallet agenzia

# Generare come il brand: vedi §0.1 (managed_user_id).
```

---

## Gestione errori

Ogni errore lancia un'eccezione tipizzata che estende `heroshots.ApiError`
(`.code`, `.status`, `.details`).

```python
from heroshots import QuotaExceededError, ValidationError

try:
    client.videos.generate("product.jpg")
except QuotaExceededError as e:
    print("Crediti esauriti:", e.message)
except ValidationError as e:
    print("Payload non valido:", e.code)
```

| Eccezione | Quando |
|---|---|
| `ValidationError` | payload non valido |
| `AuthError` / `TokenExpiredError` | token mancante/non valido/scaduto |
| `ForbiddenError` | piano/permessi non sufficienti (es. API key sul piano Free) |
| `NotFoundError` | risorsa o job inesistente/scaduto |
| `QuotaExceededError` | crediti/quota esauriti |
| `BillingError` | nessun metodo di pagamento o dati di fatturazione/IVA mancanti |
| `ProviderError` | generazione fallita (anche job falliti) |
| `RateLimitError` | troppe richieste (429), dopo i tentativi automatici; `retry_after` in secondi |
| `ServiceUnavailableError` / `InternalError` | problemi lato server |
