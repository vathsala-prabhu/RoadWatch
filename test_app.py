import unittest
import json
import uuid
from app import app
from database import get_db_connection, create_tables

class RoadWatchIntegrationTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        create_tables()

    def test_01_home_page(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Road", response.data)
        self.assertIn(b"Watch", response.data)

    def test_02_map_page(self):
        response = self.client.get('/map')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"exploreMap", response.data)
        self.assertIn(b"Markers View", response.data)
        self.assertIn(b"Heatmap View", response.data)

    def test_03_mysuru_demonstration_data_presence(self):
        """Verify demonstration data represents Mysuru, Karnataka with valid coordinates."""
        response = self.client.get('/api/complaints')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertGreaterEqual(len(data), 10)

        # Check that demonstration data has is_demo == True
        demo_records = [c for c in data if c.get('is_demo')]
        self.assertGreaterEqual(len(demo_records), 10)

        # All coordinates must be within the Mysuru Karnataka geographic bounding box
        for c in data:
            lat = c['latitude']
            lng = c['longitude']
            self.assertGreaterEqual(lat, 12.20, f"Lat {lat} is outside Mysuru")
            self.assertLessEqual(lat, 12.45, f"Lat {lat} is outside Mysuru")
            self.assertGreaterEqual(lng, 76.50, f"Lng {lng} is outside Mysuru")
            self.assertLessEqual(lng, 76.75, f"Lng {lng} is outside Mysuru")

        # Verify requested Mysuru areas exist in location text
        all_locations = " ".join(c['location'] for c in data)
        required_areas = [
            "Vijayanagar", "Kuvempunagar", "Jayalakshmipuram", "Hebbal",
            "Saraswathipuram", "Bogadi", "Hootagalli", "Bannimantap",
            "Hunsur Road", "City Centre"
        ]
        for area in required_areas:
            self.assertIn(area.lower(), all_locations.lower(), f"Missing required area: {area}")

    def test_04_genuine_user_complaints_preserved(self):
        """Ensure genuine citizen complaints (is_demo=0) such as Koorgalli are preserved."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM complaints WHERE location LIKE '%koorgalli%'")
        row = cursor.fetchone()
        conn.close()
        self.assertIsNotNone(row, "Genuine user complaint in Koorgalli was lost!")
        self.assertEqual(row['is_demo'], 0)
        self.assertAlmostEqual(row['latitude'], 12.372493, places=3)
        self.assertAlmostEqual(row['longitude'], 76.585902, places=3)

    def test_05_admin_cannot_see_report_form_or_submit_complaints(self):
        """Verify role separation: Admins cannot access report form or submit complaints."""
        # 1. Login as Admin
        self.client.post('/login', data={
            'email': 'admin@roadwatch.org',
            'password': 'Admin@123'
        }, follow_redirects=True)

        # 2. Check Admin navigation does NOT contain 'Report Damage'
        home_res = self.client.get('/')
        self.assertNotIn(b'<a href="/report" class="nav-item">Report Damage</a>', home_res.data)
        self.assertIn(b"Complaint Management", home_res.data)

        # 3. Check Admin map page does NOT contain '+ Report New Damage'
        map_res = self.client.get('/map')
        self.assertNotIn(b"+ Report New Damage", map_res.data)

        # 4. Admin attempts GET /report - Must be blocked and redirected to /admin
        get_report_res = self.client.get('/report', follow_redirects=True)
        self.assertEqual(get_report_res.status_code, 200)
        self.assertIn(b"Administrators are not permitted to submit complaints", get_report_res.data)
        self.assertIn(b"Road Damage Management", get_report_res.data)

        # 5. Admin attempts POST /report - Backend must reject
        post_report_res = self.client.post('/report', data={
            'damage_type': 'Pothole',
            'location': 'Illegal Admin Submission St',
            'latitude': '12.3051',
            'longitude': '76.6551'
        }, follow_redirects=True)
        self.assertIn(b"Administrators are not permitted to submit complaints", post_report_res.data)

        # Verify nothing was inserted with this location
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM complaints WHERE location = 'Illegal Admin Submission St'")
        row = cursor.fetchone()
        conn.close()
        self.assertIsNone(row, "Admin was able to insert a complaint!")

    def test_06_guest_redirected_to_login_for_report(self):
        """Unauthenticated guests cannot access complaint submission form directly."""
        self.client.get('/logout', follow_redirects=True)
        res = self.client.get('/report', follow_redirects=True)
        self.assertIn(b"Please sign in or register as a citizen", res.data)
        self.assertIn(b"Sign in to RoadWatch", res.data)

    def test_07_citizen_can_submit_complaint_with_gps(self):
        """Citizen user can log in, view the report form, and submit with GPS."""
        # Login as Citizen
        self.client.post('/login', data={
            'email': 'citizen@roadwatch.org',
            'password': 'Citizen@123'
        }, follow_redirects=True)

        # Access GET /report
        form_res = self.client.get('/report')
        self.assertEqual(form_res.status_code, 200)
        self.assertIn(b"Pinpoint Precise Location", form_res.data)
        self.assertIn(b"Use My Current Location", form_res.data)

        # Submit POST /report in Mysuru
        unique_loc = f"Kuvempunagar 5th Cross {uuid.uuid4().hex[:6]}, Mysuru"
        post_res = self.client.post('/report', data={
            'damage_type': 'Pothole',
            'location': unique_loc,
            'description': 'Pothole near auto stand, Mysuru.',
            'priority': 'High',
            'latitude': '12.289500',
            'longitude': '76.623400'
        }, follow_redirects=True)
        self.assertEqual(post_res.status_code, 200)

        # Verify saved in database as citizen report (is_demo = 0)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM complaints WHERE location = ?", (unique_loc,))
        row = cursor.fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row['is_demo'], 0)
        self.assertAlmostEqual(row['latitude'], 12.2895, places=4)
        self.assertAlmostEqual(row['longitude'], 76.6234, places=4)

        # Verify citizen can view in My Reports
        my_res = self.client.get('/my-reports')
        self.assertIn(unique_loc.encode('utf-8'), my_res.data)

    def test_08_citizen_can_submit_complaint_without_gps(self):
        """Citizen can submit previously captured photo/report without mandatory GPS."""
        self.client.post('/login', data={
            'email': 'citizen@roadwatch.org',
            'password': 'Citizen@123'
        }, follow_redirects=True)

        unique_loc = f"Saraswathipuram Main Rd {uuid.uuid4().hex[:6]}, Mysuru"
        post_res = self.client.post('/report', data={
            'damage_type': 'Surface Cracking',
            'location': unique_loc,
            'description': 'Photo taken earlier, manual report without GPS.',
            'priority': 'Low',
            'latitude': '',
            'longitude': ''
        }, follow_redirects=True)
        self.assertEqual(post_res.status_code, 200)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM complaints WHERE location = ?", (unique_loc,))
        row = cursor.fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertIsNone(row['latitude'])
        self.assertEqual(row['is_demo'], 0)

    def test_09_admin_search_and_filter(self):
        """Admin can search complaints by keyword and filter by status and origin."""
        self.client.post('/login', data={
            'email': 'admin@roadwatch.org',
            'password': 'Admin@123'
        }, follow_redirects=True)

        # Search for Kuvempunagar
        search_res = self.client.get('/admin?search=Kuvempunagar')
        self.assertEqual(search_res.status_code, 200)
        self.assertIn(b"Kuvempunagar", search_res.data)

        # Filter by origin demo
        demo_filter_res = self.client.get('/admin?origin=demo')
        self.assertEqual(demo_filter_res.status_code, 200)
        self.assertIn(b"Demo Data", demo_filter_res.data)

        # Filter by status Pending
        pending_filter_res = self.client.get('/admin?status=Pending')
        self.assertEqual(pending_filter_res.status_code, 200)
        self.assertIn(b"Pending", pending_filter_res.data)

    def test_10_admin_status_update(self):
        """Admin can change complaint status between Pending, In Progress, and Resolved."""
        self.client.post('/login', data={
            'email': 'admin@roadwatch.org',
            'password': 'Admin@123'
        }, follow_redirects=True)

        # Fetch first complaint
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM complaints LIMIT 1")
        cid = cursor.fetchone()['id']
        conn.close()

        # Update to Resolved
        update_res = self.client.post(f'/admin/complaint/{cid}/status', data={
            'status': 'Resolved'
        }, follow_redirects=True)
        self.assertEqual(update_res.status_code, 200)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM complaints WHERE id = ?", (cid,))
        status = cursor.fetchone()['status']
        conn.close()
        self.assertEqual(status, 'Resolved')

    def test_11_admin_analytics_access(self):
        """Admin has full access to analytics and heatmap API."""
        self.client.post('/login', data={
            'email': 'admin@roadwatch.org',
            'password': 'Admin@123'
        }, follow_redirects=True)

        res = self.client.get('/api/admin/analytics')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data.decode('utf-8'))
        self.assertIn('summary', data)
        self.assertGreater(data['summary']['total'], 0)

if __name__ == '__main__':
    unittest.main()
