from flask import Flask, request, jsonify
import base64
import json
import traceback

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

app = Flask(__name__)

# Load private key
with open("private.pem", "rb") as f:
    private_key = load_pem_private_key(
        f.read(),
        password=None
    )


@app.route("/flow", methods=["POST"])
def flow():
    try:

        body = request.json

        print("===== REQUEST RECEIVED =====")
        print(body)

        encrypted_flow_data = base64.b64decode(
            body["encrypted_flow_data"]
        )

        encrypted_aes_key = base64.b64decode(
            body["encrypted_aes_key"]
        )

        iv = base64.b64decode(
            body["initial_vector"]
        )

        print("encrypted_flow_data length =", len(encrypted_flow_data))
        print("encrypted_aes_key length =", len(encrypted_aes_key))
        print("iv length =", len(iv))

        # Decrypt AES key using RSA private key
        aes_key = private_key.decrypt(
            encrypted_aes_key,
            padding.OAEP(
                mgf=padding.MGF1(
                    algorithm=hashes.SHA256()
                ),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        print("AES KEY LENGTH =", len(aes_key))

        # Split ciphertext and tag
        ciphertext = encrypted_flow_data[:-16]
        tag = encrypted_flow_data[-16:]

        print("CIPHERTEXT LENGTH =", len(ciphertext))
        print("TAG LENGTH =", len(tag))

        # Decrypt flow payload
        cipher = Cipher(
            algorithms.AES(aes_key),
            modes.GCM(iv, tag)
        )

        decryptor = cipher.decryptor()

        decrypted = (
            decryptor.update(ciphertext)
            + decryptor.finalize()
        )

        print("===== DECRYPTED DATA =====")
        print(decrypted.decode())

        flow_data = json.loads(
            decrypted.decode()
        )

        action = flow_data.get("action")

        print("ACTION =", action)

        # Health check ping
        if action == "ping":

            response_data = {
                "version": "3.0",
                "data": {
                    "status": "active"
                }
            }

        else:

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

        print("===== RESPONSE =====")
        print(response_json)

        # Encrypt response
        response_cipher = Cipher(
            algorithms.AES(aes_key),
            modes.GCM(iv)
        )

        encryptor = response_cipher.encryptor()

        encrypted_response = (
            encryptor.update(
                response_json.encode()
            )
            + encryptor.finalize()
        )

        encrypted_response += encryptor.tag

        response_base64 = base64.b64encode(
            encrypted_response
        ).decode()

        print("===== RESPONSE SENT =====")

        return response_base64, 200

    except Exception as e:

        print("===== ERROR =====")
        print(traceback.format_exc())

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/", methods=["GET"])
def health():
    return "OK", 200


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8080
    )
