from __future__ import annotations

import base64
import functools
import hashlib
import math
from typing import Optional, Protocol
import secrets

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from _typeshed import ReadableBuffer


RANDOM_STRING_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def make_password(password: str) -> str:
    hasher = get_hasher()
    salt = hasher.salt()
    return hasher.encode(password, salt)


class Hash(Protocol):
    def __call__(self, string: ReadableBuffer = b"", *, usedforsecurity: bool = True) -> hashlib._Hash:
        ...


class PBKDF2PasswordHasher:
    """
    Secure password hashing using the PBKDF2 algorithm (recommended)

    Configured to use PBKDF2 + HMAC + SHA256.
    The result is a 64 byte binary string.  Iterations may be changed
    safely but you must rename the algorithm if you change SHA256.
    """

    algorithm: str = "pbkdf2_sha256"
    iterations: int = 600000
    digest: Hash = hashlib.sha256
    salt_entropy: int = 128

    def encode(self, password: str, salt, iterations: Optional[int] = None):
        iterations = iterations or self.iterations
        hash = pbkdf2(password, salt, iterations, digest=self.digest)
        hash = base64.b64encode(hash).decode("ascii").strip()
        return "%s$%d$%s$%s" % (self.algorithm, iterations, salt, hash)

    def decode(self, encoded: str):
        algorithm, iterations, salt, hash = encoded.split("$", 3)
        assert algorithm == self.algorithm
        return {
            "algorithm": algorithm,
            "hash": hash,
            "iterations": int(iterations),
            "salt": salt,
        }

    def verify(self, password: str, encoded: str):
        decoded = self.decode(encoded)
        encoded_2 = self.encode(password, decoded["salt"], decoded["iterations"])
        return constant_time_compare(encoded, encoded_2)

    def salt(self) -> str:
        """
        Generate a cryptographically secure nonce salt in ASCII with an entropy
        of at least `salt_entropy` bits.
        """
        # Each character in the salt provides
        # log_2(len(alphabet)) bits of entropy.
        char_count = math.ceil(self.salt_entropy / math.log2(len(RANDOM_STRING_CHARS)))
        return get_random_string(char_count, allowed_chars=RANDOM_STRING_CHARS)


def get_random_string(length: int, allowed_chars: str = RANDOM_STRING_CHARS) -> str:
    """
    Return a securely generated random string.

    The bit length of the returned value can be calculated with the formula:
        log_2(len(allowed_chars)^length)

    For example, with default `allowed_chars` (26+26+10), this gives:
      * length: 12, bit length =~ 71 bits
      * length: 22, bit length =~ 131 bits
    """
    return "".join(secrets.choice(allowed_chars) for i in range(length))


def pbkdf2(password: str, salt: str, iterations: int, dklen: int = 0, digest: Optional[Hash] = None):
    """Return the hash of password using pbkdf2."""
    if digest is None:
        digest = hashlib.sha256

    password_bytes = password.encode("utf-8", "strict")
    salt_bytes = salt.encode("utf-8", "strict")
    return hashlib.pbkdf2_hmac(digest().name, password_bytes, salt_bytes, iterations, dklen or None)


def constant_time_compare(val1, val2):
    """Return True if the two strings are equal, False otherwise."""
    return secrets.compare_digest(val1.encode("utf-8", "strict"), val2.encode("utf-8", "strict"))


@functools.lru_cache
def get_hasher() -> PBKDF2PasswordHasher:
    return PBKDF2PasswordHasher()
