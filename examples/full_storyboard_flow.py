"""End-to-end StudioHero flow, mirroring the web app, via the HeroShots SDK.

Reproduces: login -> upload -> balance -> brief suggestions -> candidates ->
storyboard -> reference frames -> long video. Every generation step is BILLABLE.

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

    duration = 30
    # 2. (Optional) check the balance before spending credits.
    print("balance:", client.balance())

    # 3. Brief suggestions.
    briefs = client.storyboard.brief_suggestions(
        product_image_url=product_url, subject_image_url=subject_url,
        duration_seconds=duration, language_code="it",
    )
    brief = briefs[0]
    print("brief:", brief)

    # 4. Concept candidates -> pick one.
    candidates = client.storyboard.candidates(
        custom_prompt=brief, duration_seconds=duration,
        product_image_url=product_url, subject_image_url=subject_url,
        ratio="16:9", language_code="it",
    )
    selected = candidates[0]

    # 5. Full storyboard (async, frames deferred).
    job = client.storyboard.generate(
        custom_prompt=brief, duration_seconds=duration, selected_candidate=selected,
        product_image_url=product_url, subject_image_url=subject_url,
    )
    sb = client.storyboard.wait(job["job_id"])
    storyboard = sb.get("storyboard") or sb.get("result")
    print("storyboard ready:", len(storyboard.get("segments", [])), "segments")

    # 6. Reference frames (async, progressive).
    fjob = client.storyboard.frames(
        storyboard=storyboard, product_image_url=product_url, subject_image_url=subject_url,
    )
    frames = client.storyboard.wait(
        fjob["job_id"],
        on_progress=lambda d: print("  frames_partial:", d.get("frames_partial")),
    )
    storyboard = frames.get("storyboard") or storyboard

    # 7. Long video render.
    vjob = client.longvideo.start(image_url=product_url, storyboard=storyboard, ratio="16:9")
    result = client.longvideo.wait(vjob["job_id"])
    print("FINAL VIDEO:", result.get("final_video_url"))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: full_storyboard_flow.py <product.jpg> <model.jpg>")
    main(sys.argv[1], sys.argv[2])
