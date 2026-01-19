"""
Other Routes - Chatbot, Reviews, Static Files
"""
import os
from flask import Blueprint, request, jsonify, send_from_directory, current_app
from models import db, Review, UserRole
from utils.decorators import token_required

others_bp = Blueprint('others', __name__)

# Chatbot dan sentiment service akan di-inject
chatbot = None
predict_sentiment = None

def set_chatbot(bot):
    """Set chatbot instance dari app.py"""
    global chatbot
    chatbot = bot

def set_sentiment_service(predict_fn):
    """Set sentiment prediction function dari app.py"""
    global predict_sentiment
    predict_sentiment = predict_fn


# =========================
# CHATBOT
# =========================
@others_bp.route('/api/chat', methods=['POST'])
@token_required
def chat_with_bot(current_user):
    global chatbot
    
    if not chatbot:
        return jsonify({'error': 'Chatbot sedang tidak aktif (Model belum dimuat)'}), 503

    data = request.json
    question = data.get('message')

    if not question:
        return jsonify({'error': 'Pesan (message) wajib diisi'}), 400

    try:
        answer = chatbot.chat(question)
        return jsonify({'answer': answer})
    except Exception as e:
        print(f"Chat Error: {e}")
        return jsonify({'error': 'Terjadi kesalahan pada chatbot'}), 500


# =========================
# CREATE REVIEW
# =========================
@others_bp.route('/api/reviews', methods=['POST'])
@token_required
def create_review(current_user):
    global predict_sentiment
    
    data = request.json
    rating = data.get('rating')
    comment = data.get('comment')

    if not rating or not isinstance(rating, int) or not (1 <= rating <= 5):
        return jsonify({'error': 'Rating harus berupa angka 1-5'}), 400

    # Analisis Sentimen Otomatis
    sentiment = None
    if comment and predict_sentiment:
        sentiment = predict_sentiment(comment)

    review = Review(
        user_id=current_user.id,
        rating=rating,
        comment=comment,
        sentiment=sentiment
    )
    db.session.add(review)
    db.session.commit()

    return jsonify({'message': 'Review berhasil dikirim', 'data': review.to_dict()}), 201


# =========================
# GET REVIEWS
# =========================
@others_bp.route('/api/reviews', methods=['GET'])
def get_reviews():
    global predict_sentiment
    
    reviews = Review.query.order_by(Review.created_at.desc()).all()
    
    # Lazy Analysis: Analisis sentimen untuk review yang belum punya label
    updated = False
    for r in reviews:
        if r.comment and r.sentiment is None and predict_sentiment:
            try:
                sentiment = predict_sentiment(r.comment)
                if sentiment:
                    r.sentiment = sentiment
                    updated = True
            except Exception as e:
                print(f"⚠️ Failed to analyze review {r.id}: {e}")
    
    if updated:
        db.session.commit()
    
    return jsonify([r.to_dict() for r in reviews])


# =========================
# DELETE REVIEW
# =========================
@others_bp.route('/api/reviews/<int:review_id>', methods=['DELETE'])
@token_required
def delete_review(current_user, review_id):
    if current_user.role != UserRole.ADMIN:
        return jsonify({'error': 'Akses ditolak'}), 403

    review = Review.query.get_or_404(review_id)
    db.session.delete(review)
    db.session.commit()
    return jsonify({'message': 'Review berhasil dihapus'})


# =========================
# STATIC FILE (UPLOADS)
# =========================
@others_bp.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)
