from flask import Flask, request, jsonify
import base64
import json

from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.serialization import load_pem_private_key

app = Flask(__name__)

with open("private.pem", "rb") as f:
    private_key = load_pem_private_key(
        f.read(),
        password=None
    )


@app.route("/flow", methods=["POST"])
def flow():

    body = request.json

    encrypted_flow_data = base64.b64decode(
        body["encrypted_flow_data"]
    )

    encrypted_aes_key = base64.b64decode(
        body["encrypted_aes_key"]
    )

    iv = base64.b64decode(
        body["initial_vector"]
    )

    aes_key = private_key.decrypt(
        encrypted_aes_key,
        padding.PKCS1v15()
    )

    cipher = Cipher(
        algorithms.AES(aes_key),
        modes.GCM(iv)
    )

    decryptor = cipher.decryptor()

    decrypted = decryptor.update(
        encrypted_flow_data
    )

    print(decrypted)

    response_data = {
        "data": {
            "vehicles": [
                {
                    "id": "TN01AB1234",
                    "title": "TN01AB1234"
                },
                {
                    "id": "TN01CD5678",
                    "title": "TN01CD5678"
                }
            ]
        }
    }

    response_json = json.dumps(response_data)

    encryptor = cipher.encryptor()

    encrypted_response = encryptor.update(
        response_json.encode()
    )

    return base64.b64encode(
        encrypted_response
    )


@app.route("/")
def health():
    return "OK"
