# RoadWatch – Cloud-Based Road Damage Reporting and Management System

RoadWatch is a cloud-hosted, location-aware web platform designed to empower citizens to report road hazards such as potholes, severe surface cracking, manhole collapses, and road shoulder erosion.

The platform provides municipal authorities with geospatial intelligence, complaint management, real-time email notifications, and hazard-density visualisation, with demonstration data centred around **Mysuru, Karnataka, India**.

RoadWatch is deployed on **Amazon Web Services (AWS)**, using EC2 for application hosting, S3 for complaint image storage, SNS for email notifications, and CloudWatch for infrastructure monitoring.

---

## 🌟 Key Features & Role Separation

### 1. Citizen Role – Reporting & Tracking

Citizens can:

- **Register & Sign In** with securely hashed passwords.
- **Submit Road Damage Complaints** (`/report`) with damage category, priority, description, and photo upload.
- **Pinpoint Location via Two Options:**
  - **Option 1 – Use My Current Location:** Automatic browser Geolocation with accuracy feedback and draggable map pin preview.
  - **Option 2 – Select on Map:** Interactive OpenStreetMap centred on Mysuru, Karnataka (`12.3051, 76.6551`), where clicking or dragging updates coordinates.
- **Support for Earlier Photos:** GPS permission is optional, allowing citizens to upload previously captured photos and manually pinpoint the location.
- **View & Track Complaints** (`/my-reports`) with status indicators:
  - Pending
  - In Progress
  - Resolved
- **Cloud-Based Image Uploads:** Complaint photographs are uploaded to a private AWS S3 bucket.
- **Automated Email Notifications:** Every successful complaint submission triggers an AWS SNS email notification containing the complaint ID, category, location, priority, and description.

### 2. Admin Role – Management & Analytics Only

Admins are strictly restricted to complaint management and cannot submit complaints.

- **Backend Role Enforcement:** `@citizen_required` blocks administrators from accessing `GET /report` or submitting `POST /report`.
- **Clean Navigation:** Report Damage and Report New Damage buttons are hidden from administrator navigation bars and map views.
- **Complaint Management Portal** (`/admin`):
  - Search complaints by street, landmark, defect, or ID.
  - Filter complaints by workflow status, priority, and origin (Citizen Report vs. Demo Data).
  - Update complaint status using a dropdown.
  - Manage and monitor submitted complaints.
- **Geospatial Analytics & Heatmap Dashboard** (`/admin/analytics`):
  - Real-time metrics: Total, Pending, In Progress, Resolved, and High-Priority complaints.
  - Four interactive Chart.js visualisations:
    - Status Doughnut Chart
    - Category Bar Chart
    - Monthly Trends Line Chart
    - Resolved vs. Pending Comparison
  - Synchronized hazard-density heatmap using `Leaflet.heat`.

### 3. Mysuru, Karnataka Demonstration Data

Demonstration complaints are distributed across authentic locations in Mysuru, Karnataka, India.

Map centre: `12.3051, 76.6551`

- **Vijayanagar:** 2nd Stage Water Tank & 4th Stage Ring Road
- **Kuvempunagar:** Vishwamanava Double Road & Anikethana Road
- **Jayalakshmipuram:** Kalidasa Road
- **Hebbal:** Industrial Area / Outer Ring Road (Infosys Gate)
- **Saraswathipuram:** 5th Main Fire Station & Kukkarahalli Lake approach
- **Bogadi:** 2nd Stage Gaddige Main Road
- **Hootagalli:** Industrial Area (Automotive Axles)
- **Bannimantap:** Torch Light Parade Ground / Highway Circle
- **Hunsur Road:** NH 275 near BM Hospital & Paduvarahalli Junction
- **Mysuru City Centre:** Sayyaji Rao Road, K.R. Circle, D. Devaraj Urs Road, Palace North Gate

**Data Integrity:** Genuine citizen-submitted complaints, such as Koorgalli, are preserved and marked with `is_demo = 0`, clearly distinguishing them from demonstration records.

---

