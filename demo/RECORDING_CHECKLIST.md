# Screen Recording Checklist

Record a single continuous run of `python src/pipeline.py <your_photo.jpg>`
showing, in order:

1. Terminal starts, face detected + SHA-256 printed (stage 1)
2. Vision API call goes out, matching pages print, best social match URL
   shown (stage 2) — briefly switch to a browser tab and open that URL to
   show it's a real, live post
3. Transaction submitted to Sepolia — show the printed Etherscan link,
   open it in browser to show the confirmed transaction on-chain (stage 3)
4. Verification step prints `"verified": true`
5. (Optional but strong) Manually re-run `verify` with the same inputs a
   second time afterward to show the on-chain record persists

Keep it as one take, no editing needed — a plain screen capture of the
terminal + browser tabs is enough per the task requirements.
