"""
face_id.py — Step 1: Face detection & encoding

Detects a face in an input image and produces a 128-dimensional
face encoding using the `face_recognition` library (built on dlib's
ResNet face recognition model).

Usage:
    python face_id.py path/to/photo.jpg
"""

import sys
import json
import hashlib
import face_recognition
import numpy as np


def encode_face(image_path: str) -> dict:
    """Detect the first face in an image and return its encoding + metadata."""
    image = face_recognition.load_image_file(image_path)

    face_locations = face_recognition.face_locations(image, model="hog")
    if not face_locations:
        raise ValueError(f"No face detected in {image_path}")

    encodings = face_recognition.face_encodings(image, known_face_locations=face_locations)
    if not encodings:
        raise ValueError(f"Face detected but encoding failed for {image_path}")

    encoding = encodings[0]  # use the first detected face
    top, right, bottom, left = face_locations[0]

    # A stable content hash of the raw image bytes — used later for the
    # blockchain proof so we have a tamper-evident fingerprint of the
    # exact source image, not just the encoding.
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    image_sha256 = hashlib.sha256(image_bytes).hexdigest()

    return {
        "image_path": image_path,
        "image_sha256": image_sha256,
        "face_box": {"top": top, "right": right, "bottom": bottom, "left": left},
        "encoding": encoding.tolist(),  # 128 floats
    }


def compare_faces(encoding_a: list, encoding_b: list, tolerance: float = 0.6) -> dict:
    """Compare two face encodings. Lower distance = more similar (0.6 is a
    commonly used match threshold for face_recognition)."""
    a = np.array(encoding_a)
    b = np.array(encoding_b)
    distance = np.linalg.norm(a - b)
    return {"distance": float(distance), "is_match": bool(distance <= tolerance)}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python face_id.py <image_path>")
        sys.exit(1)

    result = encode_face(sys.argv[1])
    # Don't dump the full 128-float vector to stdout by default, just a summary
    print(json.dumps({
        "image_path": result["image_path"],
        "image_sha256": result["image_sha256"],
        "face_box": result["face_box"],
        "encoding_preview": result["encoding"][:5] + ["..."],
    }, indent=2))