## ☁️ AWS Cloud Architecture

RoadWatch uses AWS services to provide cloud hosting, image storage, automated notifications, and infrastructure monitoring.

### 1. Amazon EC2 – Application Hosting

- Hosts the Flask-based RoadWatch application on an Ubuntu Linux server.
- Application runs using **Gunicorn** as the WSGI application server.
- **Nginx** acts as a reverse proxy, forwarding incoming HTTP requests to Gunicorn.
- The application is accessible through the EC2 public IP address.
- Systemd manages the application service and supports automatic service restarts.

### 2. Amazon S3 – Complaint Image Storage

- Complaint images are uploaded directly to an AWS S3 bucket using the Python `boto3` SDK.
- Images are stored in a private S3 bucket with public access blocked.
- Unique filenames are generated to avoid filename collisions.
- Image retrieval uses temporary, time-limited presigned URLs.
- Existing locally stored images remain compatible with the application's upload-serving route.

### 3. Amazon SNS – Automated Email Notifications

- An SNS topic named `RoadWatch-Alerts` handles application notifications.
- When a citizen successfully submits a complaint, Flask publishes a message to the SNS topic.
- SNS delivers an email to subscribed and confirmed email endpoints.
- Notifications include:
  - Complaint ID
  - Damage category
  - Location
  - Priority
  - Description
  - Complaint status
- SNS publishing is performed after the database transaction is committed, so notification failures do not prevent a complaint from being saved.

### 4. Amazon CloudWatch – Infrastructure Monitoring

- Monitors EC2 instance performance.
- Tracks CPU utilisation and other available EC2 metrics.
- Supports CloudWatch alarms for identifying high CPU utilisation.
- SNS can be configured as the alarm notification destination to send email alerts when configured thresholds are breached.

### 5. AWS IAM – Secure Access Management

- An IAM role named `RoadWatchEC2Role` is attached to the EC2 instance.
- The application uses the EC2 instance role through the AWS SDK credential provider chain.
- No AWS access keys need to be hardcoded in the application.
- The IAM policy grants the permissions required for:
  - S3 bucket listing and object operations.
  - SNS publishing to the `RoadWatch-Alerts` topic.
- Permissions are scoped to the required S3 bucket and SNS topic.

### Cloud Architecture Workflow

```text
             Citizen
                |
                v
        Nginx (HTTP :80)
                |
                v
       Gunicorn (Port 8000)
                |
                v
        Flask Application
                |
        +-------+-------+
        |       |       |
        v       v       v
      SQLite   AWS S3  AWS SNS
      Database  Images  Email Alerts
                |
                v
          Private Bucket

        AWS EC2 Instance
                |
                v
          AWS CloudWatch
          Metrics & Alarms
                |
                v
             AWS SNS
          Alarm Emails

        AWS IAM Role
        Secure AWS Access
```

---

## 🏗️ Technology Stack

| Layer | Technologies |
|---|---|
| Backend | Python, Flask 3.1.3 |
| Database | SQLite3 |
| Frontend | HTML5, CSS3, JavaScript (ES6+) |
| Mapping | Leaflet.js 1.9.4, OpenStreetMap, Leaflet.heat |
| Data Visualisation | Chart.js 4.4.1 |
| Cloud Hosting | Amazon EC2 (Ubuntu Linux) |
| Application Server | Gunicorn |
| Reverse Proxy | Nginx |
| Image Storage | Amazon S3, Boto3 |
| Email Notifications | Amazon SNS |
| Monitoring | Amazon CloudWatch |
| Access Management | AWS IAM |
| Version Control | Git & GitHub |

---

## 🚀 Deployment Architecture

RoadWatch is deployed on an AWS EC2 instance in the **Asia Pacific (Sydney) region (`ap-southeast-2`)**.

