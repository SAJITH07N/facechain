// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/// @title ProofRegistry
/// @notice Stores a tamper-evident record linking a face-scan hash to the
///         matching social media post that was found for it. Anyone can
///         later re-derive the same hash from the original data and check
///         it against what's stored here to verify nothing was altered.
contract ProofRegistry {
    struct Proof {
        bytes32 recordHash;   // SHA-256 hash of {image_sha256, matched_url, timestamp}
        string matchedUrl;    // the discovered social media post URL
        uint256 timestamp;    // block timestamp at submission
        address submitter;
    }

    // recordHash => Proof
    mapping(bytes32 => Proof) public proofs;

    event ProofSubmitted(bytes32 indexed recordHash, string matchedUrl, address indexed submitter, uint256 timestamp);

    function submitProof(bytes32 recordHash, string calldata matchedUrl) external {
        require(proofs[recordHash].timestamp == 0, "Proof already exists");

        proofs[recordHash] = Proof({
            recordHash: recordHash,
            matchedUrl: matchedUrl,
            timestamp: block.timestamp,
            submitter: msg.sender
        });

        emit ProofSubmitted(recordHash, matchedUrl, msg.sender, block.timestamp);
    }

    function verifyProof(bytes32 recordHash) external view returns (bool exists, string memory matchedUrl, uint256 timestamp, address submitter) {
        Proof memory p = proofs[recordHash];
        exists = p.timestamp != 0;
        matchedUrl = p.matchedUrl;
        timestamp = p.timestamp;
        submitter = p.submitter;
    }
}
