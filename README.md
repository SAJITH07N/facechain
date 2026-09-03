# FaceChain — Face Identification & Blockchain Verification

Built for HH Goa 2026 Shortlisting Task 3.

A three-stage pipeline:

**Face scan → Web/social media search → Blockchain upload & verification**

1. **Face identification** (`src/face_id.py`) — detects a face in an input
   image and encodes it as a 128-dimensional vector using the
   `face_recognition` library (dlib's ResNet-based face recognition model).
   Also computes a SHA-256 hash of the raw image, used later as the
   fingerprint we anchor on-chain.

2. **Web / social media search** (`src/reverse_search.py`) — runs a genuine
   reverse-image search using **Google Cloud Vision's Web Detection API**.
   This returns real pages on the web where a matching (or partially
   matching) copy of the image appears. A simple heuristic then ranks
   those results to surface the best social-media domain match
   (Instagram, X/Twitter, Facebook, LinkedIn, TikTok, Reddit, Pinterest).

3. **Blockchain verification** (`src/blockchain_verify.py`,
   `contracts/ProofRegistry.sol`) — once a matching post is found, we
   compute `SHA256(image_hash | matched_url | timestamp)` and submit it to
   a small `ProofRegistry` smart contract deployed on the **Ethereum
   Sepolia testnet**. The record is then re-verified by recomputing the
   hash from the original inputs and reading the on-chain record back —
   if they match, the data hasn't been tampered with since submission.

`src/pipeline.py` runs all three stages end-to-end and prints a final JSON
report with the face hash, matched post URL, transaction hash, and
verification result.

## Why Sepolia (and not mainnet)

Sepolia is a free public Ethereum testnet, so the proof is a real,
publicly verifiable on-chain transaction (anyone can check it on
[Sepolia Etherscan](https://sepolia.etherscan.io/)) without spending real
money — appropriate for a hackathon demo while still demonstrating a
genuine tamper-evident blockchain record.

## Setup

1. **Clone & install dependencies**
   ```bash
   git clone <this-repo-url>
   cd facechain
   pip install -r requirements.txt
   ```
   Note: `dlib` needs CMake and a C++ compiler to build. On Windows the
   easiest path is `pip install dlib` via a prebuilt wheel, or use
   `conda install -c conda-forge dlib`.

2. **Google Cloud Vision setup**
   - Create a GCP project, enable the **Cloud Vision API**.
   - Create a service account, download its JSON key.
   - Copy `.env.example` to `.env` and set `GOOGLE_APPLICATION_CREDENTIALS`
     to the path of that key file.

3. **Deploy the smart contract**
   - Open [Remix IDE](https://remix.ethereum.org), paste in
     `contracts/ProofRegistry.sol`, compile it.
   - Connect MetaMask, switch to Sepolia testnet, get free test ETH from a
     faucet (e.g. `sepoliafaucet.com`).
   - Deploy the contract, copy the deployed address into `.env` as
     `CONTRACT_ADDRESS`.

4. **Set remaining env vars**
   - `RPC_URL`: a free Sepolia RPC endpoint from Infura or Alchemy.
   - `PRIVATE_KEY`: the private key of a test wallet holding Sepolia ETH
     (never use a real/mainnet wallet key here).

5. **Run the pipeline**
   ```bash
   export $(cat .env | xargs)   # or use python-dotenv
   python src/pipeline.py path/to/face_scan.jpg
   ```

## Individual stage scripts

Each stage can also be run standalone for testing:
```bash
python src/face_id.py path/to/photo.jpg
python src/reverse_search.py path/to/photo.jpg
python src/blockchain_verify.py submit <image_sha256> <matched_url>
python src/blockchain_verify.py verify <image_sha256> <matched_url> <timestamp>
```

## Known limitations

- **Search recall**: Google Vision's Web Detection only surfaces images
  that are publicly indexed and visually similar to the exact input photo.
  If the only copy of a post uses a cropped/filtered/heavily-edited image,
  or the account is private, it may not be found. This is a known
  precision/recall limitation of reverse image search generally, not
  specific to this implementation.
- **No cross-referencing with the face encoding**: the current pipeline
  uses image-level matching (via Vision API) to find the social post,
  not per-face similarity matching across all faces returned. `face_id.py`
  exposes `compare_faces()` for this, but it isn't wired into the search
  step since Vision's Web Detection doesn't expose per-face candidate
  images to compare against.
- **Gas / testnet reliability**: Sepolia is a public testnet maintained by
  the community; RPC providers occasionally rate-limit free tiers, and
  faucets can be slow. Budget time for this before recording the demo.
- **One proof per unique hash**: the contract's `submitProof` reverts if
  the exact same `recordHash` is submitted twice (prevents accidental
  duplicate records for the identical input).
- **Ethical scope**: this pipeline is built and demonstrated using
  self-consented data (the builder's own photo and known social account).
  It is not intended or tested for identifying third parties without
  their consent.

## Tech stack

- Python 3.11
- `face_recognition` / dlib — face detection & encoding
- Google Cloud Vision API — reverse image / web search
- `web3.py` + Solidity — blockchain interaction
- Ethereum Sepolia testnet
