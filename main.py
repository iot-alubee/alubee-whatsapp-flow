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

# Print corresponding public key on startup
public_key = private_key.public_key()
pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)

print("===== PUBLIC KEY FROM PRIVATE.PEM =====")
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

        # Try OAEP SHA256 first
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

        except Exception as e:

            print("RSA OAEP SHA256 FAILED")
            print(str(e))

            try:

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

            except Exception as e2:

                print("RSA OAEP SHA1 FAILED")
                print(str(e2))

                return jsonify({
                    "success": False,
                    "error": "Unable to decrypt AES key. Private key does not match Meta public key."
                }), 500

        print("AES KEY LENGTH =", len(aes_key))

        # Split GCM tag
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

        print("\n===== DECRYPTED DATA =====")
        print(decrypted_data.decode())

        flow_data = json.loads(
            decrypted_data.decode()
        )

        action = flow_data.get("action")

        print("ACTION =", action)

        # WhatsApp health check
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

        print("\n===== RESPONSE JSON =====")
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

        print("Response encrypted successfully")

        return response_base64, 200

    except Exception:

        print("\n===== ERROR =====")
        print(traceback.format_exc())

        return jsonify({
            "success": False,
            "error": traceback.format_exc()
        }), 500


@app.route("/", methods=["GET"])
def health():
    return "OK", 200


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8080
    )
