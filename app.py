import os
import uuid
from functools import wraps
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect, url_for, session,
    flash, jsonify, send_from_directory
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from database import get_db_connection, create_tables
import boto3

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "roadwatch-secret-key-production-ready-2026")

# AWS S3 configuration. Boto3 automatically uses the EC2 instance IAM role.
AWS_REGION = os.environ.get("AWS_REGION", "ap-southeast-2")
S3_BUCKET = os.environ.get("S3_BUCKET")
s3_client = boto3.client("s3", region_name=AWS_REGION) if S3_BUCKET else None
# AWS SNS Configuration
SNS_TOPIC_ARN = os.environ.get(
    "SNS_TOPIC_ARN",
    "arn:aws:sns:ap-southeast-2:304019241867:RoadWatch-Alerts"
)

sns_client = boto3.client(
    "sns",
    region_name=AWS_REGION
)
# File upload configuration
UPLOAD_FOLDER = os.path.join(app.root_path, "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize database schema and migrations
create_tables()


# -------------------------------------------------------------
# Helper Functions & Role-Based Access Control Decorators
# -------------------------------------------------------------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def validate_coordinates(lat, lng):
    """Safely validate latitude and longitude. Returns (float, float) or (None, None)."""
    if lat is None or lng is None:
        return None, None
    lat_str = str(lat).strip()
    lng_str = str(lng).strip()
    if not lat_str or not lng_str:
        return None, None
    try:
        lat_f = float(lat_str)
        lng_f = float(lng_str)
        if -90.0 <= lat_f <= 90.0 and -180.0 <= lng_f <= 180.0:
            return round(lat_f, 6), round(lng_f, 6)
        return None, None
    except (ValueError, TypeError):
        return None, None


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please sign in to access this page.", "error")
            return redirect(url_for("login_page", next=request.path))
        return f(*args, **kwargs)
    return decorated_function


def citizen_required(f):
    """
    Enforces that ONLY citizens can access complaint submission.
    Admins are strictly blocked on the backend from seeing the form or submitting reports.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get("user_id")
        user_role = session.get("user_role")

        if not user_id:
            flash("Please sign in or register as a citizen to submit a road damage complaint.", "info")
            return redirect(url_for("login_page", next=request.path))

        if user_role == "admin":
            flash("Administrators are not permitted to submit complaints. Complaint submission is reserved exclusively for citizens.", "error")
            return redirect(url_for("admin_dashboard"))

        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please sign in as an administrator to access the portal.", "error")
            return redirect(url_for("login_page", next=request.path))
        if session.get("user_role") != "admin":
            flash("Access denied. Administrator privileges required.", "error")
            return redirect(url_for("home"))
        return f(*args, **kwargs)
    return decorated_function


# -------------------------------------------------------------
# Public & Citizen Routes
# -------------------------------------------------------------
@app.route("/")
def home():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS total FROM complaints")
    total = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS pending FROM complaints WHERE status = 'Pending'")
    pending = cursor.fetchone()["pending"]

    cursor.execute("SELECT COUNT(*) AS in_progress FROM complaints WHERE status = 'In Progress'")
    in_progress = cursor.fetchone()["in_progress"]

    cursor.execute("SELECT COUNT(*) AS resolved FROM complaints WHERE status = 'Resolved'")
    resolved = cursor.fetchone()["resolved"]

    cursor.execute("""
        SELECT id, damage_type, location, description, status, priority, latitude, longitude, is_demo, created_at
        FROM complaints
        ORDER BY id DESC
        LIMIT 4
    """)
    recent_reports = cursor.fetchall()
    conn.close()

    stats = {
        "total": total,
        "pending": pending,
        "in_progress": in_progress,
        "resolved": resolved
    }
    return render_template("home.html", stats=stats, recent_reports=recent_reports)


@app.route("/register", methods=["GET", "POST"])
def register_page():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("All fields are required.", "error")
            return render_template("register.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template("register.html")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        existing = cursor.fetchone()

        if existing:
            conn.close()
            flash("An account with that email already exists. Please log in.", "error")
            return redirect(url_for("login_page"))

        hashed_password = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, 'citizen')",
            (name, email, hashed_password)
        )
        conn.commit()
        conn.close()

        flash("Account created successfully! You can now sign in.", "success")
        return redirect(url_for("login_page"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, email, password, role FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["user_role"] = user["role"]
            flash(f"Welcome back, {user['name']}!", "success")

            next_url = request.args.get("next")
            if next_url and next_url.startswith("/") and not (user["role"] == "admin" and next_url == "/report"):
                return redirect(next_url)
            if user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("my_reports"))
        else:
            flash("Invalid email or password. Please try again.", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("home"))


@app.route("/report", methods=["GET", "POST"])
@citizen_required
def report():
    """
    Complaint submission endpoint.
    Strictly restricted to citizens via @citizen_required.
    Admins are blocked and redirected to the admin portal.
    """
    if request.method == "POST":
        damage_type = request.form.get("damage_type", "").strip()
        location = request.form.get("location", "").strip()
        description = request.form.get("description", "").strip()
        priority = request.form.get("priority", "Medium").strip()
        raw_lat = request.form.get("latitude")
        raw_lng = request.form.get("longitude")

        if not damage_type or not location:
            flash("Please provide both the damage category and location description.", "error")
            return redirect(url_for("report"))

        # Backend coordinate validation
        lat, lng = validate_coordinates(raw_lat, raw_lng)

        # Upload new complaint images directly to private AWS S3.
        # Existing image_key values remain compatible with the /uploads route below.
        image_key = None
        if "image" in request.files:
            file = request.files["image"]

            if file and file.filename != "":
                if not allowed_file(file.filename):
                    flash("Unsupported image format. Please upload PNG, JPG, JPEG, or WEBP.", "error")
                    return redirect(url_for("report"))

                if not S3_BUCKET or s3_client is None:
                    app.logger.error("S3_BUCKET is not configured.")
                    flash("Image storage is not configured. Please contact the administrator.", "error")
                    return redirect(url_for("report"))

                safe_name = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4().hex[:10]}_{safe_name}"

                try:
                    s3_client.upload_fileobj(
                        file,
                        S3_BUCKET,
                        unique_filename,
                        ExtraArgs={"ContentType": file.mimetype or "application/octet-stream"}
                    )
                    image_key = unique_filename
                except Exception:
                    app.logger.exception("S3 complaint image upload failed")
                    flash("Image upload failed. Please try again.", "error")
                    return redirect(url_for("report"))

        user_id = session.get("user_id")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO complaints (user_id, damage_type, location, description, image_key, status, priority, latitude, longitude, is_demo)
            VALUES (?, ?, ?, ?, ?, 'Pending', ?, ?, ?, 0)
        """, (user_id, damage_type, location, description, image_key, priority, lat, lng))

        conn.commit()

        # Get the newly generated complaint ID
        complaint_id = cursor.lastrowid

        # Close database connection
        conn.close()

        # Send SNS email notification
        try:
            message = (
                f"A new road damage complaint has been submitted.\n\n"
                f"Complaint ID: RW-{complaint_id}\n"
                f"Category: {damage_type}\n"
                f"Location: {location}\n"
                f"Priority: {priority}\n"
                f"Description: {description or 'Not provided'}\n"
                f"Status: Pending\n"
            )

            sns_client.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject=f"New RoadWatch Complaint - RW-{complaint_id}",
                Message=message
            )

            app.logger.info(
                "SNS notification sent for RW-%s", complaint_id
            )

        except Exception:
            app.logger.exception(
                "SNS notification failed for RW-%s", complaint_id
            )


        except Exception:
            app.logger.exception("SNS notification failed for RW-%s", complaint_id)
        flash(f"Road damage report #RW-{complaint_id} submitted successfully! Municipal dispatch has been notified.", "success")
        return redirect(url_for("map_page", lat=lat, lng=lng, zoom=16) if lat and lng else url_for("map_page"))

    return render_template("report.html")


