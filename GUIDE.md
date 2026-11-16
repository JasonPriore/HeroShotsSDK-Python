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
| Studio Hero (storyboard, tutte le fasi, voci, montaggio automatico) | `storyboard` + `audio` + `longvideo` |
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
    subject_image_url="model.jpg",      # oppure avatar_id=42
    aspect_ratio="3:4",                 # 1:1 16:9 4:3 3:4 9:16 3:2 2:3 21:9
    size="2K",                          # 720p 1080p 2K 4K
)
print(gen["url"])                        # la chiamata attende l'immagine finita

# Oppure still-life (solo prodotto):
gen = client.images.generate("product.jpg", still_life=True, aspect_ratio="1:1")

# Per non tenere aperta la richiesta: async_generation=True, poi wait().
job = client.images.generate("product.jpg", avatar_id=42, async_generation=True)
done = client.images.wait(job["generation_id"])     # status "done" o "failed"
print(done["output_url"])
```

**Esempio di risultato (`gen`, chiamata normale):**
```json
{
  "url": "https://cdn.heroshots.ai/out/img_9f2a.png",
  "generation_id": "gen_9f2a",
  "_meta": { "credits_remaining": { "hs_credits": 1232, "currency_credit": 48.1 },
             "charges": { "cost_charged": 0.39, "billing_operation": "image" } }
}
```

**Esempio di risultato (`done`, dopo `wait`):**
```json
{ "status": "done", "generation_id": "gen_9f2a", "output_url": "https://cdn.heroshots.ai/out/img_9f2a.png", "error": null }
```

---

## 3. Video corto

Animazione breve a partire da un'immagine.

```python
v = client.videos.generate(
    "product.jpg",
    custom_prompt="slow dolly-in, soft studio light",
    duration_seconds=15,      # blocchi da 15 s
    ratio="16:9",
    resolution="1080p",
)

done = client.videos.wait(v["video_id"])   # succeeded / failed
print(done["video_url"])
```

`generate()` torna appena il video è stato inviato al motore, con un
`video_id`; `wait()` lo segue fino alla fine. Non passare `async_generation`:
in quel caso l'API restituisce un `generation_id` che `videos.wait()` non segue.

**Esempio di risultato (`done`):**
```json
{ "task_id": "cgt-2026…", "status": "succeeded", "video_url": "https://cdn.heroshots.ai/out/vid_5c1e.mp4" }
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

done = client.stilllife.wait(task["task_id"])      # status "done" o "failed"
print(done["processed_video_url"])

# (Opzionale, solo con login) prova e applica un nuovo sfondo:
client.stilllife.change_background(task["task_id"], background_url="bg2.jpg")
```

**Esempio di risultato (`done`):**
```json
{ "task_id": 77, "status": "done", "processed_video_url": "https://cdn.heroshots.ai/out/sl_77.mp4", "error": null }
```

---

## 5. Video lungo

Pipeline multi-segmento. Puoi avviarla da una semplice immagine + prompt, oppure
da uno storyboard di Studio Hero (vedi §6: `start_from_storyboard`).

```python
job = client.longvideo.start(
    image_url="product.jpg",
    custom_prompt="30s ad, three beats: reveal, detail, logo",
    ratio="16:9",
    resolution="1080p",
    duration_seconds=30,          # 30, 45 o 60
    # Facoltativo (solo con login): montaggio automatico dopo l'export.
    montage={"brief": "Sconto 20% fino a domenica", "language_code": "it",
             "logo_url": "https://cdn/.../logo.png", "logo_mode": "in_video"},
)

# Attende che tutti i segmenti siano pronti (status "segments_ready").
ready = client.longvideo.wait(job["job_id"])
for seg in ready["segments"]:
    print(seg["index"], seg["video_url"])

# Rifare un solo segmento (e, con cascade=True, quelli dopo):
client.longvideo.regenerate_segment(job["job_id"], 1, comment="più lento", cascade=True)

