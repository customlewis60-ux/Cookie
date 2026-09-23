"""Future privacy adapters. No ZK implementation or chain integration is claimed."""
from typing import Protocol

class IdentityProvider(Protocol):
    async def verify_signature(self, address: str, challenge: str, signature: str) -> bool: ...

class PrivacyProofProvider(Protocol):
    async def verify_authorization_proof(self, proof: bytes, public_inputs: dict) -> bool: ...

# EVM/Solana identity and independent Zcash ecosystem adapters can implement
# these interfaces in separate modules. Nothing here creates or verifies proofs.