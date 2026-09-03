"""
reverse_search.py — Step 2: Web / social media search

Runs a genuine reverse-image search using SerpAPI's Google Lens API.
This is a real API call (not a hardcoded result) that returns visual
matches — real pages across the web where a visually similar/identical
copy of the image appears, which is how we find the matching social post.

SerpAPI requires the image to be reachable via a public URL (it uploads
that URL to Google Lens on your behalf), so this script first uploads
the local image to a temporary public host (0x0.st) before searching.
For a real submission, prefer hosting the demo image somewhere you
control (e.g. a GitHub raw URL) instead of relying on a throwaway host.

Setup:
    1. Sign up free at https://serpapi.com/users/sign_up (free plan:
       250 searches/month, no credit card required).
    2. Copy your API key from https://serpapi.com/manage-api-key
    3. Set SERPAPI_KEY in your .env file.

Usage:
    python reverse_search.py path/to/photo.jpg
"""

import sys
import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()


def upload_image_temporarily(image_path: str) -> str:
    """Uploads the image to a temporary public host so SerpAPI's Google
    Lens engine (which requires a public image URL) can fetch it. Tries
    multiple free hosts in order so a single outage doesn't block you.
    Swap this for your own hosting (e.g. a GitHub raw URL) for anything
    beyond a quick demo — these are throwaway hosts, not for sensitive
    images."""
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    # Try catbox.moe first, fall back to 0x0.st if it's unavailable.
    try:
        response = requests.post(
            "https://catbox.moe/user/api.php",
            data={"reqtype": "fileupload"},
            files={"fileToUpload": image_bytes},
            timeout=30,
        )
        response.raise_for_status()
        url = response.text.strip()
        if url.startswith("http"):
            return url
    except requests.RequestException:
        pass

    response = requests.post("https://0x0.st", files={"file": image_bytes}, timeout=30)
    response.raise_for_status()
    return response.text.strip()


def reverse_image_search(image_path: str, image_url: str = None) -> dict:
    """If image_url is provided (e.g. a GitHub raw URL), it's used directly
    — this is the recommended path since it doesn't depend on a flaky
    throwaway host. Otherwise, falls back to auto-uploading image_path to
    a temporary public host."""
    api_key = os.environ["SERPAPI_KEY"]
    if image_url is None:
        image_url = upload_image_temporarily(image_path)

    response = requests.get(
        "https://serpapi.com/search",
        params={
            "engine": "google_lens",
            "url": image_url,
            "type": "visual_matches",
            "api_key": api_key,
        },
    )
    response.raise_for_status()
    data = response.json()

    if "error" in data:
        raise RuntimeError(f"SerpAPI error: {data['error']}")

    matches = []
    for match in data.get("visual_matches", []):
        matches.append({
            "url": match.get("link"),
            "page_title": match.get("title"),
            "score": match.get("position"),  # lower position = closer match
            "source": match.get("source"),
        })

    result = {
        "image_path": image_path,
        "image_url_used": image_url,
        "best_guess_labels": [data.get("search_metadata", {}).get("engine")] if data.get("search_metadata") else [],
        "matching_pages": matches,
        "full_matching_image_urls": [m.get("link") for m in matches],
        "partial_matching_image_urls": [],
    }
    return result


def pick_best_social_match(result: dict) -> dict | None:
    """Very simple heuristic: prefer pages_with_matching_images whose URL
    contains a known social media domain, ranked by Vision's own score."""
    social_domains = [
        "instagram.com", "facebook.com", "twitter.com", "x.com",
        "linkedin.com", "tiktok.com", "pinterest.com", "reddit.com",
    ]
    candidates = [
        m for m in result["matching_pages"]
        if any(d in m["url"] for d in social_domains)
    ]
    if not candidates:
        return None
    # 'score' here is the result's position in Google Lens's ranking
    # (0 = closest match), so sort ascending rather than descending.
    candidates.sort(key=lambda m: m.get("score", 999))
    return candidates[0]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python reverse_search.py <image_path> [public_image_url]")
        sys.exit(1)

    image_path = sys.argv[1]
    image_url = sys.argv[2] if len(sys.argv) > 2 else None

    result = reverse_image_search(image_path, image_url=image_url)
    best = pick_best_social_match(result)
    print(json.dumps({"search_result": result, "best_social_match": best}, indent=2))