# Montaggio finale (solo con login): unisce i segmenti in final_video_url.
# Se è stato chiesto il montaggio automatico, render() aspetta anche quello.
final = client.longvideo.render(job["job_id"])     # = wait + export + attesa
video_url = final.get("captioned_final_video_url") or final["final_video_url"]
client.download(video_url, "out/spot.mp4")         # accetta anche URL assoluti
```

Come nel portale, quando i segmenti sono pronti il job si ferma in
`segments_ready`: puoi rivederli o rifarli, poi `export()` (o `render()`) crea il
video unico. L'export non costa nulla. Con una **API key** l'export non è
disponibile: usi i singoli `segments[].video_url`. I video con doppiaggio
arrivano già a `done` con `final_video_url`.

**Montaggio automatico** (grafiche, sottotitoli karaoke, logo, cartello finale):

- all'avvio: `montage={...}` (campi `brief`, `language_code`, `logo_url`,
  `logo_mode` = `"in_video"` | `"end_only"` | `"off"`, `inserts` =
  `[{"url", "label"}]`, immagini mostrate solo nel montaggio);
- dopo la generazione: `client.longvideo.montage(job_id, brief=..., logo_mode=...)`.
  Risponde 202 (parte subito, status `captioning`) oppure con `needs_export: true`
  se il video non è ancora esportato (parte al prossimo `export()`); poi
  `render(job_id)`.

Lo status passa `done` → `captioning` → `done`. I campi da guardare:
`montage_requested`, `montage_pending`, `montage_progress`, `montage_done`,
`montage_report`. Il video montato è **`captioned_final_video_url`**;
`final_video_url` resta il taglio senza montaggio. Se il montaggio fallisce,
`render()` ritorna con `montage_done: false` e `montage_report.error` (il video
originale resta disponibile). `client.longvideo.montage_available()` dice se il
server può fare il montaggio.

**Esempio di risultato (`final`, con montaggio):**
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
  "final_video_url": "https://app.heroshots.ai/image/proxy/long_video/812/final.mp4",
  "captioned_final_video_url": "https://app.heroshots.ai/image/proxy/long_video/812/montage/final.mp4",
  "montage_requested": true,
  "montage_pending": false,
  "montage_done": true,
  "montage_report": { "kind": "full" }
}
```

`client.download(url, dest)` accetta un URL assoluto: il token viene inviato
solo se l'URL è dell'host dell'API (`base_url`), mai a un CDN esterno.

---

## 6. Studio Hero — tutte le fasi

Il flusso del web app, passo per passo: brief → concept → (consigliato) →
storyboard → reference frame 4K → (board) → (revisione) → voci → render con voce
e montaggio automatico → download. Solo con login (portal JWT).

