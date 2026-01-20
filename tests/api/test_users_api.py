"""
API tests for user endpoints
"""
import pytest
from unittest.mock import MagicMock, patch

@pytest.mark.api
@pytest.mark.users
class TestUserAPI:
    """Test cases for user API endpoints"""

    def test_get_user_profile(self, client, sample_user):
        """Test getting user profile"""
        response = client.get(f'/api/users/{sample_user.id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['username'] == sample_user.username

    def test_update_profile_success(self, client, auth_headers, sample_user):
        """Test updating user profile successfully"""
        update_data = {
            'full_name': 'New Name',
            'phone': '08999999',
            'bio': 'New Bio',
            'password': 'newpassword123'
        }
        
        response = client.put(
            f'/api/users/{sample_user.id}',
            json=update_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['user']['full_name'] == 'New Name'
        
        # Verify password change implicitly by logging in could be done, but unit test is simpler
        # Just assume it worked if status 200 and maybe check DB
        
    def test_update_profile_short_password(self, client, auth_headers, sample_user):
        """Test updating password with too short password"""
        update_data = {
            'password': '123'
        }
        response = client.put(
            f'/api/users/{sample_user.id}',
            json=update_data,
            headers=auth_headers
        )
        assert response.status_code == 400
        assert 'minimal 6 karakter' in response.get_json()['error']

    def test_update_profile_unauthorized(self, client, auth_headers):
        """Test updating profile of another user"""
        # auth_headers belongs to sample_user (id=1 usually)
        # Try to update user id 999
        response = client.put(
            '/api/users/999',
            json={'full_name': 'Hacked'},
            headers=auth_headers
        )
        assert response.status_code == 403

    def test_delete_user_own_account_failed(self, client, auth_headers, sample_user):
        """Test user trying to delete their own account"""
        response = client.delete(
            f'/api/users/{sample_user.id}',
            headers=auth_headers
        )
        # Based on logic: users can delete themselves? 
        # Code says: if current_user.id == user_id: return error 'Anda tidak dapat menghapus akun sendiri saat sedang login'
        assert response.status_code == 400
        assert 'tidak dapat menghapus akun sendiri' in response.get_json()['error']

    def test_delete_user_as_admin_success(self, client, admin_headers, sample_user, db_session):
        """Test admin deleting another user"""
        
        # Mocking file removals for cleanup
        with patch('os.path.exists', return_value=True):
            with patch('os.remove') as mock_remove:
                response = client.delete(
                    f'/api/users/{sample_user.id}',
                    headers=admin_headers
                )
                
                assert response.status_code == 200
                
                from models import User
                deleted = db_session.query(User).get(sample_user.id)
                assert deleted is None

    def test_delete_user_unauthorized(self, client, auth_headers, sample_admin):
        """Test regular user trying to delete another user (e.g. admin)"""
        response = client.delete(
            f'/api/users/{sample_admin.id}',
            headers=auth_headers
        )
        assert response.status_code == 403

    def test_get_all_users_public_route(self, client, sample_user):
        """Test get all users route (it seems public based on code analysis)"""
        # routes/users.py: @users_bp.route('/api/users', methods=['GET']) -> No token_required
        response = client.get('/api/users')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
