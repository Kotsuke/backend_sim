"""
Integration tests for complete user flows
"""
import pytest


@pytest.mark.integration
class TestUserFlow:
    """Test complete user workflows"""
    
    def test_complete_registration_and_login_flow(self, client, db_session):
        """Test complete flow: register -> login -> get profile"""
        # Step 1: Register
        register_response = client.post('/api/register', json={
            'username': 'flowuser',
            'email': 'flow@example.com',
            'password': 'password123',
            'full_name': 'Flow User',
            'phone': '081234567890'
        })
        assert register_response.status_code == 201
        
        # Step 2: Login
        login_response = client.post('/api/login', json={
            'username': 'flowuser',
            'password': 'password123'
        })
        assert login_response.status_code == 200
        login_data = login_response.get_json()
        assert 'token' in login_data
        
        token = login_data['token']
        user_id = login_data['user']['id']
        headers = {'Authorization': f'Bearer {token}'}
        
        # Step 3: Get profile (using user ID)
        profile_response = client.get(f'/api/users/{user_id}', headers=headers)
        assert profile_response.status_code == 200
        profile_data = profile_response.get_json()
        assert profile_data['username'] == 'flowuser'
    
    def test_post_creation_and_verification_flow(self, client, sample_user, db_session):
        """Test complete flow: login -> create post -> verify post"""
        from models import Post
        
        # Step 1: Login
        login_response = client.post('/api/login', json={
            'username': 'testuser',
            'password': 'password123'
        })
        assert login_response.status_code == 200
        token = login_response.get_json()['token']
        headers = {'Authorization': f'Bearer {token}'}
        
        # Step 2: Create a post manually in DB (simulating upload)
        post = Post(
            user_id=sample_user.id,
            image_path='integration_test.jpg',
            latitude=-6.200000,
            longitude=106.816666,
            severity='SERIUS',
            caption='Integration test post'
        )
        db_session.add(post)
        db_session.commit()
        post_id = post.id
        
        # Step 3: Verify the post
        verify_response = client.post(
            f'/api/posts/{post_id}/verify',
            json={'type': 'CONFIRM'},
            headers=headers
        )
        assert verify_response.status_code == 200
        
        # Step 4: Check post verification count
        db_session.refresh(post)
        assert post.confirm_count == 1
    
    def test_admin_workflow(self, client, sample_admin, sample_user, db_session):
        """Test admin workflow: login -> view stats -> manage users"""
        # Step 1: Admin login
        login_response = client.post('/api/login', json={
            'username': 'admin',
            'password': 'admin123'
        })
        assert login_response.status_code == 200
        token = login_response.get_json()['token']
        admin_headers = {'Authorization': f'Bearer {token}'}
        
        # Step 2: View dashboard stats
        stats_response = client.get('/api/dashboard/stats', headers=admin_headers)
        assert stats_response.status_code == 200
        stats_data = stats_response.get_json()
        assert 'total_users' in stats_data
        
        # Step 3: Get all users
        users_response = client.get('/api/users', headers=admin_headers)
        assert users_response.status_code == 200
        users_data = users_response.get_json()
        assert isinstance(users_data, list)
        assert len(users_data) > 0
    
    def test_petugas_update_status_workflow(self, client, sample_petugas, sample_post, db_session):
        """Test petugas workflow: login -> update post status"""
        # Step 1: Petugas login
        login_response = client.post('/api/login', json={
            'username': 'petugas',
            'password': 'petugas123'
        })
        assert login_response.status_code == 200
        token = login_response.get_json()['token']
        petugas_headers = {'Authorization': f'Bearer {token}'}
        
        # Step 2: Update post status to DIPROSES
        update_response = client.put(
            f'/api/posts/{sample_post.id}/status',
            json={'status': 'DIPROSES'},
            headers=petugas_headers
        )
        assert update_response.status_code == 200
        
        # Step 3: Verify status was updated
        db_session.refresh(sample_post)
        assert sample_post.status.upper() == 'DIPROSES'
        
        # Step 4: Update post status to SELESAI
        complete_response = client.put(
            f'/api/posts/{sample_post.id}/status',
            json={'status': 'SELESAI'},
            headers=petugas_headers
        )
        assert complete_response.status_code == 200
        
        db_session.refresh(sample_post)
        assert sample_post.status.upper() == 'SELESAI'
    
    def test_review_submission_workflow(self, client, sample_user):
        """Test review workflow: login -> submit review -> view reviews"""
        # Step 1: Login
        login_response = client.post('/api/login', json={
            'username': 'testuser',
            'password': 'password123'
        })
        assert login_response.status_code == 200
        token = login_response.get_json()['token']
        headers = {'Authorization': f'Bearer {token}'}
        
        # Step 2: Submit review
        review_response = client.post('/api/reviews',
            json={
                'rating': 5,
                'comment': 'Aplikasi sangat membantu!'
            },
            headers=headers
        )
        assert review_response.status_code == 201
        
        # Step 3: Get all reviews
        get_reviews_response = client.get('/api/reviews')
        assert get_reviews_response.status_code == 200
        reviews_data = get_reviews_response.get_json()
        assert isinstance(reviews_data, list)
        
        # Check if our review is in the list
        review_found = False
        for review in reviews_data:
            if review['user_id'] == sample_user.id:
                review_found = True
                break
        
        assert review_found
