"""
Test configuration and fixtures for SmartInfra Backend
Using SQLite in-memory database for isolated testing
"""
import os
import sys
import pytest
from flask import Flask

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models import db, User, Post, Review, PostVerification, UserRole, VerificationType


def create_test_app():
    """Create a fresh Flask app for testing with SQLite."""
    app = Flask(__name__)
    
    # Test configuration - SQLite in-memory
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Use StaticPool to persist in-memory database across connections
    from sqlalchemy.pool import StaticPool
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'connect_args': {'check_same_thread': False},
        'poolclass': StaticPool
    }
    
    app.config['SECRET_KEY'] = 'test_secret_key_for_testing'
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'test_uploads')
    
    # Initialize database with this app
    db.init_app(app)
    
    # Register blueprints
    from routes.auth import auth_bp
    from routes.users import users_bp
    from routes.posts import posts_bp
    from routes.admin import admin_bp
    from routes.others import others_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(posts_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(others_bp)
    
    return app


@pytest.fixture(scope='session')
def app():
    """Create application for the tests."""
    test_app = create_test_app()
    
    # Create upload folder
    os.makedirs(test_app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    with test_app.app_context():
        db.create_all()
        yield test_app
        db.drop_all()
    
    # Cleanup
    if os.path.exists(test_app.config['UPLOAD_FOLDER']):
        import shutil
        shutil.rmtree(test_app.config['UPLOAD_FOLDER'], ignore_errors=True)


@pytest.fixture(scope='function')
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture(scope='function')
def db_session(app):
    """Create a new database session for a test."""
    with app.app_context():
        # Clean all tables
        db.session.remove()
        db.drop_all()
        db.create_all()
        
        yield db.session
        
        # Cleanup
        db.session.remove()


@pytest.fixture
def sample_user(db_session):
    """Create a sample user for testing."""
    user = User(
        username='testuser',
        email='test@example.com',
        full_name='Test User',
        role=UserRole.USER,
        phone='081234567890',
        bio='Test bio',
        points=100
    )
    user.set_password('password123')
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def sample_admin(db_session):
    """Create a sample admin user for testing."""
    admin = User(
        username='admin',
        email='admin@example.com',
        full_name='Admin User',
        role=UserRole.ADMIN,
        phone='081234567891'
    )
    admin.set_password('admin123')
    db_session.add(admin)
    db_session.commit()
    return admin


@pytest.fixture
def sample_petugas(db_session):
    """Create a sample petugas user for testing."""
    petugas = User(
        username='petugas',
        email='petugas@example.com',
        full_name='Petugas User',
        role=UserRole.PETUGAS,
        phone='081234567892'
    )
    petugas.set_password('petugas123')
    db_session.add(petugas)
    db_session.commit()
    return petugas


@pytest.fixture
def sample_post(db_session, sample_user):
    """Create a sample post for testing."""
    post = Post(
        user_id=sample_user.id,
        image_path='test_image.jpg',
        latitude=-6.200000,
        longitude=106.816666,
        address='Jakarta',
        province='DKI Jakarta',
        city='Jakarta Pusat',
        district='Menteng',
        pothole_count=3,
        severity='SERIUS',
        caption='Test pothole',
        status='MENUNGGU'
    )
    db_session.add(post)
    db_session.commit()
    return post


@pytest.fixture
def sample_review(db_session, sample_user):
    """Create a sample review for testing."""
    review = Review(
        user_id=sample_user.id,
        rating=5,
        comment='Great application!',
        sentiment='positif'
    )
    db_session.add(review)
    db_session.commit()
    return review


@pytest.fixture
def auth_headers(client, sample_user):
    """Get authentication headers for a user."""
    response = client.post('/api/login', json={
        'username': 'testuser',
        'password': 'password123'
    })
    data = response.get_json()
    token = data.get('token') if data else None
    return {'Authorization': f'Bearer {token}'} if token else {}


@pytest.fixture
def admin_headers(client, sample_admin):
    """Get authentication headers for an admin."""
    response = client.post('/api/login', json={
        'username': 'admin',
        'password': 'admin123'
    })
    data = response.get_json()
    token = data.get('token') if data else None
    return {'Authorization': f'Bearer {token}'} if token else {}


@pytest.fixture
def petugas_headers(client, sample_petugas):
    """Get authentication headers for a petugas."""
    response = client.post('/api/login', json={
        'username': 'petugas',
        'password': 'petugas123'
    })
    data = response.get_json()
    token = data.get('token') if data else None
    return {'Authorization': f'Bearer {token}'} if token else {}
