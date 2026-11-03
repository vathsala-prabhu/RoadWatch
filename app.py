import os
import uuid
from functools import wraps
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv
from flask import (
    Flask, flash, redirect, render_template, request, session, url_for, abort
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from database import create_tables, get_db_connection

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-this-development-secret")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
create_tables()


def current_user():
    if "user_id" not in session:
        return None
    conn = get_db_connection()
    user = conn.execute(
        "SELECT id, name, email, role FROM users WHERE id = ?",
        (session["user_id"],)
    ).fetchone()
    conn.close()
    return user


@app.context_processor
def inject_user():
    return {"current_user": current_user()}


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        if user["role"] != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_image(file):
    """Upload to S3 when configured; otherwise save locally for development."""
    if not file or not file.filename:
        return None

    if not allowed_file(file.filename):
        raise ValueError("Use a JPG, JPEG, PNG or WEBP image.")

    original = secure_filename(file.filename)
    extension = original.rsplit(".", 1)[1].lower()
    object_name = f"complaints/{uuid.uuid4().hex}.{extension}"

    bucket = os.getenv("S3_BUCKET")
    if bucket:
        s3 = boto3.client("s3", region_name=os.getenv("AWS_REGION"))
        try:
            s3.upload_fileobj(
                file,
                bucket,
                object_name,
                ExtraArgs={"ContentType": file.mimetype or "application/octet-stream"}
            )
            return f"s3:{object_name}"
        except (BotoCoreError, ClientError) as exc:
            app.logger.exception("S3 upload failed")
            raise RuntimeError("Image upload to cloud storage failed. Please try again.") from exc

    local_name = f"{uuid.uuid4().hex}.{extension}"
    file.save(UPLOAD_DIR / local_name)
    return f"local:{local_name}"


def image_url(image_key):
    if not image_key:
        return None
    if image_key.startswith("local:"):
        return url_for("uploaded_file", filename=image_key.split(":", 1)[1])
    if image_key.startswith("s3:"):
        bucket = os.getenv("S3_BUCKET")
        if not bucket:
            return None
        s3 = boto3.client("s3", region_name=os.getenv("AWS_REGION"))
        try:
            return s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": image_key.split(":", 1)[1]},
                ExpiresIn=900
            )
        except (BotoCoreError, ClientError):
            app.logger.exception("Could not generate S3 image URL")
    return None


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or len(password) < 8:
            flash("Enter your name, a valid email and a password of at least 8 characters.", "error")
            return render_template("register.html")

        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, 'citizen')",
                (name, email, generate_password_hash(password))
            )
            conn.commit()
        except Exception:
            conn.rollback()
            flash("That email may already be registered. Try logging in.", "error")
            return render_template("register.html")
        finally:
            conn.close()

        flash("Account created successfully. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if not user or not check_password_hash(user["password_hash"], password):
            flash("Incorrect email or password.", "error")
            return render_template("login.html")

        session.clear()
        session["user_id"] = user["id"]
        flash(f"Welcome back, {user['name']}!", "success")
        return redirect(url_for("admin_dashboard" if user["role"] == "admin" else "dashboard"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))


@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    conn = get_db_connection()
    complaints = conn.execute(
        "SELECT * FROM complaints WHERE user_id = ? ORDER BY created_at DESC",
        (user["id"],)
    ).fetchall()
    conn.close()
    items = [dict(row) for row in complaints]
    for item in items:
        item["image_url"] = image_url(item["image_key"])
    return render_template("dashboard.html", complaints=items)


@app.route("/report", methods=["GET", "POST"])
@login_required
def report():
    if request.method == "POST":
        damage_type = request.form.get("damage_type", "").strip()
        location = request.form.get("location", "").strip()
        description = request.form.get("description", "").strip()
        image = request.files.get("image")

        if not damage_type or not location or not description:
            flash("Please complete all required fields.", "error")
            return render_template("report.html")

        try:
            image_key = save_image(image) if image and image.filename else None
        except (ValueError, RuntimeError) as exc:
            flash(str(exc), "error")
            return render_template("report.html")

        user = current_user()
        conn = get_db_connection()
        conn.execute(
            """INSERT INTO complaints
               (user_id, damage_type, location, description, image_key)
               VALUES (?, ?, ?, ?, ?)""",
            (user["id"], damage_type, location, description, image_key)
        )
        conn.commit()
        conn.close()
        flash("Your road damage report has been submitted.", "success")
        return redirect(url_for("dashboard"))

    return render_template("report.html")


@app.route("/admin")
@admin_required
def admin_dashboard():
    conn = get_db_connection()
    complaints = conn.execute(
        """SELECT complaints.*, users.name AS citizen_name, users.email AS citizen_email
           FROM complaints JOIN users ON complaints.user_id = users.id
           ORDER BY complaints.created_at DESC"""
    ).fetchall()
    conn.close()

    items = [dict(row) for row in complaints]
    for item in items:
        item["image_url"] = image_url(item["image_key"])

    stats = {
        "total": len(items),
        "pending": sum(c["status"] == "Pending" for c in items),
        "progress": sum(c["status"] == "In Progress" for c in items),
        "resolved": sum(c["status"] == "Resolved" for c in items),
    }
    return render_template("admin.html", complaints=items, stats=stats)


@app.route("/admin/complaint/<int:complaint_id>/status", methods=["POST"])
@admin_required
def update_status(complaint_id):
    status = request.form.get("status")
    if status not in {"Pending", "In Progress", "Resolved"}:
        abort(400)
    conn = get_db_connection()
    result = conn.execute(
        "UPDATE complaints SET status = ? WHERE id = ?",
        (status, complaint_id)
    )
    conn.commit()
    conn.close()
    if result.rowcount == 0:
        abort(404)
    flash("Complaint status updated.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    from flask import send_from_directory
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.errorhandler(403)
def forbidden(_error):
    return render_template("error.html", code=403, message="You do not have permission to view this page."), 403


@app.errorhandler(404)
def not_found(_error):
    return render_template("error.html", code=404, message="The page you requested could not be found."), 404


@app.errorhandler(413)
def too_large(_error):
    flash("Image is too large. Maximum upload size is 5 MB.", "error")
    return redirect(request.referrer or url_for("report"))


if __name__ == "__main__":
    app.run(debug=True)
