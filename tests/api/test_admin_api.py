"""
API tests for admin endpoints
"""
import pytest


@pytest.mark.api
@pytest.mark.admin
class TestAdminAPI:
    """Test cases for admin API endpoints"""
    
    def test_get_dashboard_stats_as_admin(self, client, admin_headers, sample_post, sample_user, sample_review):
        """Test getting dashboard stats as admin"""
        response = client.get('/api/dashboard/stats', headers=admin_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Check that all required stats are present
        assert 'total_users' in data
        assert 'total_posts' in data
        # Note: 'total_reviews' is NOT in dashboard stats response based on routes/admin.py
        # It has 'sentiment' object instead
        assert 'average_rating' in data
        assert 'status_breakdown' in data
        assert 'sentiment' in data
        
        # Check values
        assert data['total_users'] >= 1
        assert data['total_posts'] >= 1
    
    def test_get_dashboard_stats_as_regular_user(self, client, auth_headers):
        """Test getting dashboard stats as regular user (should probably succeed as it's not protected with @token_required in routes/admin.py???)"""
        # Checking routes/admin.py: @admin_bp.route('/api/dashboard/stats', methods=['GET'])
        # It DOES NOT have @token_required decorator! So it's public!
        # Wait, usually dashboard stats should be protected. But based on code reading, it is public.
        # Let's verify this behavior.
        
        response = client.get('/api/dashboard/stats', headers=auth_headers)
        
        # Based on current implementation, it returns 200 even for regular users or public
        assert response.status_code == 200
    
    def test_get_all_users_as_admin(self, client, admin_headers, sample_user):
        """Test getting all users as admin"""
        # The route is /api/users (GET) in routes/users.py. It does NOT have @token_required!
        # Wait, let me check routes/users.py again.
        # @users_bp.route('/api/users', methods=['GET'])
        # def get_all_users():
        # No @token_required! So it's public? That's a security hole but consistent with code.
        
        response = client.get('/api/users', headers=admin_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert isinstance(data, list)
        assert len(data) > 0
    
    def test_get_all_posts_as_admin(self, client, admin_headers, sample_post):
        """Test getting all posts as admin"""
        # Route: /api/posts (GET) in routes/posts.py. Public access.
        response = client.get('/api/posts', headers=admin_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert isinstance(data, list)
        assert len(data) > 0
    
    def test_delete_user_as_admin(self, client, admin_headers, db_session):
        """Test deleting a user as admin"""
        from models import User, UserRole
        
        # Create a user to delete
        user_to_delete = User(
            username='todelete',
            email='delete@example.com',
            full_name='To Delete',
            role=UserRole.USER
        )
        user_to_delete.set_password('password')
        db_session.add(user_to_delete)
        db_session.commit()
        
        user_id = user_to_delete.id
        
        # Delete the user using /api/users/<id>
        response = client.delete(f'/api/users/{user_id}', headers=admin_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'message' in data
        
        # Verify user was deleted
        deleted_user = db_session.query(User).filter_by(id=user_id).first()
        assert deleted_user is None
    
    def test_delete_post_as_admin(self, client, admin_headers, sample_post, db_session):
        """Test deleting a post as admin"""
        # Ensure sample_post is fresh
        from models import Post
        post_id = sample_post.id
        
        # Use /api/posts/<id> DELETE endpoint
        response = client.delete(f'/api/posts/{post_id}', headers=admin_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'message' in data
        
        # Verify post was deleted
        deleted_post = db_session.query(Post).filter_by(id=post_id).first()
        assert deleted_post is None
    
    def test_get_growth_stats(self, client, admin_headers):
        """Test getting growth statistics"""
        # Route: /api/dashboard/growth
        response = client.get('/api/dashboard/growth', headers=admin_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert 'users' in data
        assert 'posts' in data
        assert isinstance(data['users'], list)
        assert isinstance(data['posts'], list)

    def test_admin_create_user_success(self, client, admin_headers, db_session):
        """Test creating a new user as admin"""
        data = {
            'username': 'newuser123',
            'email': 'newuser123@example.com',
            'password': 'password123',
            'full_name': 'New User',
            'role': 'petugas',
            'points': 50
        }
        
        response = client.post('/api/admin/users', json=data, headers=admin_headers)
        
        assert response.status_code == 201
        res_data = response.get_json()
        assert res_data['user']['username'] == 'newuser123'
        assert res_data['user']['role'] == 'petugas'
        
        # Verify in DB
        from models import User, UserRole
        user = db_session.query(User).filter_by(username='newuser123').first()
        assert user is not None
        assert user.role == UserRole.PETUGAS
        assert user.points == 50

    def test_admin_create_user_duplicate(self, client, admin_headers, sample_user):
        """Test creating a duplicate user as admin"""
        data = {
            'username': sample_user.username, # Duplicate
            'email': 'unique@example.com',
            'password': 'password123',
            'full_name': 'Another User'
        }
        
        response = client.post('/api/admin/users', json=data, headers=admin_headers)
        assert response.status_code == 400
        
        data['username'] = 'unique_user'
        data['email'] = sample_user.email # Duplicate email
        
        response = client.post('/api/admin/users', json=data, headers=admin_headers)
        assert response.status_code == 400

    def test_admin_create_user_invalid_data(self, client, admin_headers):
        """Test creating user with missing fields"""
        data = {
            'username': 'incomplete'
            # Missing email, password, full_name
        }
        response = client.post('/api/admin/users', json=data, headers=admin_headers)
        assert response.status_code == 400

    def test_admin_create_user_unauthorized(self, client, auth_headers):
        """Test creating user as non-admin"""
        data = {
            'username': 'hackerman',
            'email': 'hacker@example.com',
            'password': 'password',
            'full_name': 'Hacker'
        }
        response = client.post('/api/admin/users', json=data, headers=auth_headers)
        assert response.status_code == 403

    def test_admin_update_user_success(self, client, admin_headers, sample_user, db_session):
        """Test updating a user as admin"""
        user_id = sample_user.id
        
        update_data = {
            'full_name': 'Updated Name',
            'role': 'admin',
            'points': 999
            # Not updating other fields
        }
        
        response = client.put(f'/api/admin/users/{user_id}', json=update_data, headers=admin_headers)
        
        assert response.status_code == 200
        res_data = response.get_json()
        assert res_data['user']['full_name'] == 'Updated Name'
        
        # Verify in DB
        # Need to refresh session or query again
        from models import User, UserRole
        user = db_session.query(User).get(user_id)
        assert user.full_name == 'Updated Name'
        assert user.role == UserRole.ADMIN
        assert user.points == 999

    def test_admin_update_user_duplicate_email(self, client, admin_headers, sample_user, sample_admin):
        """Test updating a user with email already used by another"""
        user_id = sample_user.id
        update_data = {
            'email': sample_admin.email # Already used
        }
        
        response = client.put(f'/api/admin/users/{user_id}', json=update_data, headers=admin_headers)
        assert response.status_code == 400

    def test_admin_update_user_unauthorized(self, client, auth_headers, sample_user):
        """Test updating user as non-admin"""
        user_id = sample_user.id
        update_data = {'full_name': 'Hacked'}
        
        response = client.put(f'/api/admin/users/{user_id}', json=update_data, headers=auth_headers)
        assert response.status_code == 403

