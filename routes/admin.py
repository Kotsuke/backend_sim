"""
Admin Routes - Dashboard Stats, User Management, DB Migration
"""
from flask import Blueprint, request, jsonify
from sqlalchemy import func
from models import db, User, UserRole, Post, Review
from utils.decorators import token_required

admin_bp = Blueprint('admin', __name__)


# =========================
# DASHBOARD STATS
# =========================
@admin_bp.route('/api/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    """Statistik untuk dashboard admin"""
    total_posts = Post.query.count()
    total_users = User.query.count()
    serious_damage = Post.query.filter_by(severity='SERIUS').count()
    
    # Hitung ulasan rata-rata
    avg_rating = db.session.query(func.avg(Review.rating)).scalar()
    avg_rating = round(avg_rating, 1) if avg_rating else 0.0

    # Hitung Sentimen
    positive_reviews = Review.query.filter_by(sentiment='positif').count()
    negative_reviews = Review.query.filter_by(sentiment='negatif').count()

    return jsonify({
        'total_posts': total_posts,
        'total_users': total_users,
        'serious_damage': serious_damage,
        'average_rating': avg_rating,
        'sentiment': {
            'positive': positive_reviews,
            'negative': negative_reviews
        }
    })


# =========================
# GROWTH STATS (FOR CHARTS)
# =========================
@admin_bp.route('/api/dashboard/growth', methods=['GET'])
def get_growth_stats():
    """Mengembalikan data timestamp untuk grafik pertumbuhan"""
    users = db.session.query(User.created_at).all()
    posts = db.session.query(Post.created_at).all()
    
    user_dates = [u.created_at.isoformat() for u in users if u.created_at]
    post_dates = [p.created_at.isoformat() for p in posts if p.created_at]
    
    return jsonify({
        'users': user_dates,
        'posts': post_dates
    })


# =========================
# CREATE USER (ADMIN ONLY)
# =========================
@admin_bp.route('/api/admin/users', methods=['POST'])
@token_required
def admin_create_user(current_user):
    """Admin dapat membuat akun user baru"""
    if current_user.role != UserRole.ADMIN:
        return jsonify({'error': 'Akses ditolak. Hanya admin yang bisa membuat user.'}), 403
    
    data = request.json
    if not all(k in data for k in ('username', 'email', 'password', 'full_name')):
        return jsonify({'error': 'Data tidak lengkap.'}), 400
    
    if User.query.filter((User.username == data['username']) | (User.email == data['email'])).first():
        return jsonify({'error': 'Username atau Email sudah terpakai'}), 400
    
    user = User(
        username=data['username'],
        email=data['email'],
        full_name=data['full_name'],
        phone=data.get('phone', ''),
        bio=data.get('bio', 'Dibuat oleh Admin'),
        points=int(data.get('points', 0))
    )
    user.set_password(data['password'])
    
    # Set role berdasarkan input
    role_input = data.get('role', 'user').lower()
    if role_input == 'admin':
        user.role = UserRole.ADMIN
    elif role_input == 'petugas':
        user.role = UserRole.PETUGAS
    else:
        user.role = UserRole.USER
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({'message': 'User berhasil dibuat', 'user': user.to_dict()}), 201


# =========================
# UPDATE USER (ADMIN ONLY)
# =========================
@admin_bp.route('/api/admin/users/<int:user_id>', methods=['PUT'])
@token_required
def admin_update_user(current_user, user_id):
    if current_user.role != UserRole.ADMIN:
        return jsonify({'error': 'Akses ditolak'}), 403
    
    user = User.query.get_or_404(user_id)
    data = request.json
    
    if 'full_name' in data: user.full_name = data['full_name']
    if 'email' in data:
        existing = User.query.filter(User.email == data['email'], User.id != user_id).first()
        if existing: return jsonify({'error': 'Email sudah digunakan'}), 400
        user.email = data['email']
    if 'username' in data:
        existing = User.query.filter(User.username == data['username'], User.id != user_id).first()
        if existing: return jsonify({'error': 'Username sudah digunakan'}), 400
        user.username = data['username']
    if 'phone' in data: user.phone = data['phone']
    if 'bio' in data: user.bio = data['bio']
    if 'role' in data:
        role_input = data['role'].lower()
        if role_input == 'admin':
            user.role = UserRole.ADMIN
        elif role_input == 'petugas':
            user.role = UserRole.PETUGAS
        else:
            user.role = UserRole.USER
    if 'password' in data and data['password']:
        user.set_password(data['password'])
    if 'points' in data: user.points = int(data['points'])
    
    db.session.commit()
    return jsonify({'message': 'User berhasil diperbarui', 'user': user.to_dict()})


# =========================
# DATABASE MIGRATION
# =========================
def check_and_migrate_db(app):
    """Cek dan update schema database jika diperlukan"""
    from sqlalchemy import text, inspect
    
    with app.app_context():
        inspector = inspect(db.engine)
        
        # 1. Cek users.created_at
        user_cols = [c['name'] for c in inspector.get_columns('users')]
        if 'created_at' not in user_cols:
            print("⚠️ Column 'created_at' missing in 'users', migrating...")
            try:
                db.session.execute(text("ALTER TABLE users ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP"))
                db.session.commit()
                print("✅ Migration: Added 'created_at' to 'users'")
            except Exception as e:
                print(f"❌ Migration failed: {e}")

        # 2. Cek reviews.sentiment
        if 'reviews' in inspector.get_table_names():
            review_cols = [c['name'] for c in inspector.get_columns('reviews')]
            if 'sentiment' not in review_cols:
                print("⚠️ Column 'sentiment' missing in 'reviews', migrating...")
                try:
                    db.session.execute(text("ALTER TABLE reviews ADD COLUMN sentiment VARCHAR(20)"))
                    db.session.commit()
                    print("✅ Migration: Added 'sentiment' to 'reviews'")
                except Exception as e:
                    print(f"❌ Migration failed: {e}")

        # 3. Cek posts columns
        if 'posts' in inspector.get_table_names():
            post_cols = [c['name'] for c in inspector.get_columns('posts')]
            
            if 'status' not in post_cols:
                print("⚠️ Column 'status' missing in 'posts', migrating...")
                try:
                    db.session.execute(text("ALTER TABLE posts ADD COLUMN status VARCHAR(20) DEFAULT 'menunggu'"))
                    db.session.commit()
                    print("✅ Migration: Added 'status' to 'posts'")
                except Exception as e:
                    print(f"❌ Migration failed: {e}")
            
            # 4. Cek posts.province, posts.city, posts.district
            if 'province' not in post_cols:
                print("⚠️ Column 'province' missing in 'posts', migrating...")
                try:
                    db.session.execute(text("ALTER TABLE posts ADD COLUMN province VARCHAR(100)"))
                    db.session.commit()
                    print("✅ Migration: Added 'province' to 'posts'")
                except Exception as e:
                    print(f"❌ Migration failed: {e}")
            
            if 'city' not in post_cols:
                print("⚠️ Column 'city' missing in 'posts', migrating...")
                try:
                    db.session.execute(text("ALTER TABLE posts ADD COLUMN city VARCHAR(100)"))
                    db.session.commit()
                    print("✅ Migration: Added 'city' to 'posts'")
                except Exception as e:
                    print(f"❌ Migration failed: {e}")
            
            if 'district' not in post_cols:
                print("⚠️ Column 'district' missing in 'posts', migrating...")
                try:
                    db.session.execute(text("ALTER TABLE posts ADD COLUMN district VARCHAR(100)"))
                    db.session.commit()
                    print("✅ Migration: Added 'district' to 'posts'")
                except Exception as e:
                    print(f"❌ Migration failed: {e}")
