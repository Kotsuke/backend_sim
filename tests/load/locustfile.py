"""
Load testing with Locust
Test the performance and scalability of the SmartInfra Backend API
"""
from locust import HttpUser, task, between
import random


class SmartInfraUser(HttpUser):
    """Simulated user for load testing"""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    def on_start(self):
        """Called when a simulated user starts"""
        # Register and login
        self.username = f"loadtest_user_{random.randint(1000, 9999)}"
        self.email = f"{self.username}@example.com"
        self.password = "password123"
        
        # Register
        self.client.post("/api/register", json={
            "username": self.username,
            "email": self.email,
            "password": self.password,
            "full_name": f"Load Test User {random.randint(1, 1000)}",
            "phone": f"081234{random.randint(100000, 999999)}"
        })
        
        # Login
        response = self.client.post("/api/login", json={
            "username": self.username,
            "password": self.password
        })

# ... (inside AdminUser) ...

    def on_start(self):
        """Login as admin"""
        # You need to create an admin user first
        response = self.client.post("/api/login", json={
            "username": "admin",
            "password": "admin123"
        })

# ... (inside PetugasUser) ...

    def on_start(self):
        """Login as petugas"""
        response = self.client.post("/api/login", json={
            "username": "petugas",
            "password": "petugas123"
        })
        
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = None
            self.headers = {}
    
    @task(2)
    def get_posts(self):
        """Get posts"""
        if self.token:
            self.client.get("/api/posts", headers=self.headers)
    
    @task(1)
    def update_post_status(self):
        """Update post status"""
        if self.token:
            post_id = random.randint(1, 100)
            statuses = ['MENUNGGU', 'DIPROSES', 'SELESAI']
            status = random.choice(statuses)
            
            self.client.put(
                f"/api/posts/{post_id}/status",
                json={"status": status},
                headers=self.headers
            )


# How to run:
# 1. Install locust: pip install locust
# 2. Run: locust -f tests/load/locustfile.py --host=http://localhost:5000
# 3. Open browser: http://localhost:8089
# 4. Set number of users and spawn rate
# 5. Start test and monitor results
