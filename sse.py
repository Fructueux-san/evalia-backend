from flask import Flask, request, jsonify
from flask_sse import sse
from confs.caching import url_string_sse
from flask_cors import CORS


app = Flask(__name__)
CORS(app, resources={r"*": {"origins": "*"}})

app.config["REDIS_URL"] = url_string_sse
app.register_blueprint(sse, url_prefix="/stream")


@app.post("/notify")
def notify():
    user = request.args.get("user")
    msg_type = request.args.get("type")
    data = request.get_json()

    try:
        sse.publish(data, type=msg_type, channel=f"user:{user}")
        return jsonify(message="Evènement publié avec succès"), 200
    except Exception as e:
        return jsonify(message="Impossible de publier sur le canal de cet utilisateur", error=f"{e}"), 500


if __name__ == "__main__":
    app.run(port=8001, host="0.0.0.0", debug=True)


