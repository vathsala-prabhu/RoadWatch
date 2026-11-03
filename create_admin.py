from getpass import getpass
from werkzeug.security import generate_password_hash
from database import create_tables, get_db_connection

create_tables()
print("Create the RoadWatch administrator account")
name = input("Admin name: ").strip()
email = input("Admin email: ").strip().lower()
password = getpass("Admin password (at least 8 characters): ")

if not name or not email or len(password) < 8:
    raise SystemExit("Name/email are required and password must be at least 8 characters.")

conn = get_db_connection()
try:
    conn.execute(
        "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, 'admin')",
        (name, email, generate_password_hash(password))
    )
    conn.commit()
    print("Admin account created. You can now log in.")
except Exception as exc:
    conn.rollback()
    print(f"Could not create admin: {exc}")
finally:
    conn.close()
