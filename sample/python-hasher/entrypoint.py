from __future__ import annotations
import os
import hashlib


class JobEntrypoint:

    def perform(self, attempts: int = 4_000_000) -> str:
        """
        Calculate SHA256 hashes many times
        """
        hasher = hashlib.sha256(os.urandom(256))
        for _ in range(attempts):
            hasher.update(hasher.digest())
        return hasher.hexdigest()

    def docs_input_example(self) -> dict:
        """Return example input values for this model"""
        return {
            'attempts': 4_000_000,
        }
