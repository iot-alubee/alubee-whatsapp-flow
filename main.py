from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/flow", methods=["POST"])
def flow():

    print(request.json)

    return jsonify({
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
    })

@app.route("/", methods=["GET"])
def health():
    return "OK"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)