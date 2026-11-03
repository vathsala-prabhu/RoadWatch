# RoadWatch — Cloud-Based Road Damage Reporting and Management System

A Flask + SQLite web application for citizens to report road damage and for administrators to review complaints and update their status.

## Features
- Citizen registration and login
- Password hashing
- Submit road damage reports with optional image
- Citizen dashboard to track submitted reports
- Admin dashboard to review all reports and update status
- Local image storage for development
- Optional Amazon S3 image storage using Boto3
- Responsive HTML/CSS/JavaScript interface

## 1. Setup on Windows

Open this folder in VS Code, then in the terminal run:

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` and set a long random `SECRET_KEY`. Leave `S3_BUCKET` blank for local development.

## 2. Run the application

```powershell
python app.py
```

Open http://127.0.0.1:5000

The SQLite database is created automatically as `road_damage.db`.

## 3. Create an administrator

In a second terminal (with the virtual environment activated), run:

```powershell
python create_admin.py
```

Enter the admin name, email and password. Then log in using that account. Do not make a normal citizen account an admin manually through the public form.

## 4. Local test flow

1. Register a citizen account.
2. Log in.
3. Submit a road damage report and optionally attach a JPG/PNG/WEBP image (maximum 5 MB).
4. Check the report in My Reports.
5. Log out.
6. Log in with the admin account.
7. Update the complaint status.

## 5. Optional Amazon S3 configuration

Create a private S3 bucket. Attach an EC2 IAM role that grants the application only the required permissions on that bucket (at minimum `s3:PutObject` and `s3:GetObject` for the relevant object prefix).

Set these values in `.env` for local testing, or as environment variables on EC2:

```env
S3_BUCKET=your-unique-bucket-name
AWS_REGION=ap-south-1
```

For local development, configure AWS credentials using the AWS CLI (`aws configure`) or an appropriate AWS profile. On EC2, prefer an attached IAM instance role and do not place access keys in the application.

When `S3_BUCKET` is blank, images are stored in the local `uploads/` folder. When it is set, images are uploaded to S3 and displayed through short-lived presigned URLs.

## 6. Deployment notes

- Use a production WSGI server such as Gunicorn; do not use Flask's development server in production.
- Keep `.env`, the SQLite database, and uploaded local files out of Git.
- Back up the SQLite database. For a small class project, SQLite is acceptable, but it is not intended for high-concurrency production workloads.
- Configure HTTPS before collecting real personal information.
- Add CSRF protection, rate limiting, stronger admin account controls and audit logs before any real-world/public deployment.
- CloudWatch can monitor EC2 metrics. Install/configure the CloudWatch Agent if you also want application log files sent to CloudWatch Logs.