```python
# --- Fase 0: referenze (path locali → URL ospitati) ---
product = client.uploads.image("product.jpg", folder="products")["public_url"]
subject = client.uploads.image("model.jpg", folder="subjects")["public_url"]

# Campi che il portale manda a ogni chiamata storyboard (vedi tabella sotto).
common = dict(
    product_image_url=product,
    subject_image_url=subject,
    duration_seconds=30,              # 30, 45 o 60 per il video lungo
    ratio="9:16",
    resolution="1080p",
    language_code="it",
    video_type="ugc",                 # ugc | cinema | spot_tv | sas_software
    ugc_style="top_creator",          # amateur | top_creator
    look_mode="current",              # tiene l'outfit del soggetto
    storyboard_reference_frames_required=True,
    storyboard_board_required=False,
)

# --- Fase 1: brief suggeriti + quello consigliato ---
briefs = client.storyboard.brief_suggestions(**common)      # [{title, brief, pros, cons}]
rec = client.storyboard.recommend("brief", briefs, **common)
brief = briefs[rec["recommended_index"]]["brief"]

# --- Fase 2: concept candidati + quello consigliato ---
concepts = client.storyboard.candidates(custom_prompt=brief, **common)
rec = client.storyboard.recommend("concept", concepts, custom_prompt=brief,
                                  chosen_brief=brief, **common)
selected = concepts[rec["recommended_index"]]

# --- Fase 3: storyboard completo (async, frame differiti) ---
job = client.storyboard.generate(custom_prompt=brief, selected_candidate=selected, **common)
storyboard = client.storyboard.wait(job["job_id"])["storyboard"]

# --- Fase 4: reference frame 4K (async, con progresso) ---
if storyboard.get("reference_frames_deferred"):
    fjob = client.storyboard.frames(storyboard, **common)
    frames = client.storyboard.wait(
        fjob["job_id"], timeout=900,
        on_progress=lambda d: print("  frame pronti:", len(d.get("frames_partial") or {})),
    )
    storyboard = client.storyboard.merge(storyboard, frames)

# --- Fase 4b (se il server usa la board): immagine storyboard board ---
# bjob = client.storyboard.board(storyboard, **common)
# storyboard = client.storyboard.merge(storyboard, client.storyboard.wait(bjob["job_id"], timeout=900))

# --- Fase 5 (opzionale): revisione — la risposta È lo storyboard rivisto ---
# rev_fields = {k: v for k, v in common.items() if k != "duration_seconds"}
# storyboard = client.storyboard.revise("Rendi il segmento 2 più lento", brief, 30, storyboard,
#                                       selected_candidate=selected, **rev_fields)
# (dopo una revisione rifai la Fase 4 per i nuovi frame)

# --- Fase 6: voci, una per ruolo che parla ---
voices = client.audio.voices()["voices"]          # [{voice_id, name, category, labels, ...}]
roles = client.storyboard.voice_roles(storyboard) # [{key: "subject_1", label, role_type, text, ...}]
voice_ids = {role["key"]: voices[0]["voice_id"] for role in roles}   # scegli tu la voce per ruolo

# --- Fase 7: render come il portale (voce + montaggio automatico) ---
vjob = client.longvideo.start_from_storyboard(
    storyboard,
    product_image_url=product,
    subject_image_url=subject,
    # oppure un avatar: avatar_id=12, avatar_view_type="mezzo_busto"  (vista reale, non "avatar")
    voice_id=voice_ids,               # o una sola voce per tutti i ruoli: voice_id="..."
    language_code="it",
    montage=True,                     # brief, lingua e logo come nel portale
    brief=brief,
    ratio="9:16",
    resolution="1080p",
    # brand_logo_url="https://cdn/.../logo.png", brand_logo_mode="in_video",
)
final = client.longvideo.render(vjob["job_id"])   # segmenti → export → montaggio

# --- Fase 8: download del video montato ---
url = final.get("captioned_final_video_url") or final["final_video_url"]
client.download(url, "out/spot.mp4")
```

**Cosa manda `start_from_storyboard`** (lo stesso body del portale):

| Campo | Da dove |
|---|---|
| `product_image_url`, `subject_image_url`, `additional_product_image_urls` | input |
| `avatar_id` + `avatar_view_type` (+ `avatar_image_set`) | input; la vista deve esistere (`fullbody`, `mezzo_busto`, `closeup`, `profile_left`...); `"avatar"` viene rifiutato |
| `product_box_closed_url` / `product_box_open_url`, `extra_products` (`[{image_url, box_closed_url?, box_open_url?}]`) | input (scatola del prodotto, altri prodotti) |
| `brand_logo_url` + `brand_logo_mode` (`in_video` \| `end_only` \| `off`) | input |
| `custom_prompt` | `storyboard["optimized_prompt"]` (non il brief) |
| `duration` e `duration_seconds` | `storyboard["duration_seconds"]` |
| `studiohero_segment_prompts` | `visual_prompt` (o `seedance_prompt`) di ogni segmento |
| `studiohero_segment_reference_image_urls` | per segmento: `script_sequence.reference_frames[].image_url` + `control_frame.image_url` (omesso se non ci sono frame) |
| `reference_image_urls` | board, prodotto, viste extra, soggetto (senza doppioni) |
| `voiceover_cast`, `tts_voice_id`, `language_code` | `storyboard.voice_cast(storyboard, voice_id)`; `tts_voice_id` = voce del primo ruolo |
| `montage` | `montage=True` → `{brief, language_code, logo_url, logo_mode}`; senza montaggio e con logo `end_only` → `{kind: "outro", ...}` (solo la chiusura animata del logo) |

