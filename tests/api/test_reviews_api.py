"""
API tests for reviews endpoints
"""
import pytest


@pytest.mark.api
class TestReviewsAPI:
    """Test cases for reviews API endpoints"""
    
    def test_create_review(self, client, auth_headers):
        """Test creating a new review"""
        response = client.post('/api/reviews', 
            json={
                'rating': 5,
                'comment': 'Great app!'
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert 'message' in data
        # Based on routes/others.py, it returns 'data' key, NOT 'review'
        assert 'data' in data
        assert data['data']['rating'] == 5
    
    def test_create_review_without_auth(self, client):
        """Test creating a review without authentication"""
        response = client.post('/api/reviews', 
            json={
                'rating': 5,
                'comment': 'Great app!'
            }
        )
        
        assert response.status_code == 401
    
    def test_create_review_invalid_rating(self, client, auth_headers):
        """Test creating a review with invalid rating"""
        response = client.post('/api/reviews',
            json={
                'rating': 6,  # Invalid: should be 1-5
                'comment': 'Test'
            },
            headers=auth_headers
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
    
    def test_get_reviews(self, client, sample_review):
        """Test getting all reviews"""
        response = client.get('/api/reviews')
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Based on routes/others.py, it returns a list directly
        assert isinstance(data, list)
        assert len(data) > 0
    
    def test_delete_review_as_admin(self, client, sample_review, admin_headers, db_session):
        """Test deleting a review as admin"""
        review_id = sample_review.id
        
        response = client.delete(f'/api/reviews/{review_id}', headers=admin_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'message' in data
    
    def test_delete_review_as_regular_user(self, client, sample_review, auth_headers):
        """Test deleting a review as regular user (should fail)"""
        review_id = sample_review.id
        
        response = client.delete(f'/api/reviews/{review_id}', headers=auth_headers)
        
        # Regular users should not be able to delete reviews
        assert response.status_code in [403, 401]
    
    def test_review_sentiment_analysis(self, client, auth_headers):
        """Test that sentiment is analyzed for reviews"""
        from unittest.mock import MagicMock, patch
        
        # Mock sentiment predictor
        mock_predictor = MagicMock(return_value='negatif')
        
        # We need to set the global predict_sentiment in routes.others
        with patch('routes.others.predict_sentiment', mock_predictor):
            response = client.post('/api/reviews',
                json={
                    'rating': 1,
                    'comment': 'Aplikasi jelek banget, tidak berguna sama sekali'
                },
                headers=auth_headers
            )
            
            assert response.status_code == 201
            data = response.get_json()
            
            # Check keys
            assert 'data' in data
            assert data['data']['sentiment'] == 'negatif'

    def test_chat_with_bot_success(self, client, auth_headers):
        """Test chat endpoint with successful bot response"""
        from unittest.mock import MagicMock, patch
        
        mock_bot = MagicMock()
        mock_bot.chat.return_value = "Halo, saya bot."
        
        with patch('routes.others.chatbot', mock_bot):
            response = client.post('/api/chat',
                json={'message': 'Halo'},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            assert response.get_json()['answer'] == "Halo, saya bot."
            
    def test_chat_with_bot_inactive(self, client, auth_headers):
        """Test chat endpoint when bot is inactive (None)"""
        from unittest.mock import patch
        
        with patch('routes.others.chatbot', None):
            response = client.post('/api/chat',
                json={'message': 'Halo'},
                headers=auth_headers
            )
            
            assert response.status_code == 503
            
    def test_chat_with_bot_no_message(self, client, auth_headers):
        """Test chat endpoint with empty message"""
        from unittest.mock import MagicMock, patch
        
        mock_bot = MagicMock()
        with patch('routes.others.chatbot', mock_bot):
            response = client.post('/api/chat',
                json={}, # Missing message
                headers=auth_headers
            )
            assert response.status_code == 400

    def test_get_reviews_lazy_analysis(self, client, db_session, sample_user):
        """Test GET /api/reviews triggers lazy sentiment analysis"""
        from unittest.mock import MagicMock, patch
        from models import Review
        
        # Create a review WITHOUT sentiment
        review = Review(
            user_id=sample_user.id,
            rating=5,
            comment="Mantap",
            sentiment=None 
        )
        db_session.add(review)
        db_session.commit()
        
        # Mock predictor
        mock_predictor = MagicMock(return_value='positif')
        
        with patch('routes.others.predict_sentiment', mock_predictor):
            response = client.get('/api/reviews')
            assert response.status_code == 200
            
            # Check DB if updated
            # Need to commit/refresh to see changes? 
            # The route does db.session.commit()
            
            updated_review = db_session.query(Review).get(review.id)
            assert updated_review.sentiment == 'positif'
