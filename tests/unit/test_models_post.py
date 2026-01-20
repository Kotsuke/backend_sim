"""
Unit tests for Post model
"""
import pytest
from models import Post, PostStatus


@pytest.mark.unit
class TestPostModel:
    """Test cases for Post model"""
    
    def test_create_post(self, db_session, sample_user):
        """Test creating a new post"""
        post = Post(
            user_id=sample_user.id,
            image_path='test.jpg',
            latitude=-6.200000,
            longitude=106.816666,
            address='Test Address',
            province='Test Province',
            city='Test City',
            district='Test District',
            pothole_count=2,
            severity='SERIUS',
            caption='Test caption',
            status='MENUNGGU'
        )
        
        db_session.add(post)
        db_session.commit()
        
        assert post.id is not None
        assert post.user_id == sample_user.id
        assert post.pothole_count == 2
        assert post.severity == 'SERIUS'
        assert post.status == 'MENUNGGU'
        assert post.confirm_count == 0  # Default value
        assert post.false_count == 0  # Default value
    
    def test_post_to_dict(self, sample_post, app):
        """Test post serialization to dict"""
        with app.test_request_context():
            post_dict = sample_post.to_dict()
            
            assert post_dict['id'] == sample_post.id
            assert post_dict['user_id'] == sample_post.user_id
            assert post_dict['lat'] == float(sample_post.latitude)
            assert post_dict['long'] == float(sample_post.longitude)
            assert post_dict['pothole_count'] == 3
            assert post_dict['severity'] == 'SERIUS'
            assert post_dict['status'] == 'MENUNGGU'
            assert 'verification' in post_dict
            assert post_dict['verification']['valid'] == 0
            assert post_dict['verification']['false'] == 0
    
    def test_post_relationships(self, db_session, sample_user):
        """Test post relationships with user"""
        post = Post(
            user_id=sample_user.id,
            image_path='test.jpg',
            latitude=-6.200000,
            longitude=106.816666,
            severity='TIDAK_SERIUS',
            caption='Test'
        )
        
        db_session.add(post)
        db_session.commit()
        
        # Test relationship
        assert post.author.username == sample_user.username
        assert post.uploaded_by == sample_user.full_name
    
    def test_post_status_values(self, db_session, sample_user):
        """Test different post status values"""
        posts = []
        statuses = ['MENUNGGU', 'DIPROSES', 'SELESAI']
        
        for status in statuses:
            post = Post(
                user_id=sample_user.id,
                image_path=f'test_{status}.jpg',
                latitude=-6.200000,
                longitude=106.816666,
                severity='SERIUS',
                status=status
            )
            posts.append(post)
        
        db_session.add_all(posts)
        db_session.commit()
        
        for i, status in enumerate(statuses):
            assert posts[i].status == status
    
    def test_post_location_data(self, db_session, sample_user):
        """Test post location data"""
        post = Post(
            user_id=sample_user.id,
            image_path='test.jpg',
            latitude=-6.200000,
            longitude=106.816666,
            address='Jl. Test No. 123',
            province='DKI Jakarta',
            city='Jakarta Selatan',
            district='Kebayoran Baru',
            severity='SERIUS'
        )
        
        db_session.add(post)
        db_session.commit()
        
        assert float(post.latitude) == -6.200000
        assert float(post.longitude) == 106.816666
        assert post.address == 'Jl. Test No. 123'
        assert post.province == 'DKI Jakarta'
        assert post.city == 'Jakarta Selatan'
        assert post.district == 'Kebayoran Baru'
    
    def test_post_verification_counts(self, sample_post, db_session):
        """Test verification counts"""
        # Update verification counts
        sample_post.confirm_count = 10
        sample_post.false_count = 3
        db_session.commit()
        
        assert sample_post.confirm_count == 10
        assert sample_post.false_count == 3
