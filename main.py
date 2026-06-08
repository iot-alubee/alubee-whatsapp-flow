import logging
import os

from flask import Flask, request
from cryptography.hazmat.primitives import serialization

from flow_crypto import decrypt_request, encrypt_response, load_private_key
from od_flow_handler import build_od_flow_response

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

PRIVATE_KEY_PATH = (os.getenv("FLOW_PRIVATE_KEY_PATH") or "private.pem").strip()
private_key = load_private_key(PRIVATE_KEY_PATH)

public_key = private_key.public_key()
pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)
logger.info("Flow endpoint public key:\n%s", pem.decode())


@app.route("/flow", methods=["POST"])
def flow():
    try:
        body = request.json or {}
        logger.info("flow request keys=%s", list(body.keys()))

        flow_data, aes_key, iv = decrypt_request(body, private_key)
        logger.info(
            "flow action=%s screen=%s data_keys=%s",
            flow_data.get("action"),
            flow_data.get("screen"),
            list((flow_data.get("data") or {}).keys()),
        )

        response_data = build_od_flow_response(flow_data)
        encrypted = encrypt_response(response_data, aes_key, iv)
        return encrypted, 200, {"Content-Type": "text/plain"}

    except Exception:
        logger.exception("flow endpoint error")
        # Non-200 breaks the form UI ("Something went wrong"); log and return 500 for Meta retry.
        return "", 500


@app.route("/", methods=["GET"])
def health():
    return "OK", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
