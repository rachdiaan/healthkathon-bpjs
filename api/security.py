"""Hash password (scrypt stdlib) dan token session. Format hash: scrypt$n$r$p$salt_hex$hash_hex."""
from __future__ import annotations

import hashlib
import hmac
import secrets

SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**14, 8, 1
DKLEN = 32


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=DKLEN)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, n, r, p, salt_hex, hash_hex = stored.split("$")
        if algo != "scrypt":
            return False
        dk = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=int(n), r=int(r), p=int(p),
                            dklen=len(hash_hex) // 2)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(dk.hex(), hash_hex)


# Hash dummy untuk menyamakan waktu respons saat username tidak ada (SEC-5).
DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