| Component | Configuration |
|---|---|
| Cloud Provider | Amazon Web Services |
| Compute Service | Amazon EC2 |
| Instance Type | `t3.micro` |
| Operating System | Ubuntu |
| AWS Region | `ap-southeast-2` |
| Web Server | Nginx |
| Application Server | Gunicorn |
| Internal Application Port | `8000` |
| Public HTTP Port | `80` |
| Database | SQLite3 |
| Image Storage | Private AWS S3 Bucket |
| Notification Service | AWS SNS |
| Monitoring Service | AWS CloudWatch |

### Deployment Flow

1. RoadWatch source code is maintained in GitHub.
2. The project is cloned onto the EC2 Ubuntu instance.
3. Python dependencies are installed in a virtual environment.
4. Environment variables are configured on the EC2 instance.
5. Gunicorn runs the Flask application.
6. Nginx forwards public HTTP requests to Gunicorn.
7. The EC2 IAM role provides secure access to AWS services.
8. Complaint images are stored in S3, and SNS handles notification delivery.

---

## ⚙️ Configuration

The application uses environment variables for configuration.

Example `.env` configuration:

```env
SECRET_KEY=your-secure-secret-key
AWS_REGION=ap-southeast-2
S3_BUCKET=your-s3-bucket-name
SNS_TOPIC_ARN=your-sns-topic-arn
```

**Security considerations:**

- Never commit `.env` files or AWS credentials to GitHub.
- Keep the S3 bucket private.
- Use IAM instance roles instead of hardcoded AWS access keys.
- Use a strong, secret Flask `SECRET_KEY`.
- Restrict IAM permissions to only the AWS resources required by the application.

---

## 🚀 Getting Started – Local Setup

### 1. Clone the Repository

```powershell
git clone https://github.com/vathsala-prabhu/RoadWatch.git
cd RoadWatch
```

### 2. Activate Environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root and configure the required environment variables.

For local execution, ensure AWS credentials are configured securely if you want to test S3 uploads or SNS notifications. The EC2 instance role is used automatically in the deployed environment.

### 5. Initialize and Seed Database

```powershell
python database.py
```

Applies database schema creation and migrations, including latitude, longitude, priority, and demonstration-data fields.

### 6. Run the Application

```powershell
python app.py
```

Open the application at:

**http://127.0.0.1:5000**

---

## 🔑 Demo Accounts

| Role | Email | Password | Allowed Capabilities |
|---|---|---|---|
| City Administrator | `admin@roadwatch.org` | `Admin@123` | Admin dashboard, analytics, status updater, complaint search and filtering. Cannot submit complaints. |
| Citizen User | `citizen@roadwatch.org` | `Citizen@123` | Complaint reporting, photo uploads, personal report tracking, and map access. |

*These are demonstration credentials. Change them before any production deployment.*

---

## 🧪 Automated Testing

Run the integration test suite:

```powershell
python -m unittest test_app.py
```

The 11 tests verify:

1. Public page rendering and live platform statistics.
2. Interactive map rendering and layer switching.
3. Demonstration complaints in Mysuru with valid bounding coordinates.
4. Preservation of genuine citizen complaints (`is_demo = 0`).
5. Strict role separation between citizens and administrators.
6. Guest redirection to sign-in for complaint submissions.
7. Citizen reporting with GPS coordinates.
8. Citizen reporting without GPS permission.
9. Admin search, keyword filtering, and origin filtering.
10. Admin complaint status updating (`Pending` → `In Progress` → `Resolved`).
11. Admin analytics and heatmap API access.

---

## 🔮 Future Enhancements

- Machine-learning-based road damage classification from uploaded images.
- Automated complaint severity assessment.
- SMS and additional notification channels.
- Role-based access for multiple municipal departments.
- Advanced GIS-based reporting and spatial analysis.
- Cloud database migration for improved scalability.
- Expanded monitoring, logging, and operational dashboards.

---

## 🎯 Project Objective

RoadWatch aims to bridge the gap between citizens and municipal authorities by providing a transparent, location-aware road damage reporting and management platform.

By combining geospatial technologies with cloud infrastructure, automated notifications, and analytics, the system supports faster complaint visibility, better prioritisation, and more efficient road maintenance management.

**Built with Python, Flask, AWS, and geospatial technologies.**
