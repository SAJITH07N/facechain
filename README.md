# FaceChain — Face Identification & Blockchain Verification

Built for HH Goa 2026 Shortlisting Task 3.

A pipeline with five stages:

**Face scan → Web/social media search → Face-match confidence check → Blockchain upload & verification → Tamper-evidence demonstration**

1. **Face identification** (`src/face_id.py`) — detects a face in an input
   image and encodes it as a 128-dimensional vector using the
   `face_recognition` library (dlib's ResNet-based face recognition model).
   Also computes a SHA-256 hash of the raw image, used later as the
   fingerprint we anchor on-chain.

2. **Web / social media search** (`src/reverse_search.py`) — runs a genuine
   reverse-image search using **SerpAPI's Google Lens API** (free plan,
   no credit card required, 250 searches/month). This returns real visual
   matches from across the web where a similar/identical copy of the
   image appears. A simple heuristic then ranks those results to surface
   the best social-media domain match (Instagram, X/Twitter, Facebook,
   LinkedIn, TikTok, Reddit, Pinterest).

3. **Blockchain verification** (`src/blockchain_verify.py`,
   `contracts/ProofRegistry.sol`) — once a matching post is found, we
   compute `SHA256(image_hash | matched_url | timestamp)` and submit it to
   a small `ProofRegistry` smart contract deployed on the **Ethereum
   Sepolia testnet**. The record is then re-verified by recomputing the
   hash from the original inputs and reading the on-chain record back —
   if they match, the data hasn't been tampered with since submission.

4. **Face-match confidence check** — the pipeline doesn't blindly trust
   the search engine's top result. It downloads the matched image's
   thumbnail, runs the same face detection/encoding used on the original
   scan, and compares the two encodings to report whether they're likely
   the same person. This closes the actual identity-verification loop
   rather than just trusting visual-similarity search.

5. **Tamper-evidence demonstration** — immediately after a successful
   on-chain verification, the pipeline deliberately re-verifies using a
   subtly altered URL and shows that verification correctly fails. This
   is a live demonstration of the "tamper-evident" property the whole
   project is built around, rather than just an assertion of it.

`src/pipeline.py` runs all stages end-to-end and prints a final JSON
report with the face hash, matched post URL, face-match confidence,
transaction hash, verification result, and the tamper-evidence check.

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

2. **SerpAPI setup**
   - Sign up free at [serpapi.com/users/sign_up](https://serpapi.com/users/sign_up)
     (free plan: 250 searches/month, no credit card required).
   - Copy your API key from [serpapi.com/manage-api-key](https://serpapi.com/manage-api-key).
   - Copy `.env.example` to `.env` and set `SERPAPI_KEY` to that key.

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
   python src/pipeline.py path/to/face_scan.jpg "https://your-public-image-url"
   ```
   The second argument (a public image URL, e.g. a GitHub raw URL) is
   optional — if omitted, the script auto-uploads the image to a
   temporary public host instead. Passing your own URL is recommended
   for reliability.

## Individual stage scripts

Each stage can also be run standalone for testing:
```bash
python src/face_id.py path/to/photo.jpg
python src/reverse_search.py path/to/photo.jpg "https://your-public-image-url"
python src/blockchain_verify.py submit <image_sha256> <matched_url>
python src/blockchain_verify.py verify <image_sha256> <matched_url> <timestamp>
```

## Known limitations

- **Temporary image hosting**: SerpAPI's Google Lens engine requires a
  public image URL rather than a direct file upload. `reverse_search.py`
  accepts an optional public image URL directly (recommended — e.g. a
  GitHub raw URL, which is what this repo's own demo uses); if none is
  given, it falls back to auto-uploading the image to a temporary public
  host (tries catbox.moe, then 0x0.st). Throwaway hosts are fine for a
  quick test but not appropriate for sensitive images — use your own
  hosting (a private, signed URL) for anything beyond a demo.
- **Search recall varies significantly by platform**: through testing,
  we found Instagram specifically blocks most search-engine crawlers via
  `robots.txt`, so Google Lens essentially cannot index or surface
  individual Instagram posts by content, regardless of how long they've
  been public. X/Twitter and LinkedIn are considerably more crawlable.
  Newly-posted content anywhere can also take hours to days to be
  indexed. This is a structural limitation of the platforms and the
  search engine, not of this implementation.
- **Face-match confidence has a false-negative mode**: the confidence
  check (`face_match_confidence`) downloads the matched result's
  thumbnail and runs face detection on it — but many social platforms
  serve heavily cropped, low-resolution, or non-portrait thumbnails,
  which can fail face detection even when the underlying post is a
  genuine match. A `"face_detected_in_match": false` result means the
  check was inconclusive, not that the match is wrong.
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
- SerpAPI (Google Lens engine) — reverse image / web search
- `web3.py` + Solidity — blockchain interaction
- Ethereum Sepolia testnet
