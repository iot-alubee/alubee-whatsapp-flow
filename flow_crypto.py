"""Encrypt / decrypt WhatsApp Flow endpoint payloads (Meta data channel)."""

from __future__ import annotations

import base64
import json
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def load_private_key(path: str):
    with open(path, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def decrypt_request(body: dict, private_key) -> tuple[dict, bytes, bytes]:
    encrypted_flow_data = base64.b64decode(body["encrypted_flow_data"])
    encrypted_aes_key = base64.b64decode(body["encrypted_aes_key"])
    iv = base64.b64decode(body["initial_vector"])

    try:
        aes_key = private_key.decrypt(
            encrypted_aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
    except Exception:
        aes_key = private_key.decrypt(
            encrypted_aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA1()),
                algorithm=hashes.SHA1(),
                label=None,
            ),
        )

    ciphertext = encrypted_flow_data[:-16]
    tag = encrypted_flow_data[-16:]
    cipher = Cipher(algorithms.AES(aes_key), modes.GCM(iv, tag))
    decryptor = cipher.decryptor()
    decrypted_data = decryptor.update(ciphertext) + decryptor.finalize()
    flow_data = json.loads(decrypted_data.decode("utf-8"))
    return flow_data, aes_key, iv


def encrypt_response(response_data: dict[str, Any], aes_key: bytes, iv: bytes) -> str:
    response_json = json.dumps(response_data)
    response_iv = bytes(b ^ 0xFF for b in iv)
    response_cipher = Cipher(algorithms.AES(aes_key), modes.GCM(response_iv))
    encryptor = response_cipher.encryptor()
    encrypted_response = encryptor.update(response_json.encode("utf-8")) + encryptor.finalize()
    encrypted_response += encryptor.tag
    return base64.b64encode(encrypted_response).decode()