Gli argomenti extra (`captions=True`, `reference_video_url=...`) vengono inoltrati
così come sono e vincono su tutto. `longvideo.start(storyboard=...)` resta
disponibile e manda solo la parte storyboard (`custom_prompt`, prompt e frame per
segmento, durata).

**Campi delle chiamate storyboard** (in `common`): `video_type` (`ugc` |
`cinema` | `spot_tv` | `sas_software`), `ugc_style` (`amateur` | `top_creator`),
`look_mode` (`current`, oppure `custom` con `look_description`),
`storyboard_reference_frames_required` / `storyboard_board_required`, più gli
stessi input del render (`avatar_id` + `avatar_view_type`, `brand_logo_url` /
`brand_logo_mode`, `product_box_closed_url` / `product_box_open_url`,
`extra_products`, `background_image_url`, `body_posture_image_url`).

**Esempio di risultato per fase:**

Fase 1 — `brief_suggestions` →
```json
[{ "title": "Drop urbano", "brief": "Spot dinamico urban per il lancio sneaker...", "pros": ["..."], "cons": ["..."] },
 { "title": "Luxury slow", "brief": "Mood luxury slow-motion con focus sul materiale...", "pros": [], "cons": [] }]
```

Fase 1/2 — `recommend` →
```json
{ "recommended_index": 0, "reason": "Il prodotto si vede meglio con un taglio dinamico." }
```

Fase 2 — `candidates` (un elemento) →
```json
{
  "id": "concept-1",
  "title": "Urban Drop",
  "logline": "energia di strada, taglio rapido",
  "visual_direction": "camera a mano, luce naturale",
  "clip_plan": ["reveal", "dettaglio", "logo + claim"],
  "voice_roles": ["Soggetto"]
}
```

Fase 3 — `wait(job["job_id"])["storyboard"]` →
```json
{
  "duration_seconds": 30,
  "optimized_prompt": "...",
  "segments": [
    { "index": 1, "visual_prompt": "...", "voiceover_text": "...",
      "script_sequence": { "voice_cast": [{ "role_id": "subject_1", "label_it": "Soggetto", "spoken_it": "..." }],
                           "reference_frames": [{ "role": "start", "image_url": null }] } }
  ],
  "reference_frames_deferred": true,
  "storyboard_board_image_url": null
}
```

Fase 4 — `wait(fjob["job_id"])` (i frame arrivano sotto `frames`) →
```json
{
  "job_id": "fr_88a1", "status": "done",
  "frames": { "segments": [
    { "index": 1, "script_sequence": { "reference_frames": [{ "role": "start", "image_url": "https://cdn/.../seg1_start.png" }] } }
  ], "reference_image_urls": ["https://cdn/.../seg1_start.png"] }
}
```

Fase 6 — `audio.voices()` →
```json
{ "configured": true,
  "voices": [{ "voice_id": "21m00Tcm4TlvDq8ikWAM", "name": "Giulia", "category": "premade",
               "labels": { "accent": "italian" }, "description": "", "preview_url": "https://..." }] }
```

Fase 7 — `final` → vedi [§5](#5-video-lungo) (`captioned_final_video_url`).

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
page = client.generations.list(type="image", per_page=20)
for g in client.generations.iterate(type="video"):          # tutte le pagine
    print(g["id"], g["download_url"])

# L'id da scaricare è quello dello storico (g["id"]), non il generation_id.
log_id = page["generations"][0]["id"]
client.images.download(log_id, "out/foto.jpg")  # stesso watermark/risoluzione della generazione
raw = client.images.download(log_id)            # senza dest: ritorna i bytes
client.videos.download(video_log_id, "out/spot.mp4")
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
