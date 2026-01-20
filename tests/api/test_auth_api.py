"""
API tests for authentication endpoints
"""
import pytest
import json


@pytest.mark.api
@pytest.mark.auth
class TestAuthAPI:
    """Test cases for authentication API endpoints"""
    
    def test_register_success(self, client, db_session):
        """Test successful user registration"""
        response = client.post('/api/register', json={
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'password123',
            'full_name': 'New User',
            'phone': '081234567890'
        })
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['message'] == 'Registrasi berhasil'
        assert 'user' in data
        assert data['user']['username'] == 'newuser'
    
    def test_register_missing_fields(self, client):
        """Test registration with missing required fields"""
        response = client.post('/api/register', json={
            'username': 'testuser',
            'email': 'test@example.com'
            # Missing password and full_name
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
    
    def test_register_duplicate_username(self, client, sample_user):
        """Test registration with duplicate username"""
        response = client.post('/api/register', json={
            'username': 'testuser',  # Already exists
            'email': 'different@example.com',
            'password': 'password123',
            'full_name': 'Different User'
        })
        
        assert response.status_code in [400, 409]
        data = response.get_json()
        assert 'error' in data
    
    def test_login_success(self, client, sample_user):
        """Test successful login"""
        response = client.post('/api/login', json={
            'username': 'testuser',
            'password': 'password123'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'token' in data
        assert 'user' in data
        assert data['user']['username'] == 'testuser'
    
    def test_login_wrong_password(self, client, sample_user):
        """Test login with wrong password"""
        response = client.post('/api/login', json={
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        
        assert response.status_code == 401
        data = response.get_json()
        assert 'error' in data
    
    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user"""
        response = client.post('/api/login', json={
            'username': 'nonexistent',
            'password': 'password123'
        })
        
        assert response.status_code == 401
        data = response.get_json()
        assert 'error' in data
    
    def test_login_missing_credentials(self, client):
        """Test login with missing credentials"""
        response = client.post('/api/login', json={
            'username': 'testuser'
            # Missing password
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_google_login_new_user(self, client, db_session):
        """Test Google login for a new user (account creation)"""
        data = {
            'email': 'newgoogle@example.com',
            'name': 'Google User',
            'google_id': '1234567890'
        }
        
        response = client.post('/api/google-login', json=data)
        
        assert response.status_code == 200
        res_data = response.get_json()
        assert 'token' in res_data
        assert res_data['user']['email'] == 'newgoogle@example.com'
        assert res_data['user']['full_name'] == 'Google User'
        
        # Verify in DB
        from models import User
        user = db_session.query(User).filter_by(email='newgoogle@example.com').first()
        assert user is not None
        assert user.bio == 'Login via Google'

    def test_google_login_existing_user_email_match(self, client, db_session):
        """Test Google login when user already exists with same email"""
        from models import User
        
        # Pre-create user with same email
        existing_user = User(
            username='existing',
            email='existing@example.com',
            full_name='Existing User',
            phone='123'
        )
        existing_user.set_password('pass')
        db_session.add(existing_user)
        db_session.commit()
        
        data = {
            'email': 'existing@example.com',
            'name': 'Existing Google Mode',
            'google_id': '987654321'
        }
        
        response = client.post('/api/google-login', json=data)
        assert response.status_code == 200
        res_data = response.get_json()
        assert res_data['user']['id'] == existing_user.id
        
    def test_google_login_incomplete_data(self, client):
        """Test Google login with missing fields"""
        data = {
            'email': 'bad@example.com'
            # Missing name, google_id
        }
        response = client.post('/api/google-login', json=data)
        assert response.status_code == 400

    def test_google_login_username_collision(self, client, db_session):
        """Test Google login when base username from email is taken"""
        from models import User
        
        # User 1: 'john'
        user1 = User(
            username='john',
            email='john.other@example.com',
            full_name='John Other'
        )
        user1.set_password('pass')
        db_session.add(user1)
        db_session.commit()
        
        # User 2 login via Google with 'john@gmail.com' -> base is 'john'
        # Should generate 'john1'
        data = {
            'email': 'john@gmail.com',
            'name': 'John Google',
            'google_id': '111222'
        }
        
        response = client.post('/api/google-login', json=data)
        assert response.status_code == 200
        res_data = response.get_json()
        assert res_data['user']['username'] == 'john1'
