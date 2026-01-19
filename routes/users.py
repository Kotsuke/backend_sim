"""
User Routes - Profile, User Management
"""
import os
from flask import Blueprint, request, jsonify, current_app
from models import db, User, UserRole, Post, PostVerification, Review
from utils.decorators import token_required

users_bp = Blueprint('users', __name__)


# =========================
# GET USER PROFILE
# =========================
@users_bp.route('/api/users/<int:user_id>', methods=['GET'])
def get_user_profile(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict())


# =========================
# UPDATE PROFILE
# =========================
@users_bp.route('/api/users/<int:user_id>', methods=['PUT'])
@token_required
def update_profile(current_user, user_id):
    if current_user.id != user_id:
        return jsonify({'error': 'Akses ditolak'}), 403

    data = request.json
    if 'full_name' in data: current_user.full_name = data['full_name']
    if 'phone' in data: current_user.phone = data['phone']
    if 'bio' in data: current_user.bio = data['bio']
    
    # Update password jika dikirim dan tidak kosong
    if 'password' in data and data['password']:
        if len(data['password']) >= 6:
            current_user.set_password(data['password'])
        else:
            return jsonify({'error': 'Password minimal 6 karakter'}), 400

    db.session.commit()
    return jsonify({'message': 'Profil diperbarui', 'user': current_user.to_dict()})


# =========================
# DELETE USER
# =========================
@users_bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@token_required
def delete_user(current_user, user_id):
    # Proteksi: Admin tidak boleh menghapus dirinya sendiri
    if current_user.id == user_id:
        return jsonify({'error': 'Anda tidak dapat menghapus akun sendiri saat sedang login'}), 400

    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        return jsonify({'error': 'Akses ditolak'}), 403

    # Cleanup data user manual (untuk safety jika cascade gagal/tidak kena)
    PostVerification.query.filter_by(user_id=user_id).delete()
    
    # Hapus file gambar post user ini
    user_posts = Post.query.filter_by(user_id=user_id).all()
    for p in user_posts:
        if os.path.exists(os.path.join(current_app.config['UPLOAD_FOLDER'], p.image_path)):
            try:
                os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], p.image_path))
            except:
                pass
    
    Post.query.filter_by(user_id=user_id).delete()
    Review.query.filter_by(user_id=user_id).delete()
    
    # CRITICAL FIX: Hapus user yang TEPAT (sesuai user_id), BUKAN current_user (admin)
    user_to_delete = User.query.get_or_404(user_id)
    db.session.delete(user_to_delete)
    db.session.commit()

    return jsonify({'message': 'Akun dihapus'})


# =========================
# GET ALL USERS (ADMIN)
# =========================
@users_bp.route('/api/users', methods=['GET'])
def get_all_users():
    """Daftar semua user untuk admin"""
    users = User.query.all()
    return jsonify([u.to_dict() for u in users])
