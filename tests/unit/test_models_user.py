"""
Unit tests for User model
"""
import pytest
from models import User, UserRole


@pytest.mark.unit
class TestUserModel:
    """Test cases for User model"""
    
    def test_create_user(self, db_session):
        """Test creating a new user"""
        user = User(
            username='newuser',
            email='newuser@example.com',
            full_name='New User',
            role=UserRole.USER
        )
        user.set_password('password123')
        
        db_session.add(user)
        db_session.commit()
        
        assert user.id is not None
        assert user.username == 'newuser'
        assert user.email == 'newuser@example.com'
        assert user.role == UserRole.USER
        assert user.points == 0  # Default value
    
    def test_password_hashing(self, db_session):
        """Test password hashing and verification"""
        user = User(
            username='testuser',
            email='test@example.com',
            full_name='Test User'
        )
        user.set_password('mypassword')
        
        # Password should be hashed
        assert user.password_hash != 'mypassword'
        
        # Check password should work
        assert user.check_password('mypassword') is True
        assert user.check_password('wrongpassword') is False
    
    def test_user_to_dict(self, sample_user):
        """Test user serialization to dict"""
        user_dict = sample_user.to_dict()
        
        assert user_dict['id'] == sample_user.id
        assert user_dict['username'] == 'testuser'
        assert user_dict['email'] == 'test@example.com'
        assert user_dict['role'] == 'user'
        assert 'password_hash' not in user_dict  # Should not expose password
    
    def test_user_roles(self, db_session):
        """Test different user roles"""
        # Create users with different roles
        user = User(username='user1', email='user1@example.com', full_name='User 1', role=UserRole.USER)
        admin = User(username='admin1', email='admin1@example.com', full_name='Admin 1', role=UserRole.ADMIN)
        petugas = User(username='petugas1', email='petugas1@example.com', full_name='Petugas 1', role=UserRole.PETUGAS)
        
        user.set_password('pass')
        admin.set_password('pass')
        petugas.set_password('pass')
        
        db_session.add_all([user, admin, petugas])
        db_session.commit()
        
        assert user.role == UserRole.USER
        assert admin.role == UserRole.ADMIN
        assert petugas.role == UserRole.PETUGAS
    
    def test_user_unique_constraints(self, db_session, sample_user):
        """Test unique constraints on username and email"""
        # Try to create user with duplicate username
        duplicate_user = User(
            username='testuser',  # Same as sample_user
            email='different@example.com',
            full_name='Different User'
        )
        duplicate_user.set_password('password')
        
        db_session.add(duplicate_user)
        with pytest.raises(Exception):  # Should raise IntegrityError
            db_session.commit()
        
        db_session.rollback()
        
        # Try to create user with duplicate email
        duplicate_email = User(
            username='different',
            email='test@example.com',  # Same as sample_user
            full_name='Different User'
        )
        duplicate_email.set_password('password')
        
        db_session.add(duplicate_email)
        with pytest.raises(Exception):  # Should raise IntegrityError
            db_session.commit()
