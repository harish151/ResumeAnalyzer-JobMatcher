from flask import Flask, request, jsonify
from flask_cors import CORS
from resume_parser import parse_resume
import os
import datetime
import functools
import pymysql
import jwt
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

SECRET_KEY = os.getenv("SECRET_KEY", "super_secret_jwt_key")

# Database Connection Helper
def get_db_connection():
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST"),
        port=int(os.getenv("MYSQL_PORT", 26780)),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DB"),
        ssl={"ssl": True},  # Required for Aiven SSL connection
        cursorclass=pymysql.cursors.DictCursor
    )

# Table Initialization Helper
def init_db():
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) NOT NULL UNIQUE,
                    password VARCHAR(255) NOT NULL,
                    role ENUM('user', 'recruiter', 'admin') NOT NULL DEFAULT 'user',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
        conn.commit()
        conn.close()
        print("✅ Database initialized successfully.")
    except Exception as e:
        print("❌ Database connection error:", e)

init_db()

# JWT Authentication Middleware / Decorator
def token_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get("Authorization")

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

        if not token:
            return jsonify({"error": "Access token required"}), 401

        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            current_user = data
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired"}), 403
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 403

        return f(current_user, *args, **kwargs)

    return decorated



UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Resume Parser API is running"
    })

# REGISTER ENDPOINT
@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "user")

    if not name or not email or not password:
        return jsonify({"error": "Please provide all required fields."}), 400

    if role not in ["user", "recruiter", "admin"]:
        role = "user"

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Check if email exists
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                return jsonify({"error": "Email is already registered."}), 400

            # Hash password and insert user
            hashed_pw = generate_password_hash(password)
            cursor.execute(
                "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
                (name, email, hashed_pw, role)
            )
            conn.commit()
            user_id = cursor.lastrowid

        # Generate Token
        payload = {
            "id": user_id,
            "name": name,
            "email": email,
            "role": role,
            "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

        return jsonify({
            "message": "User registered successfully",
            "token": token,
            "user": {"id": user_id, "name": name, "email": email, "role": role}
        }), 201

    except Exception as e:
        print("Registration Error:", e)
        return jsonify({"error": "Internal server error"}), 500
    finally:
        conn.close()

# LOGIN ENDPOINT
@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Please provide email and password."}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()

            if not user or not check_password_hash(user["password"], password):
                return jsonify({"error": "Invalid email or password."}), 400

            # Generate Token
            payload = {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "role": user["role"],
                "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)
            }
            token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

            return jsonify({
                "message": "Login successful",
                "token": token,
                "user": {
                    "id": user["id"],
                    "name": user["name"],
                    "email": user["email"],
                    "role": user["role"]
                }
            }), 200

    except Exception as e:
        print("Login Error:", e)
        return jsonify({"error": "Internal server error"}), 500
    finally:
        conn.close()

# CURRENT USER ENDPOINT
@app.route("/api/auth/me", methods=["GET"])
@token_required
def get_current_user(current_user):
    return jsonify({
        "user": {
            "id": current_user["id"],
            "name": current_user["name"],
            "email": current_user["email"],
            "role": current_user["role"]
        }
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