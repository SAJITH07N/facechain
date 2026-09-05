"""
blockchain_verify.py — Step 3: Blockchain upload & verification

Uploads a tamper-evident hash of the discovered post (image hash + matched
URL + timestamp) to the ProofRegistry smart contract deployed on the
Sepolia Ethereum testnet, then re-derives the hash and reads it back
on-chain to prove the record hasn't been altered.

Setup:
  1. Deploy contracts/ProofRegistry.sol to Sepolia (e.g. via Remix
     https://remix.ethereum.org — connect MetaMask on Sepolia, compile,
     deploy). Copy the deployed address into CONTRACT_ADDRESS below or
     pass it as an env var.
  2. Get a free Sepolia RPC URL from Infura/Alchemy.
  3. Get Sepolia test ETH from a faucet (e.g. sepoliafaucet.com).
  4. Set env vars: RPC_URL, PRIVATE_KEY, CONTRACT_ADDRESS

Usage:
    python blockchain_verify.py submit <image_sha256> <matched_url>
    python blockchain_verify.py verify <image_sha256> <matched_url> <timestamp>
"""

import os
import sys
import json
import hashlib
import time
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

CONTRACT_ABI = [
    {
        "inputs": [
            {"internalType": "bytes32", "name": "recordHash", "type": "bytes32"},
            {"internalType": "string", "name": "matchedUrl", "type": "string"},
        ],
        "name": "submitProof",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "recordHash", "type": "bytes32"}],
        "name": "verifyProof",
        "outputs": [
            {"internalType": "bool", "name": "exists", "type": "bool"},
            {"internalType": "string", "name": "matchedUrl", "type": "string"},
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
            {"internalType": "address", "name": "submitter", "type": "address"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
]


def get_web3() -> Web3:
    rpc_url = os.environ.get("RPC_URL")
    if not rpc_url or "YOUR_PROJECT_ID" in rpc_url or "YOUR_INFURA_PROJECT_ID" in rpc_url:
        raise RuntimeError(
            f"RPC_URL is missing or still has the placeholder in it. "
            f"Current value: {rpc_url!r}"
        )
    print(f"[debug] Connecting to RPC_URL: {rpc_url}")
    try:
        w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 15}))
        connected = w3.is_connected()
    except Exception as e:
        raise RuntimeError(f"Connection attempt raised an exception: {type(e).__name__}: {e}")
    if not connected:
        raise RuntimeError(
            f"w3.is_connected() returned False for RPC_URL: {rpc_url}. "
            f"This usually means the URL is wrong, the API key is invalid, "
            f"or the network/firewall is blocking the request."
        )
    return w3


def get_contract(w3: Web3):
    address = Web3.to_checksum_address(os.environ["CONTRACT_ADDRESS"])
    return w3.eth.contract(address=address, abi=CONTRACT_ABI)


def compute_record_hash(image_sha256: str, matched_url: str, timestamp: int) -> bytes:
    """This is the tamper-evident fingerprint we anchor on-chain.
    Anyone with the original image + matched URL + timestamp can
    recompute this exact hash to verify nothing was changed."""
    payload = f"{image_sha256}|{matched_url}|{timestamp}".encode("utf-8")
    return hashlib.sha256(payload).digest()


def submit(image_sha256: str, matched_url: str) -> dict:
    w3 = get_web3()
    contract = get_contract(w3)
    account = w3.eth.account.from_key(os.environ["PRIVATE_KEY"])

    timestamp = int(time.time())
    record_hash = compute_record_hash(image_sha256, matched_url, timestamp)

    tx = contract.functions.submitProof(record_hash, matched_url).build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
        "gas": 500000,
        "maxFeePerGas": w3.to_wei("30", "gwei"),
        "maxPriorityFeePerGas": w3.to_wei("2", "gwei"),
        "chainId": w3.eth.chain_id,
    })
    signed = account.sign_transaction(tx)
    # eth-account renamed this attribute across versions: older releases use
    # rawTransaction, newer ones use raw_transaction. Support both.
    raw_tx = getattr(signed, "raw_transaction", None) or getattr(signed, "rawTransaction", None)
    tx_hash = w3.eth.send_raw_transaction(raw_tx)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    if receipt.status != 1:
        raise RuntimeError(
            f"Transaction {tx_hash.hex()} was mined but REVERTED (status={receipt.status}). "
            f"Check it on Etherscan: https://sepolia.etherscan.io/tx/{tx_hash.hex()} "
            f"— common causes: 'Proof already exists' (duplicate recordHash), "
            f"or insufficient gas."
        )

    return {
        "tx_hash": tx_hash.hex(),
        "block_number": receipt.blockNumber,
        "record_hash": record_hash.hex(),
        "timestamp": timestamp,
        "matched_url": matched_url,
        "explorer_link": f"https://sepolia.etherscan.io/tx/{tx_hash.hex()}",
    }


def verify(image_sha256: str, matched_url: str, timestamp: int) -> dict:
    w3 = get_web3()
    contract = get_contract(w3)

    record_hash = compute_record_hash(image_sha256, matched_url, timestamp)
    exists, on_chain_url, on_chain_ts, submitter = contract.functions.verifyProof(record_hash).call()

    return {
        "exists_on_chain": exists,
        "recomputed_hash": record_hash.hex(),
        "on_chain_matched_url": on_chain_url,
        "on_chain_timestamp": on_chain_ts,
        "submitter_address": submitter,
        "verified": exists and on_chain_url == matched_url,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]
    if command == "submit":
        image_sha256, matched_url = sys.argv[2], sys.argv[3]
        print(json.dumps(submit(image_sha256, matched_url), indent=2))
    elif command == "verify":
        image_sha256, matched_url, timestamp = sys.argv[2], sys.argv[3], int(sys.argv[4])
        print(json.dumps(verify(image_sha256, matched_url, timestamp), indent=2))
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)