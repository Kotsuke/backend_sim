"""
API tests for posts endpoints
"""
import pytest
import io


@pytest.mark.api
@pytest.mark.posts
class TestPostsAPI:
    """Test cases for posts API endpoints"""
    
    def test_get_posts(self, client, sample_post):
        """Test getting all posts"""
        response = client.get('/api/posts')
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Returns list directly
        assert isinstance(data, list)
        assert len(data) > 0
    
    # GET /api/posts/<id> does NOT exist in routes/posts.py
    # So removing test_get_post_by_id and test_get_nonexistent_post
    
    def test_filter_posts_by_status_query_param(self, client, db_session, sample_user):
        """Test filtering posts using /api/posts/by-status endpoint"""
        from models import Post
        
        # Create posts with different statuses
        post1 = Post(user_id=sample_user.id, image_path='1.jpg', latitude=-6.2, 
                    longitude=106.8, severity='SERIUS', status='MENUNGGU')
        post2 = Post(user_id=sample_user.id, image_path='2.jpg', latitude=-6.2, 
                    longitude=106.8, severity='SERIUS', status='DIPROSES')
        
        db_session.add_all([post1, post2])
        db_session.commit()
        
        # Use specific filter endpoint: /api/posts/by-status?status=MENUNGGU
        response = client.get('/api/posts/by-status?status=MENUNGGU')
        assert response.status_code == 200
        data = response.get_json()
        
        assert isinstance(data, list)
        for post in data:
            assert post['status'] == 'MENUNGGU'
    
    def test_filter_posts_by_location(self, client, db_session, sample_user):
        """Test filtering posts by location using /api/posts/filter endpoint"""
        from models import Post
        
        post1 = Post(user_id=sample_user.id, image_path='1.jpg', latitude=-6.2,
                    longitude=106.8, severity='SERIUS', province='DKI Jakarta')
        post2 = Post(user_id=sample_user.id, image_path='2.jpg', latitude=-6.2,
                    longitude=106.8, severity='SERIUS', province='Jawa Barat')
        
        db_session.add_all([post1, post2])
        db_session.commit()
        
        # Use specific filter endpoint: /api/posts/filter
        response = client.get('/api/posts/filter?province=DKI Jakarta')
        assert response.status_code == 200
        data = response.get_json()
        
        assert isinstance(data, list)
        for post in data:
            assert post['province'] == 'DKI Jakarta'
    
    def test_create_post_without_auth(self, client):
        """Test creating a post without authentication"""
        # Route is /api/upload
        response = client.post('/api/upload', data={
            'caption': 'Test post'
        })
        
        # Should require authentication
        assert response.status_code == 401
    
    def test_verify_post(self, client, sample_post, auth_headers, db_session):
        """Test verifying a post"""
        # Route: /api/posts/<id>/verify
        # Body: {'type': 'CONFIRM'} (uppercase based on routes/posts.py)
        response = client.post(
            f'/api/posts/{sample_post.id}/verify',
            json={'type': 'CONFIRM'},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'message' in data
        
        # Check if verification count increased
        db_session.refresh(sample_post)
        assert sample_post.confirm_count == 1  # Was 0 initially
    
    def test_verify_nonexistent_post(self, client, auth_headers):
        """Test verifying a non-existent post"""
        response = client.post(
            '/api/posts/99999/verify',
            json={'type': 'CONFIRM'},
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    def test_update_post_status_as_petugas(self, client, sample_post, petugas_headers, db_session):
        """Test updating post status as petugas"""
        response = client.put(
            f'/api/posts/{sample_post.id}/status',
            json={'status': 'DIPROSES'},
            headers=petugas_headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'message' in data
        
        # Check if status was updated
        db_session.refresh(sample_post)
        assert sample_post.status.upper() == 'DIPROSES'
    
    def test_update_post_status_as_regular_user(self, client, sample_post, auth_headers):
        """Test updating post status as regular user (should fail)"""
        response = client.put(
            f'/api/posts/{sample_post.id}/status',
            json={'status': 'DIPROSES'},
            headers=auth_headers
        )
        
        # Regular users should not be able to update status
        assert response.status_code in [403, 401]

    @pytest.mark.current
    def test_create_post_success(self, client, auth_headers, db_session):
        """Test creating a post successfully with image upload"""
        from unittest.mock import MagicMock, patch
        import numpy as np
        
        # Mock YOLO model response with detection
        mock_box = MagicMock()
        mock_box.conf = [0.9]
        # xywh: [50, 50, 10, 10] (small box)
        mock_box.xywh = [[50, 50, 10, 10]]
        
        mock_yolo_response = MagicMock()
        mock_yolo_response.boxes = [mock_box] 
        
        mock_model = MagicMock()
        mock_model.predict.return_value = [mock_yolo_response]
        
        # Mock cv2.imdecode
        fake_img = np.zeros((100, 100, 3), dtype=np.uint8)
        
        with patch('routes.posts.yolo_model', mock_model):
            with patch('cv2.imdecode', return_value=fake_img):
                data = {
                    'image': (io.BytesIO(b"fakeimagecontent"), 'test_image.jpg'),
                    'latitude': -6.2,
                    'longitude': 106.8,
                    'full_address': 'Jalan Test',
                    'province': 'DKI Jakarta',
                    'city': 'Jakarta Pusat',
                    'district': 'Menteng'
                }
                
                response = client.post(
                    '/api/upload', 
                    data=data, 
                    content_type='multipart/form-data',
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                res_data = response.get_json()
                assert res_data['message'] == 'Upload berhasil'
                assert 'data' in res_data
                # Box is small, fewer than 4 -> TIDAK_SERIUS
                assert res_data['data']['severity'] == 'TIDAK_SERIUS' 
                assert res_data['data']['pothole_count'] == 1

    def test_create_post_no_potholes(self, client, auth_headers):
        """Test creating post where no potholes are detected"""
        from unittest.mock import MagicMock, patch
        import numpy as np
        
        # Mock YOLO model response NO detection
        mock_yolo_response = MagicMock()
        mock_yolo_response.boxes = [] 
        
        mock_model = MagicMock()
        mock_model.predict.return_value = [mock_yolo_response]
        
        fake_img = np.zeros((100, 100, 3), dtype=np.uint8)
        
        with patch('routes.posts.yolo_model', mock_model):
            with patch('cv2.imdecode', return_value=fake_img):
                data = {
                    'image': (io.BytesIO(b"fakeimagecontent"), 'test_image.jpg'),
                    'latitude': -6.2,
                    'longitude': 106.8
                }
                
                response = client.post(
                    '/api/upload', 
                    data=data, 
                    content_type='multipart/form-data',
                    headers=auth_headers
                )
                
                # Should be Not Acceptable (406)
                assert response.status_code == 406
                assert response.get_json()['message'] == 'Tidak terdeteksi lubang'

    def test_create_post_no_file(self, client, auth_headers):
        """Test creating post without file"""
        response = client.post(
            '/api/upload', 
            data={'latitude': 0, 'longitude': 0}, 
            headers=auth_headers
        )
        assert response.status_code == 400