@app.route("/map")
def map_page():
    return render_template("map.html")


@app.route("/my-reports")
@login_required
def my_reports():
    user_id = session["user_id"]
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, damage_type, location, description, image_key, status, priority, latitude, longitude, is_demo, created_at
        FROM complaints
        WHERE user_id = ?
        ORDER BY id DESC
    """, (user_id,))
    complaints = cursor.fetchall()
    conn.close()
    return render_template("my_reports.html", complaints=complaints)


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    # Continue serving legacy images that were saved on the EC2 filesystem.
    local_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if os.path.isfile(local_path):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    # New images are private S3 objects; return a short-lived presigned URL.
    if not S3_BUCKET or s3_client is None:
        return "Image unavailable", 404

    try:
        image_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": filename},
            ExpiresIn=3600
        )
        return redirect(image_url)
    except Exception:
        app.logger.exception("Unable to generate S3 image URL")
        return "Image unavailable", 404


# -------------------------------------------------------------
# Admin Management & Analytics Routes
# -------------------------------------------------------------
@app.route("/admin")
@admin_required
def admin_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS total FROM complaints")
    total = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS pending FROM complaints WHERE status = 'Pending'")
    pending = cursor.fetchone()["pending"]

    cursor.execute("SELECT COUNT(*) AS in_progress FROM complaints WHERE status = 'In Progress'")
    in_progress = cursor.fetchone()["in_progress"]

    cursor.execute("SELECT COUNT(*) AS resolved FROM complaints WHERE status = 'Resolved'")
    resolved = cursor.fetchone()["resolved"]

    cursor.execute("SELECT COUNT(*) AS high_priority FROM complaints WHERE priority = 'High'")
    high_priority = cursor.fetchone()["high_priority"]

    # Filter and Search Support for Admin
    search_query = request.args.get("search", "").strip()
    filter_status = request.args.get("status", "ALL").strip()
    filter_priority = request.args.get("priority", "ALL").strip()
    filter_origin = request.args.get("origin", "ALL").strip()

    where_clauses = ["1=1"]
    params = []

    if search_query:
        where_clauses.append("(location LIKE ? OR description LIKE ? OR damage_type LIKE ? OR CAST(id AS TEXT) LIKE ?)")
        wildcard = f"%{search_query}%"
        params.extend([wildcard, wildcard, wildcard, wildcard])

    if filter_status and filter_status != "ALL":
        where_clauses.append("status = ?")
        params.append(filter_status)

    if filter_priority and filter_priority != "ALL":
        where_clauses.append("priority = ?")
        params.append(filter_priority)

    if filter_origin == "citizen":
        where_clauses.append("is_demo = 0")
    elif filter_origin == "demo":
        where_clauses.append("is_demo = 1")

    query = f"""
        SELECT id, user_id, damage_type, location, description, image_key, status, priority, latitude, longitude, is_demo, created_at
        FROM complaints
        WHERE {" AND ".join(where_clauses)}
        ORDER BY id DESC
    """
    cursor.execute(query, params)
    complaints = cursor.fetchall()
    conn.close()

    stats = {
        "total": total,
        "pending": pending,
        "in_progress": in_progress,
        "resolved": resolved,
        "high_priority": high_priority
    }
    return render_template(
        "admin_dashboard.html",
        complaints=complaints,
        stats=stats,
        search_query=search_query,
        filter_status=filter_status,
        filter_priority=filter_priority,
        filter_origin=filter_origin
    )


@app.route("/admin/complaint/<int:complaint_id>/status", methods=["POST"])
@admin_required
def update_complaint_status(complaint_id):
    new_status = request.form.get("status")
    if new_status in ["Pending", "In Progress", "Resolved"]:
        conn = get_db_connection()
        conn.execute("UPDATE complaints SET status = ? WHERE id = ?", (new_status, complaint_id))
        conn.commit()
        conn.close()
        flash(f"Complaint #RW-{complaint_id} status updated to '{new_status}'.", "success")
    else:
        flash("Invalid status specified.", "error")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/analytics")
@admin_required
def analytics_dashboard():
    return render_template("analytics.html")


# -------------------------------------------------------------
# JSON APIs (Public Map & Admin Analytics)
# -------------------------------------------------------------
@app.route("/api/complaints")
def api_complaints():
    """Returns verified complaints with coordinates. Excludes private user PII."""
    status = request.args.get("status")
    category = request.args.get("category")
    priority = request.args.get("priority")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    query = """
        SELECT id, damage_type, location, description, image_key, status, priority, latitude, longitude, is_demo, created_at
        FROM complaints
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
    """
    params = []

    if status and status != "ALL":
        query += " AND status = ?"
        params.append(status)

    if category and category != "ALL":
        query += " AND damage_type = ?"
        params.append(category)

    if priority and priority != "ALL":
        query += " AND priority = ?"
        params.append(priority)

    if start_date:
        query += " AND created_at >= ?"
        params.append(f"{start_date} 00:00:00")

    if end_date:
        query += " AND created_at <= ?"
        params.append(f"{end_date} 23:59:59")

    query += " ORDER BY id DESC"

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    result = []
    for row in rows:
        image_url = url_for("uploaded_file", filename=row["image_key"]) if row["image_key"] else None
        result.append({
            "id": row["id"],
            "damage_type": row["damage_type"],
            "location": row["location"],
            "description": row["description"],
            "image_url": image_url,
            "status": row["status"],
            "priority": row["priority"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "is_demo": bool(row["is_demo"]),
            "created_at": str(row["created_at"]) if row["created_at"] else ""
        })

    return jsonify(result)


@app.route("/api/admin/analytics")
@admin_required
def api_admin_analytics():
    """Dynamic analytics statistics and Chart.js datasets calculated directly from database."""
    status = request.args.get("status")
    category = request.args.get("category")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    where_clauses = ["1=1"]
    params = []

    if status and status != "ALL":
        where_clauses.append("status = ?")
        params.append(status)

    if category and category != "ALL":
        where_clauses.append("damage_type = ?")
        params.append(category)

    if start_date:
        where_clauses.append("created_at >= ?")
        params.append(f"{start_date} 00:00:00")

    if end_date:
        where_clauses.append("created_at <= ?")
        params.append(f"{end_date} 23:59:59")

    where_sql = " AND ".join(where_clauses)

    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Summary Metrics
    cursor.execute(f"SELECT COUNT(*) AS total FROM complaints WHERE {where_sql}", params)
    total = cursor.fetchone()["total"]

    cursor.execute(f"SELECT COUNT(*) AS pending FROM complaints WHERE status = 'Pending' AND {where_sql}", params)
    pending = cursor.fetchone()["pending"]

    cursor.execute(f"SELECT COUNT(*) AS in_progress FROM complaints WHERE status = 'In Progress' AND {where_sql}", params)
    in_progress = cursor.fetchone()["in_progress"]

    cursor.execute(f"SELECT COUNT(*) AS resolved FROM complaints WHERE status = 'Resolved' AND {where_sql}", params)
    resolved = cursor.fetchone()["resolved"]

    cursor.execute(f"SELECT COUNT(*) AS high_priority FROM complaints WHERE priority = 'High' AND {where_sql}", params)
    high_priority = cursor.fetchone()["high_priority"]

    # 2. Complaints by Status
    cursor.execute(f"""
        SELECT status, COUNT(*) AS count
        FROM complaints
        WHERE {where_sql}
        GROUP BY status
        ORDER BY count DESC
    """, params)
    status_rows = cursor.fetchall()
    status_labels = [r["status"] for r in status_rows]
    status_counts = [r["count"] for r in status_rows]

    # Ensure all 3 statuses are represented if empty
    if not status_labels:
        status_labels = ["Pending", "In Progress", "Resolved"]
        status_counts = [0, 0, 0]

    # 3. Complaints by Category
    cursor.execute(f"""
        SELECT damage_type, COUNT(*) AS count
        FROM complaints
        WHERE {where_sql}
        GROUP BY damage_type
        ORDER BY count DESC
    """, params)
    category_rows = cursor.fetchall()
    category_labels = [r["damage_type"] for r in category_rows]
    category_counts = [r["count"] for r in category_rows]

    # 4. Monthly Complaint Trends (chronological)
    cursor.execute(f"""
        SELECT strftime('%Y-%m', created_at) AS month_year, COUNT(*) AS count
        FROM complaints
        WHERE {where_sql}
        GROUP BY month_year
        ORDER BY month_year ASC
    """, params)
    trend_rows = cursor.fetchall()

    def format_month(ym):
        if not ym:
            return ""
        try:
            dt = datetime.strptime(ym, "%Y-%m")
            return dt.strftime("%b %Y")
        except ValueError:
            return ym

    trend_labels = [format_month(r["month_year"]) for r in trend_rows]
    trend_counts = [r["count"] for r in trend_rows]

    # 5. Resolved vs Pending
    cursor.execute(f"""
        SELECT 
            strftime('%Y-%m', created_at) AS month_year,
            SUM(CASE WHEN status = 'Resolved' THEN 1 ELSE 0 END) AS resolved_count,
            SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) AS pending_count
        FROM complaints
        WHERE {where_sql}
        GROUP BY month_year
        ORDER BY month_year ASC
    """, params)
    comp_rows = cursor.fetchall()

    comp_labels = [format_month(r["month_year"]) for r in comp_rows]
    comp_resolved = [r["resolved_count"] or 0 for r in comp_rows]
    comp_pending = [r["pending_count"] or 0 for r in comp_rows]

    conn.close()

    return jsonify({
        "summary": {
            "total": total,
            "pending": pending,
            "in_progress": in_progress,
            "resolved": resolved,
            "high_priority": high_priority
        },
        "by_status": {
            "labels": status_labels,
            "data": status_counts
        },
        "by_category": {
            "labels": category_labels,
            "data": category_counts
        },
        "monthly_trends": {
            "labels": trend_labels,
            "data": trend_counts
        },
        "resolved_vs_pending": {
            "labels": comp_labels,
            "resolved": comp_resolved,
            "pending": comp_pending
        }
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
