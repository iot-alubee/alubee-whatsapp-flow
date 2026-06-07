from flask import Flask, request, jsonify
import base64
import json
import traceback

from cryptography.hazmat.primitives import hashes, serialization
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

# Print public key on startup
public_key = private_key.public_key()

pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)

print("===== PUBLIC KEY =====")
print(pem.decode())


@app.route("/flow", methods=["POST"])
def flow():

    try:

        body = request.json

        print("\n===== REQUEST RECEIVED =====")
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

        aes_key = None

        # Try OAEP SHA256
        try:

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

            print("RSA OAEP SHA256 SUCCESS")

        except Exception:

            print("RSA OAEP SHA256 FAILED")

            # Try OAEP SHA1
            aes_key = private_key.decrypt(
                encrypted_aes_key,
                padding.OAEP(
                    mgf=padding.MGF1(
                        algorithm=hashes.SHA1()
                    ),
                    algorithm=hashes.SHA1(),
                    label=None
                )
            )

            print("RSA OAEP SHA1 SUCCESS")

        print("AES KEY LENGTH =", len(aes_key))

        # Split ciphertext and GCM tag
        ciphertext = encrypted_flow_data[:-16]
        tag = encrypted_flow_data[-16:]

        print("Ciphertext Length =", len(ciphertext))
        print("Tag Length =", len(tag))

        cipher = Cipher(
            algorithms.AES(aes_key),
            modes.GCM(iv, tag)
        )

        decryptor = cipher.decryptor()

        decrypted_data = (
            decryptor.update(ciphertext)
            + decryptor.finalize()
        )

        decrypted_text = decrypted_data.decode("utf-8")

        print("\n===== DECRYPTED DATA =====")
        print(decrypted_text)

        flow_data = json.loads(
            decrypted_text
        )

        print("FLOW DATA =", flow_data)

        action = flow_data.get("action")

        #
        # HEALTH CHECK
        #
        if action == "ping":

            response_data = {
                "data": {
                    "status": "active"
                }
            }

        #
        # SAMPLE DATA RESPONSE
        #
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

        print("\n===== RESPONSE JSON =====")
        print(response_json)

        #
        # IMPORTANT:
        # Meta expects the response to be encrypted
        # with the bitwise inverted IV.
        #
        response_iv = bytes(
            [b ^ 0xFF for b in iv]
        )

        print("===== RESPONSE IV =====")
        print(
            base64.b64encode(
                response_iv
            ).decode()
        )

        response_cipher = Cipher(
            algorithms.AES(aes_key),
            modes.GCM(response_iv)
        )

        encryptor = response_cipher.encryptor()

        encrypted_response = (
            encryptor.update(
                response_json.encode("utf-8")
            )
            + encryptor.finalize()
        )

        encrypted_response += encryptor.tag

        response_base64 = base64.b64encode(
            encrypted_response
        ).decode()

        print("===== RESPONSE SENT =====")

        return (
            response_base64,
            200,
            {
                "Content-Type": "text/plain"
            }
        )

    except Exception:

        print("\n===== ERROR =====")
        print(traceback.format_exc())

        return jsonify(
            {
                "success": False,
                "error": traceback.format_exc()
            }
        ), 500


@app.route("/", methods=["GET"])
def health():

    return "OK", 200


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=8080
    )
