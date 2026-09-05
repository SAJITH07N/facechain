"""
pipeline.py — End-to-end: Face scan -> Web/social search -> Blockchain proof

This is the script to run (and screen-record) for the submission demo.

Usage:
    python pipeline.py path/to/face_scan.jpg
"""

import sys
import json

from face_id import encode_face, encode_face_from_url, compare_faces
from reverse_search import reverse_image_search, pick_best_social_match
from blockchain_verify import submit, verify


def run_pipeline(image_path: str, image_url: str = None):
    print(f"\n[1/4] Detecting & encoding face in {image_path} ...")
    face_result = encode_face(image_path)
    print(f"  -> Face found. Image SHA-256: {face_result['image_sha256']}")

    print("\n[2/4] Searching the web for a matching social media post ...")
    search_result = reverse_image_search(image_path, image_url=image_url)
    best_match = pick_best_social_match(search_result)

    if best_match is None:
        print("  -> No social-media domain match found in results.")
        print("  -> Falling back to top general matching page (if any).")
        best_match = search_result["matching_pages"][0] if search_result["matching_pages"] else None

    if best_match is None:
        print("  -> No matching page found at all. Cannot proceed to blockchain step.")
        return

    matched_url = best_match["url"]
    print(f"  -> Matched post: {matched_url} (score: {best_match.get('score')})")

    print("\n[2.5/4] Checking whether the matched image actually contains the same face ...")
    confidence = {"checked": False}
    thumbnail_url = best_match.get("thumbnail")
    if thumbnail_url:
        matched_face = encode_face_from_url(thumbnail_url)
        if matched_face is not None:
            comparison = compare_faces(face_result["encoding"], matched_face["encoding"])
            confidence = {
                "checked": True,
                "face_detected_in_match": True,
                "distance": comparison["distance"],
                "same_person_likely": comparison["is_match"],
            }
            verdict = "SAME PERSON (high confidence)" if comparison["is_match"] else "different person / uncertain"
            print(f"  -> Face distance: {comparison['distance']:.4f} -> {verdict}")
        else:
            confidence = {"checked": True, "face_detected_in_match": False}
            print("  -> No clear face detected in the matched thumbnail (common for non-portrait matches).")
    else:
        print("  -> No thumbnail available for this match; skipping confidence check.")

    print("\n[3/4] Uploading tamper-evident proof to blockchain (Sepolia testnet) ...")
    submission = submit(face_result["image_sha256"], matched_url)
    print(f"  -> Submitted. Tx: {submission['explorer_link']}")

    print("\nRe-verifying against the on-chain record ...")
    verification = verify(
        face_result["image_sha256"],
        matched_url,
        submission["timestamp"],
    )
    print(f"  -> Verified: {verification['verified']}")

    print("\n[4/4] Tamper-evidence demonstration: re-verifying with an ALTERED url ...")
    tampered_url = matched_url + "#tampered"
    tamper_check = verify(
        face_result["image_sha256"],
        tampered_url,
        submission["timestamp"],
    )
    print(f"  -> Verification with tampered data: {tamper_check['verified']} "
          f"(expected: False — this proves the record is tamper-evident)")

    report = {
        "face": {
            "image_sha256": face_result["image_sha256"],
            "face_box": face_result["face_box"],
        },
        "search": {
            "best_guess_labels": search_result["best_guess_labels"],
            "matched_url": matched_url,
        },
        "face_match_confidence": confidence,
        "blockchain": {
            "submission": submission,
            "verification": verification,
            "tamper_evidence_demo": {
                "tampered_url_tried": tampered_url,
                "verified_with_tampered_data": tamper_check["verified"],
                "correctly_rejected": tamper_check["verified"] is False,
            },
        },
    }

    print("\n===== FINAL REPORT =====")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pipeline.py <image_path> [public_image_url]")
        sys.exit(1)
    image_url = sys.argv[2] if len(sys.argv) > 2 else None
    run_pipeline(sys.argv[1], image_url=image_url)
