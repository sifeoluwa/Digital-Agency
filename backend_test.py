import requests
import unittest
import uuid
import time
from datetime import datetime

class DigitalAgencyAPITester(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url = "https://6bb5864d-497d-4c1c-b3b4-7ad65f079111.preview.emergentagent.com"
        self.token = None
        self.user = None
        self.project_id = None
        self.task_id = None
        
        # Test data
        self.test_user = {
            "name": f"Test User {uuid.uuid4().hex[:8]}",
            "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
            "password": "TestPassword123!",
            "role": "developer"
        }
        
        self.test_project = {
            "name": f"Test Project {uuid.uuid4().hex[:8]}",
            "description": "This is a test project created by automated tests",
            "client_name": "Test Client",
            "status": "planning",
            "team_members": []
        }
        
        self.test_task = {
            "title": f"Test Task {uuid.uuid4().hex[:8]}",
            "description": "This is a test task created by automated tests",
            "status": "todo",
            "priority": "medium"
        }

    def setUp(self):
        print(f"\n{'='*50}")
        print(f"Starting test: {self._testMethodName}")
        print(f"{'='*50}")

    def test_01_health_check(self):
        """Test API health endpoint"""
        response = requests.get(f"{self.base_url}/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        print("✅ Health check passed")

    def test_02_register_user(self):
        """Test user registration"""
        response = requests.post(
            f"{self.base_url}/api/auth/register", 
            json=self.test_user
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("access_token", data)
        self.assertIn("user", data)
        self.assertEqual(data["user"]["name"], self.test_user["name"])
        self.assertEqual(data["user"]["email"], self.test_user["email"])
        self.assertEqual(data["user"]["role"], self.test_user["role"])
        
        # Save token and user for subsequent tests
        self.token = data["access_token"]
        self.user = data["user"]
        print(f"✅ User registration passed - Created user: {self.user['name']}")

    def test_03_login_user(self):
        """Test user login"""
        response = requests.post(
            f"{self.base_url}/api/auth/login", 
            json={
                "email": self.test_user["email"],
                "password": self.test_user["password"]
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("access_token", data)
        self.assertIn("user", data)
        self.assertEqual(data["user"]["email"], self.test_user["email"])
        
        # Update token
        self.token = data["access_token"]
        print("✅ User login passed")

    def test_04_get_current_user(self):
        """Test getting current user profile"""
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(f"{self.base_url}/api/auth/me", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["email"], self.test_user["email"])
        print("✅ Get current user passed")

    def test_05_get_users(self):
        """Test getting all users"""
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(f"{self.base_url}/api/users", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        # Verify our test user is in the list
        user_emails = [user["email"] for user in data]
        self.assertIn(self.test_user["email"], user_emails)
        print(f"✅ Get users passed - Found {len(data)} users")

    def test_06_create_project(self):
        """Test project creation"""
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.post(
            f"{self.base_url}/api/projects", 
            json=self.test_project,
            headers=headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("project", data)
        self.assertEqual(data["project"]["name"], self.test_project["name"])
        
        # Save project ID for subsequent tests
        self.project_id = data["project"]["project_id"]
        print(f"✅ Create project passed - Created project: {self.test_project['name']}")

    def test_07_get_projects(self):
        """Test getting all projects"""
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(f"{self.base_url}/api/projects", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        # Verify our test project is in the list
        project_ids = [project["project_id"] for project in data]
        self.assertIn(self.project_id, project_ids)
        print(f"✅ Get projects passed - Found {len(data)} projects")

    def test_08_get_project_by_id(self):
        """Test getting a specific project by ID"""
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(
            f"{self.base_url}/api/projects/{self.project_id}", 
            headers=headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["project_id"], self.project_id)
        self.assertEqual(data["name"], self.test_project["name"])
        print("✅ Get project by ID passed")

    def test_09_update_project(self):
        """Test updating a project"""
        headers = {"Authorization": f"Bearer {self.token}"}
        updated_project = self.test_project.copy()
        updated_project["name"] = f"Updated {self.test_project['name']}"
        updated_project["status"] = "active"
        
        response = requests.put(
            f"{self.base_url}/api/projects/{self.project_id}", 
            json=updated_project,
            headers=headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], updated_project["name"])
        self.assertEqual(data["status"], updated_project["status"])
        print("✅ Update project passed")

    def test_10_create_task(self):
        """Test task creation"""
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.post(
            f"{self.base_url}/api/projects/{self.project_id}/tasks", 
            json=self.test_task,
            headers=headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("task", data)
        self.assertEqual(data["task"]["title"], self.test_task["title"])
        self.assertEqual(data["task"]["project_id"], self.project_id)
        
        # Save task ID for subsequent tests
        self.task_id = data["task"]["task_id"]
        print(f"✅ Create task passed - Created task: {self.test_task['title']}")

    def test_11_get_project_tasks(self):
        """Test getting all tasks for a project"""
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(
            f"{self.base_url}/api/projects/{self.project_id}/tasks", 
            headers=headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        # Verify our test task is in the list
        task_ids = [task["task_id"] for task in data]
        self.assertIn(self.task_id, task_ids)
        print(f"✅ Get project tasks passed - Found {len(data)} tasks")

    def test_12_update_task(self):
        """Test updating a task"""
        headers = {"Authorization": f"Bearer {self.token}"}
        task_update = {
            "title": f"Updated {self.test_task['title']}",
            "status": "in-progress",
            "priority": "high"
        }
        
        response = requests.put(
            f"{self.base_url}/api/projects/{self.project_id}/tasks/{self.task_id}", 
            json=task_update,
            headers=headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["title"], task_update["title"])
        self.assertEqual(data["status"], task_update["status"])
        self.assertEqual(data["priority"], task_update["priority"])
        print("✅ Update task passed")

    def test_13_delete_task(self):
        """Test deleting a task"""
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.delete(
            f"{self.base_url}/api/projects/{self.project_id}/tasks/{self.task_id}", 
            headers=headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["message"], "Task deleted successfully")
        print("✅ Delete task passed")

    def test_14_delete_project(self):
        """Test deleting a project"""
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.delete(
            f"{self.base_url}/api/projects/{self.project_id}", 
            headers=headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["message"], "Project deleted successfully")
        print("✅ Delete project passed")

    def test_15_invalid_login(self):
        """Test login with invalid credentials"""
        response = requests.post(
            f"{self.base_url}/api/auth/login", 
            json={
                "email": "nonexistent@example.com",
                "password": "WrongPassword123"
            }
        )
        self.assertEqual(response.status_code, 401)
        print("✅ Invalid login test passed")

if __name__ == "__main__":
    # Run tests in order
    test_suite = unittest.TestSuite()
    test_suite.addTest(DigitalAgencyAPITester('test_01_health_check'))
    test_suite.addTest(DigitalAgencyAPITester('test_02_register_user'))
    test_suite.addTest(DigitalAgencyAPITester('test_03_login_user'))
    test_suite.addTest(DigitalAgencyAPITester('test_04_get_current_user'))
    test_suite.addTest(DigitalAgencyAPITester('test_05_get_users'))
    test_suite.addTest(DigitalAgencyAPITester('test_06_create_project'))
    test_suite.addTest(DigitalAgencyAPITester('test_07_get_projects'))
    test_suite.addTest(DigitalAgencyAPITester('test_08_get_project_by_id'))
    test_suite.addTest(DigitalAgencyAPITester('test_09_update_project'))
    test_suite.addTest(DigitalAgencyAPITester('test_10_create_task'))
    test_suite.addTest(DigitalAgencyAPITester('test_11_get_project_tasks'))
    test_suite.addTest(DigitalAgencyAPITester('test_12_update_task'))
    test_suite.addTest(DigitalAgencyAPITester('test_13_delete_task'))
    test_suite.addTest(DigitalAgencyAPITester('test_14_delete_project'))
    test_suite.addTest(DigitalAgencyAPITester('test_15_invalid_login'))
    
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(test_suite)