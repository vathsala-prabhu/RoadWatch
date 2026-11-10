# RoadWatch – Cloud-Based Road Damage Reporting and Management System

RoadWatch is a modern, location-aware web platform designed to empower citizens to report road hazards (potholes, severe surface cracking, manhole collapses, road shoulder erosion) and provide municipal authorities with geospatial intelligence, real-time dispatch management, and density heatmaps centered around **Mysuru, Karnataka, India**.

---

## 🌟 Key Features & Role Separation

### 1. Citizen Role (Reporting & Tracking)
Citizens can:
* **Register & Sign In** with secure password hashing.
* **Submit Road Damage Complaints** (`/report`) with damage category, priority, description, and photo upload.
* **Pinpoint Location via Two Options**:
  * **Option 1 ("Use My Current Location")**: Automatic browser Geolocation with accuracy feedback and draggable map pin preview.
  * **Option 2 ("Select on Map")**: Interactive OpenStreetMap centered on Mysuru, Karnataka (`12.3051, 76.6551`) where clicking or dragging updates coordinates.
* **Support for Earlier Photos**: Non-mandatory GPS permission allows citizens to submit photos taken earlier and manually pinpoint the scene.
* **View & Track Complaints** (`/my-reports`) with real-time status badges (`Pending`, `In Progress`, `Resolved`).

### 2. Admin Role (Management & Analytics Only)
Admins are **strictly restricted to management** and cannot submit complaints:
* **Backend Role Enforcement**: `@citizen_required` blocks any administrator from accessing `GET /report` or submitting `POST /report`.
* **Clean Navigation**: The "Report Damage" / "+ Report New Damage" buttons are hidden from admin navigation bars and map views.
* **Complaint Management Portal** (`/admin`):
  * Search complaints by street, landmark, defect, or ID.
  * Filter complaints by workflow status (`Pending`, `In Progress`, `Resolved`), priority, and origin (`Citizen Report` vs. `Demo Data`).
  * Direct one-click status updater dropdown for real-time dispatch management.
* **Geospatial Analytics & Heatmap Dashboard** (`/admin/analytics`):
  * Real-time metrics: Total, Pending, In Progress, Resolved, and High-Priority counts.
  * 4 interactive Chart.js charts: Status Doughnut, Category Bar, Monthly Trends Line, and Resolved vs. Pending Comparison.
  * Synchronized hazard density heatmap layer (`Leaflet.heat`).

### 3. Mysuru, Karnataka Demonstration Data
All demonstration complaints have been placed in authentic locations across **Mysuru, Karnataka, India** (Map center: `12.3051, 76.6551`):
* **Vijayanagar**: 2nd Stage Water Tank & 4th Stage Ring Road
* **Kuvempunagar**: Vishwamanava Double Road & Anikethana Road
* **Jayalakshmipuram**: Kalidasa Road
* **Hebbal**: Industrial Area / Outer Ring Road (Infosys Gate)
* **Saraswathipuram**: 5th Main Fire Station & Kukkarahalli Lake approach
* **Bogadi**: 2nd Stage Gaddige Main Road
* **Hootagalli**: Industrial Area (Automotive Axles)
* **Bannimantap**: Torch Light Parade Ground / Highway Circle
* **Hunsur Road**: NH 275 near BM Hospital & Paduvarahalli Junction
* **Mysuru City Centre**: Sayyaji Rao Road, K.R. Circle, D. Devaraj Urs Road, Palace North Gate

*Note: Genuine citizen-submitted complaints (such as Koorgalli) are permanently preserved and marked with `Citizen Report`, clearly distinguished from `Demo Data`.*

---

## 🏗️ Technology Stack

* **Backend**: Python 3.13, Flask 3.1.3
* **Database**: SQLite3 (Local / Embedded)
* **Frontend**: HTML5, CSS3, JavaScript (ES6+)
* **Mapping**: Leaflet.js 1.9.4, OpenStreetMap, Leaflet.heat
* **Data Visualisation**: Chart.js 4.4.1
* **Image Storage**: Local filesystem (`uploads/`) with seamless AWS S3 compatibility (`boto3`)

---

## 🚀 Getting Started (Local Setup)

### 1. Activate Environment
```powershell
cd c:\Users\vaths\road-damage-system
.\venv\Scripts\Activate.ps1
```

### 2. Initialize and Seed Database
```powershell
python database.py
```
Applies safe migrations (`latitude`, `longitude`, `priority`, `is_demo`) and seeds Mysuru, Karnataka demonstration data.

### 3. Run the Application
```powershell
python app.py
```
Open **`http://127.0.0.1:5000`** in your browser.

---

## 🔑 Demo Accounts

| Role | Email | Password | Allowed Capabilities |
| :--- | :--- | :--- | :--- |
| **City Administrator** | `admin@roadwatch.org` | `Admin@123` | Full access to `/admin` & `/admin/analytics`, status updater, complaint search & filter. *Cannot submit complaints.* |
| **Citizen User** | `citizen@roadwatch.org` | `Citizen@123` | Public reporting (`/report`), photo upload, personal report tracking (`/my-reports`), `/map`. |

---

## 🧪 Automated Testing

Run the integration test suite:
```powershell
python -m unittest test_app.py
```
All 11 tests verify:
1. Public page rendering and live platform statistics.
2. Interactive map rendering and layer switching.
3. Demonstration complaints presence in Mysuru, Karnataka with valid bounding coordinates.
4. Genuine citizen complaints (e.g. Koorgalli) preserved with `is_demo = 0`.
5. Strict role separation: Admins cannot see report form, cannot submit reports, and have no report links in navigation.
6. Guest redirection to sign-in for report submissions.
7. Citizen reporting with GPS coordinates.
8. Citizen reporting without GPS (earlier photos support).
9. Admin search, keyword filtering, and origin filtering (`citizen` vs. `demo`).
10. Admin complaint status updating (`Pending` $\rightarrow$ `In Progress` $\rightarrow$ `Resolved`).
11. Admin analytics and heatmap API access.
