import os
import uuid
from flask import Flask, request, jsonify, render_template, send_from_directory
import config
import detect
import verify_claude
import notify

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = config.MAX_UPLOAD_MB * 1024 * 1024


def allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in config.ALLOWED_EXTENSIONS


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/uploads/<path:name>")
def uploads(name):
    return send_from_directory(config.UPLOAD_DIR, name)


@app.route("/analyze", methods=["POST"])
def analyze():
    file = request.files.get("image")
    if file is None or file.filename == "":
        return jsonify({"error": "No image uploaded"}), 400
    if not allowed(file.filename):
        return jsonify({"error": "Only jpg, jpeg, png allowed"}), 400

    ext = file.filename.rsplit(".", 1)[1].lower()
    name = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(config.UPLOAD_DIR, name)
    file.save(path)

    try:
        result = detect.detect(path)
    except Exception as e:
        return jsonify({"error": f"Detection failed: {type(e).__name__}"}), 500

    verdict = verify_claude.verify(path, result["detections"])

    alerts = []
    if notify.should_alert(result["counts"]):
        alerts = notify.notify_all(result["counts"], verdict, result["annotated_path"])

    return jsonify({
        "counts": result["counts"],
        "detections": result["detections"],
        "claude": verdict,
        "alerts": alerts,
        "annotated_url": "/uploads/" + os.path.basename(result["annotated_path"]),
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
