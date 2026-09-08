from flask import Flask, request, jsonify
from flask_cors import CORS
from resume_parser import parse_resume
import os

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Resume Parser API is running"
    })


@app.route("/parse-resume", methods=["POST"])
def parse_resume_api():

    if "resume" not in request.files:
        return jsonify({
            "error": "No resume file provided"
        }), 400

    file = request.files["resume"]

    if file.filename == "":
        return jsonify({
            "error": "No file selected"
        }), 400

    allowed_extensions = ["pdf", "docx"]

    extension = file.filename.rsplit(".", 1)[-1].lower()

    if extension not in allowed_extensions:
        return jsonify({
            "error": "Only PDF and DOCX files are supported"
        }), 400

    file_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        file.filename
    )

    file.save(file_path)

    try:
        result = parse_resume(file_path)

        # Delete uploaded file after processing
        os.remove(file_path)

        return jsonify({
            "success": True,
            "data": result
        })

    except Exception as e:

        if os.path.exists(file_path):
            os.remove(file_path)

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )