import sqlite3
import os
from werkzeug.security import generate_password_hash

DATABASE = os.environ.get("DATABASE_PATH", "road_damage.db")

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def migrate_db(conn):
    """Safely migrate the database schema without dropping existing tables or data."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(complaints)")
    columns = [row["name"] for row in cursor.fetchall()]

    if "latitude" not in columns:
        cursor.execute("ALTER TABLE complaints ADD COLUMN latitude REAL")
    if "longitude" not in columns:
        cursor.execute("ALTER TABLE complaints ADD COLUMN longitude REAL")
    if "priority" not in columns:
        cursor.execute("ALTER TABLE complaints ADD COLUMN priority TEXT DEFAULT 'Medium'")
    if "is_demo" not in columns:
        cursor.execute("ALTER TABLE complaints ADD COLUMN is_demo INTEGER DEFAULT 0")

def seed_initial_data(conn):
    """
    Populate or update realistic demonstration data in Mysuru, Karnataka, India.
    Preserves all genuine user-submitted complaints.
    """
    cursor = conn.cursor()

    # Provision or update demo citizen user (Ramesh Kumar, Mysuru)
    cursor.execute("SELECT id FROM users WHERE email = 'citizen@roadwatch.org'")
    citizen = cursor.fetchone()
    if not citizen:
        pass_hash = generate_password_hash("Citizen@123")
        cursor.execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
            ("Ramesh Kumar", "citizen@roadwatch.org", pass_hash, "citizen")
        )
        citizen_id = cursor.lastrowid
    else:
        citizen_id = citizen["id"]
        cursor.execute("UPDATE users SET name = 'Ramesh Kumar' WHERE id = ?", (citizen_id,))

    # Remove only legacy USA dummy data or old test runs (longitude < 0 or test strings),
    # while strictly keeping genuine user complaints (like Row 25 in Koorgalli, Mysuru)
    cursor.execute("""
        DELETE FROM complaints 
        WHERE (longitude IS NOT NULL AND longitude < 0) 
           OR location LIKE '%Market St%' 
           OR location LIKE '%Fell St%' 
           OR location LIKE '%Haight St%' 
           OR location LIKE '%Howard St%' 
           OR location LIKE '%Columbus%'
           OR location LIKE '%Stanyan%'
           OR location LIKE '%Embarcadero%'
           OR location LIKE '%Test Street%'
           OR location LIKE '%Alex Corner%'
    """)

    # Check if demonstration complaints in Mysuru already exist
    cursor.execute("SELECT COUNT(*) AS cnt FROM complaints WHERE is_demo = 1")
    demo_count = cursor.fetchone()["cnt"]

    if demo_count == 0:
        # Realistic Demonstration Complaints across Mysuru, Karnataka, India
        mysuru_demo_complaints = [
            # 1. Mysuru City Centre
            (citizen_id, "Pothole", "Sayyaji Rao Road, near K.R. Circle, Mysuru City Centre",
             "Asphalt cavitation near pedestrian crossing causing two-wheeler swerving during peak market hours.",
             None, "Pending", "High", 12.3086, 76.6533, 1, "2026-11-08 10:15:00"),

            (citizen_id, "Street Light / Signage Obstruction", "D. Devaraj Urs Road near Gandhi Square, Mysuru City Centre",
             "Damaged road median divider stone obstructing vehicular lane turning towards Gandhi Square.",
             None, "Resolved", "Low", 12.3060, 76.6490, 1, "2026-10-18 11:30:00"),

            (citizen_id, "Pothole", "Albert Victor Road, near Mysuru Palace North Gate, Mysuru",
             "Depressed pothole near palace heritage gate, water accumulation during monsoon rains.",
             None, "In Progress", "Medium", 12.3051, 76.6551, 1, "2026-11-06 14:20:00"),

            # 2. Jayalakshmipuram
            (citizen_id, "Pothole", "Kalidasa Road, Jayalakshmipuram near Premier Studio Junction, Mysuru",
             "Severe pothole near commercial cafe stretch, hazard for evening two-wheeler traffic.",
             None, "Pending", "High", 12.3215, 76.6285, 1, "2026-11-07 16:45:00"),

            # 3. Saraswathipuram
            (citizen_id, "Erosion / Edge Break", "Saraswathipuram 5th Main, near Fire Station & Kukkarahalli Lake approach, Mysuru",
             "Pavement edge crumbling into the unpaved mud shoulder near the bus stop.",
             None, "Pending", "High", 12.3015, 76.6322, 1, "2026-11-09 09:10:00"),

            # 4. Kuvempunagar
            (citizen_id, "Pothole", "Vishwamanava Double Road, near Kuvempunagar Complex, Mysuru",
             "Deep crater on the main double road in front of shopping complex causing traffic congestion.",
             None, "Pending", "High", 12.2858, 76.6264, 1, "2026-11-05 17:30:00"),

            (citizen_id, "Manhole / Drainage Issue", "Anikethana Road, Kuvempunagar near Navodaya Circle, Mysuru",
             "Sunken storm water drain chamber cover creating an abrupt bump for motorists.",
             None, "Resolved", "Medium", 12.2925, 76.6210, 1, "2026-10-22 13:15:00"),

            # 5. Vijayanagar
            (citizen_id, "Pothole", "Vijayanagar 2nd Stage, near Water Tank & High Tension Double Road, Mysuru",
             "Deep pothole expanding on double road near water tank junction, loose gravel scattering.",
             None, "In Progress", "High", 12.3392, 76.6025, 1, "2026-11-04 11:00:00"),

            (citizen_id, "Surface Cracking", "Vijayanagar 4th Stage, near Ring Road Junction, Mysuru",
             "Extensive alligator cracking on asphalt stretch following monsoon runoff.",
             None, "Pending", "Medium", 12.3485, 76.5940, 1, "2026-10-28 15:40:00"),

            # 6. Bogadi
            (citizen_id, "Pothole", "Bogadi 2nd Stage, Gaddige Main Road near Ring Road flyover, Mysuru",
             "Multiple interconnected potholes on Gaddige road, dangerous during rain puddles.",
             None, "Resolved", "Medium", 12.3028, 76.5985, 1, "2026-10-12 10:05:00"),

            # 7. Hebbal
            (citizen_id, "Rutting / Depression", "Hebbal Industrial Area, Outer Ring Road near Infosys Gate, Mysuru",
             "Heavy truck wheel ruts formed on the left carriage lane leading to hydroplaning risk.",
             None, "In Progress", "Medium", 12.3685, 76.6050, 1, "2026-10-29 08:50:00"),

            # 8. Hootagalli
            (citizen_id, "Surface Cracking", "Hootagalli Industrial Area, near Automotive Axles Junction, Mysuru",
             "Long longitudinal fissures along roadway due to heavy container vehicle movement.",
             None, "Pending", "Low", 12.3495, 76.5750, 1, "2026-11-01 12:25:00"),

            # 9. Bannimantap
            (citizen_id, "Manhole / Drainage Issue", "Bannimantap, near Torch Light Parade Ground & Highway Circle, Mysuru",
             "Protruding concrete manhole cover elevated above newly resurfaced asphalt layer.",
             None, "Resolved", "Medium", 12.3365, 76.6495, 1, "2026-09-28 16:15:00"),

            # 10. Hunsur Road
            (citizen_id, "Pothole", "Hunsur Road (NH 275), near BM Hospital & Paduvarahalli Junction, Mysuru",
             "Sharp-edged asphalt crater in middle lane of major highway artery towards Hunsur/Madikeri.",
             None, "In Progress", "High", 12.3190, 76.6190, 1, "2026-11-03 18:00:00")
        ]

        cursor.executemany("""
            INSERT INTO complaints (user_id, damage_type, location, description, image_key, status, priority, latitude, longitude, is_demo, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, mysuru_demo_complaints)

def create_tables():
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'citizen'
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            damage_type TEXT NOT NULL,
            location TEXT NOT NULL,
            description TEXT,
            image_key TEXT,
            status TEXT DEFAULT 'Pending',
            priority TEXT DEFAULT 'Medium',
            latitude REAL,
            longitude REAL,
            is_demo INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    migrate_db(conn)

    # Seed default admin user if no admin exists
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1")
    admin = cursor.fetchone()
    if not admin:
        admin_pass_hash = generate_password_hash("Admin@123")
        cursor.execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
            ("City Administrator", "admin@roadwatch.org", admin_pass_hash, "admin")
        )

    seed_initial_data(conn)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_tables()
    print("Database initialized, migrated, and updated with Mysuru, Karnataka demonstration data.")
