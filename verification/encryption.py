"""
AES-256-GCM credential encryption — ported from encryption.ts
Format: salt(16B) + iv(16B) + ciphertext + auth_tag(16B), all hex-encoded
"""
import os
import hmac
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

SALT_LEN = 16
IV_LEN   = 16
TAG_LEN  = 16


def _derive_key(secret: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100_000)
    return kdf.derive(secret.encode())


def encrypt_credential(plaintext: str, secret: str) -> str:
    """Encrypt a credential string. Returns hex-encoded bundle."""
    salt = os.urandom(SALT_LEN)
    iv   = os.urandom(IV_LEN)
    key  = _derive_key(secret, salt)
    aesgcm = AESGCM(key)
    # AESGCM appends 16-byte tag automatically
    ct_with_tag = aesgcm.encrypt(iv, plaintext.encode(), None)
    ct  = ct_with_tag[:-TAG_LEN]
    tag = ct_with_tag[-TAG_LEN:]
    return salt.hex() + iv.hex() + ct.hex() + tag.hex()


def decrypt_credential(bundle: str, secret: str) -> str:
    """Decrypt a credential bundle produced by encrypt_credential."""
    salt = bytes.fromhex(bundle[:SALT_LEN * 2])
    iv   = bytes.fromhex(bundle[SALT_LEN * 2: SALT_LEN * 2 + IV_LEN * 2])
    tag  = bytes.fromhex(bundle[-TAG_LEN * 2:])
    ct   = bytes.fromhex(bundle[SALT_LEN * 2 + IV_LEN * 2: -TAG_LEN * 2])
    key  = _derive_key(secret, salt)
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(iv, ct + tag, None)
    return plaintext.decode()


def mask_credential(value: str) -> str:
    if len(value) <= 4:
        return "****"
    return "*" * (len(value) - 4) + value[-4:]
