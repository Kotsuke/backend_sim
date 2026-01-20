
import pytest
import jwt
from datetime import datetime, timedelta, timezone
from flask import jsonify
from utils.decorators import token_required
from models import User

class TestDecorators:
    
    def test_token_required_no_header(self, app):
        """Test missing Authorization header"""
        
        @token_required
        def dummy_route(current_user):
            return "OK"
            
        with app.test_request_context('/'):
            response, status_code = dummy_route()
            assert status_code == 401
            assert response.get_json()['error'] == 'Token tidak ditemukan'

    def test_token_required_malformed_header(self, app):
        """Test malformed Authorization header"""
        
        @token_required
        def dummy_route(current_user):
            return "OK"
            
        # Example: just "Bearer" without token, or wrong format check depends on split
        # Code: token = request.headers['Authorization'].split(" ")[1]
        # Should fail if split doesn't have index 1
        
        with app.test_request_context('/', headers={'Authorization': 'Bearer'}):
            response, status_code = dummy_route()
            assert status_code == 401
            assert response.get_json()['error'] == 'Format token salah'

    def test_token_required_expired_token(self, app):
        """Test expired token"""
        
        @token_required
        def dummy_route(current_user):
            return "OK"
            
        # Generate expired token
        expired_token = jwt.encode({
            'user_id': 1,
            'exp': datetime.now(timezone.utc) - timedelta(hours=1)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        with app.test_request_context('/', headers={'Authorization': f'Bearer {expired_token}'}):
            response, status_code = dummy_route()
            assert status_code == 401
            # Code line 34: return jsonify({'error': 'Token kadaluarsa'}), 401
            assert response.get_json()['error'] == 'Token kadaluarsa'

    def test_token_required_invalid_token(self, app):
        """Test invalid token signature/garbage"""
        
        @token_required
        def dummy_route(current_user):
            return "OK"
            
        with app.test_request_context('/', headers={'Authorization': 'Bearer garbage.token.here'}):
            response, status_code = dummy_route()
            assert status_code == 401
            # Code line 36: return jsonify({'error': 'Token tidak valid'}), 401
            assert response.get_json()['error'] == 'Token tidak valid'

    def test_token_required_user_not_found(self, app):
        """Test valid token but user does not exist in DB"""
        
        @token_required
        def dummy_route(current_user):
            return "OK"
            
        # Token for ID 99999
        token = jwt.encode({
            'user_id': 99999,
            'exp': datetime.now(timezone.utc) + timedelta(hours=1)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        with app.test_request_context('/', headers={'Authorization': f'Bearer {token}'}):
            response, status_code = dummy_route()
            assert status_code == 401
            # Code line 32: return jsonify({'error': 'User tidak valid'}), 401
            assert response.get_json()['error'] == 'User tidak valid'
            
    def test_token_required_success(self, app, sample_user):
        """Test successful token auth via unit test way"""
        
        @token_required
        def dummy_route(current_user):
            return f"Hello {current_user.username}"
            
        # Generate valid token
        token = jwt.encode({
            'user_id': sample_user.id,
            'exp': datetime.now(timezone.utc) + timedelta(hours=1)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        with app.test_request_context('/', headers={'Authorization': f'Bearer {token}'}):
            result = dummy_route()
            assert result == "Hello testuser"
