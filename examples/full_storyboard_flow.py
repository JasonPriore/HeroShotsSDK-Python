"""End-to-end StudioHero flow, mirroring the web app, via the HeroShots SDK.

Reproduces: login -> upload -> balance -> brief suggestions (+ recommended) ->
concepts (+ recommended) -> storyboard -> reference frames -> voices -> long
video with voice and auto-edit -> download. Every generation step is BILLABLE.

Run:
    HEROSHOTS_EMAIL=dev@partner.com HEROSHOTS_PASSWORD=... \
    python examples/full_storyboard_flow.py product.jpg model.jpg
"""

import os
import sys

from heroshots import Client


def main(product_path: str, model_path: str) -> None:
    # Base URL defaults to https://app.heroshots.ai.
    client = Client.from_login(
        email=os.environ["HEROSHOTS_EMAIL"],
        password=os.environ["HEROSHOTS_PASSWORD"],
    )
    print("logged in as", client.me()["email"])

    # 1. Upload references (local files -> hosted URLs).
    product_url = client.uploads.image(product_path, folder="products")["public_url"]
    subject_url = client.uploads.image(model_path, folder="subjects")["public_url"]

    # 2. (Optional) check the balance before spending credits.
    bal = client.balance()
    print("balance:", {"hs_credits": bal.get("hs_credits"), "wallet_balance": bal.get("wallet_balance")})

    # Fields the portal sends with every storyboard call.
    common = dict(
        product_image_url=product_url,
        subject_image_url=subject_url,
        duration_seconds=30,
        ratio="9:16",
        resolution="1080p",
        language_code="it",
        video_type="ugc",
        ugc_style="top_creator",
        look_mode="current",
        storyboard_reference_frames_required=True,
    )

    # 3. Brief suggestions -> the recommended one.
    briefs = client.storyboard.brief_suggestions(**common)
    index = client.storyboard.recommend("brief", briefs, **common)["recommended_index"] if len(briefs) > 1 else 0
    brief = briefs[index]["brief"]
    print("brief:", brief)

    # 4. Concept candidates -> the recommended one.
    concepts = client.storyboard.candidates(custom_prompt=brief, **common)
    index = 0
    if len(concepts) > 1:
        index = client.storyboard.recommend(
            "concept", concepts, custom_prompt=brief, chosen_brief=brief, **common
        )["recommended_index"]
    selected = concepts[index]
    print("concept:", selected.get("title"))

    # 5. Full storyboard (async, frames deferred).
    job = client.storyboard.generate(custom_prompt=brief, selected_candidate=selected, **common)
    storyboard = client.storyboard.wait(job["job_id"])["storyboard"]
    print("storyboard ready:", len(storyboard.get("segments", [])), "segments")

    # 6. Reference frames (async, progressive) -> merged into the storyboard.
    if storyboard.get("reference_frames_deferred"):
        fjob = client.storyboard.frames(storyboard, **common)
        frames = client.storyboard.wait(
            fjob["job_id"],
            timeout=900,
            on_progress=lambda d: print("  frames ready:", len(d.get("frames_partial") or {})),
        )
        storyboard = client.storyboard.merge(storyboard, frames)

    # 7. One voice per speaking role.
    voices = client.audio.voices().get("voices") or []
    roles = client.storyboard.voice_roles(storyboard)
    voice_ids = {role["key"]: voices[0]["voice_id"] for role in roles} if voices else None
    print("roles:", [(r["key"], r["text"][:40]) for r in roles])

    # 8. Long video, exactly like the portal's render, with the auto-edit.
    vjob = client.longvideo.start_from_storyboard(
        storyboard,
        product_image_url=product_url,
        subject_image_url=subject_url,
        voice_id=voice_ids,
        language_code="it",
        montage=client.longvideo.montage_available(),
        brief=brief,
        ratio="9:16",
        resolution="1080p",
    )
    final = client.longvideo.render(vjob["job_id"])  # clips -> export -> auto-edit
    url = final.get("captioned_final_video_url") or final.get("final_video_url")
    print("FINAL VIDEO:", url)

    # 9. Download (absolute URLs are accepted).
    print("saved to", client.download(url, "out/spot.mp4"))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: full_storyboard_flow.py <product.jpg> <model.jpg>")
    main(sys.argv[1], sys.argv[2])
