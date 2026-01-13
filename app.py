import os
import cv2
import numpy as np
import jwt

from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask_cors import CORS
from inference_sdk import InferenceHTTPClient

from config import Config
from models import db, Post, PostVerification, User, UserRole, VerificationType, Review, PostStatus
import sys

# =========================
# CHATBOT SETUP
# =========================
# Tambahkan folder chatbotboti-main ke path agar bisa import module-nya
sys.path.append(os.path.join(os.path.dirname(__file__), 'chatbotboti-main'))

chatbot = None
try:
    from chatbot_model import SIMChatbot
    # Inisialisasi chatbot (load model mungkin butuh waktu & RAM)
    # Gunakan try-except agar app tetap jalan meski model belum ada
    chatbot = SIMChatbot()
    print("✅ Chatbot loaded successfully")
except Exception as e:
    print(f"⚠️ Chatbot failed to load: {e}")
    chatbot = None

# =========================
# APP INIT
# =========================
app = Flask(__name__)
CORS(app)
app.config.from_object(Config)
app.config['SECRET_KEY'] = 'secret_key_skripsi_smartinfra'

db.init_app(app)

# =========================
# ROBOFLOW CONFIG
# =========================
ROBOFLOW_API_KEY = os.environ.get("ROBOFLOW_API_KEY")
MODEL_ID = os.environ.get("ROBOFLOW_MODEL_ID", "pothole-detection-bqu6s-ztwh1/1")

if not ROBOFLOW_API_KEY:
    print("⚠️ ROBOFLOW_API_KEY not found in environment variables. Post detection might fail.")

CLIENT = InferenceHTTPClient(
    api_url="https://serverless.roboflow.com",
    api_key=ROBOFLOW_API_KEY
)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# =========================
# JWT DECORATOR
# =========================
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'Authorization' in request.headers:
            try:
                token = request.headers['Authorization'].split(" ")[1]
            except:
                return jsonify({'error': 'Format token salah'}), 401

        if not token:
            return jsonify({'error': 'Token tidak ditemukan'}), 401

        try:
            data = jwt.decode(
                token,
                app.config['SECRET_KEY'],
                algorithms=['HS256']
            )
            current_user = User.query.get(data['user_id'])
            if not current_user:
                return jsonify({'error': 'User tidak valid'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token kadaluarsa'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token tidak valid'}), 401

        return f(current_user, *args, **kwargs)

    return decorated

# =========================
# HELPER AI
# =========================
def analyze_severity(results, img_w, img_h):
    # Ambil prediksi dari Roboflow
    raw_preds = results.get('predictions', [])
    
    # 1. FILTER CONFIDENCE
    # Hanya ambil prediksi yang confidence-nya > 40% (0.4)
    # Ini membantu membuang deteksi "sampah" atau noise
    preds = [p for p in raw_preds if p.get('confidence', 0) > 0.4]
    
    count = len(preds)

    if count == 0:
        return "AMAN", 0

    serious = False
    img_area = img_w * img_h

    for p in preds:
        box = p.get('width', 0) * p.get('height', 0)
        ratio = box / img_area
        
        # 2. LOGIKA UKURAN (AREA)
        # Sebelumnya 0.02 (2%), sekarang dinaikkan ke 0.035 (3.5%)
        # Agar jika user foto agak dekat, retakan kecil tidak langsung dianggap SERIUS
        if ratio > 0.035:
            serious = True
            break

    # 3. LOGIKA JUMLAH
    # Sebelumnya > 3, sekarang > 4.
    # Jika ada lebih dari 4 lubang kecil-kecil -> SERIUS (Jalan Hancur)
    # ATAU jika ada 1 lubang besar (serious=True) -> SERIUS
    if count > 4 or serious:
        status = "SERIUS"
    else:
        status = "TIDAK_SERIUS"

    return status, count

# =========================
# AUTH
# =========================
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json

    if not all(k in data for k in ('username', 'email', 'password', 'full_name')):
        return jsonify({'error': 'Data tidak lengkap'}), 400

    if User.query.filter(
        (User.username == data['username']) |
        (User.email == data['email'])
    ).first():
        return jsonify({'error': 'Username atau Email sudah terpakai'}), 400

    user = User(
        username=data['username'],
        email=data['email'],
        full_name=data['full_name'],
        phone=data.get('phone', ''),
        bio=data.get('bio', 'Pengguna baru')
    )
    user.set_password(data['password'])

    db.session.add(user)
    db.session.commit()

    return jsonify({'message': 'Registrasi berhasil', 'user': user.to_dict()}), 201


@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data.get('username')).first()

    if not user or not user.check_password(data.get('password')):
        return jsonify({'error': 'Username atau password salah'}), 401

    token = jwt.encode({
        'user_id': user.id,
        'role': user.role.value,
        'exp': datetime.now(timezone.utc) + timedelta(hours=6)
    }, app.config['SECRET_KEY'], algorithm='HS256')

    return jsonify({
        'message': 'Login berhasil',
        'token': token,
        'user': user.to_dict()
    })


# =========================
# GOOGLE SIGN-IN
# =========================
@app.route('/api/google-login', methods=['POST'])
def google_login():
    """
    Endpoint untuk login via Google Sign-In.
    Menerima data dari frontend Flutter:
    - email: Email dari Google account
    - name: Display name dari Google account  
    - google_id: Unique ID dari Google account
    """
    data = request.json

    # Validasi data yang diterima
    if not all(k in data for k in ('email', 'name', 'google_id')):
        return jsonify({'error': 'Data Google tidak lengkap'}), 400

    email = data['email']
    name = data['name']
    google_id = data['google_id']

    # Cek apakah user dengan email ini sudah ada
    user = User.query.filter_by(email=email).first()

    if user:
        # User sudah ada, langsung login
        pass
    else:
        # User baru, buat akun otomatis
        # Generate username dari email (bagian sebelum @)
        base_username = email.split('@')[0]
        username = base_username
        
        # Pastikan username unik
        counter = 1
        while User.query.filter_by(username=username).first():
            username = f"{base_username}{counter}"
            counter += 1

        # Buat user baru dengan password random (tidak akan digunakan karena login via Google)
        import secrets
        random_password = secrets.token_hex(16)

        user = User(
            username=username,
            email=email,
            full_name=name,
            phone='',
            bio='Login via Google'
        )
        user.set_password(random_password)

        db.session.add(user)
        db.session.commit()

    # Generate JWT token
    token = jwt.encode({
        'user_id': user.id,
        'role': user.role.value,
        'exp': datetime.now(timezone.utc) + timedelta(hours=6)
    }, app.config['SECRET_KEY'], algorithm='HS256')

    return jsonify({
        'message': 'Login Google berhasil',
        'token': token,
        'user': user.to_dict()
    })

# =========================
# USER PROFILE
# =========================
@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user_profile(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict())


@app.route('/api/users/<int:user_id>', methods=['PUT'])
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


@app.route('/api/users/<int:user_id>', methods=['DELETE'])
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
        if os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], p.image_path)):
            try:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], p.image_path))
            except:
                pass
    
    Post.query.filter_by(user_id=user_id).delete()
    Review.query.filter_by(user_id=user_id).delete() # Tambahan cleanup review
    
    # CRITICAL FIX: Hapus user yang TEPAT (sesuai user_id), BUKAN current_user (admin)
    user_to_delete = User.query.get_or_404(user_id)
    db.session.delete(user_to_delete)
    db.session.commit()

    return jsonify({'message': 'Akun dihapus'})

# =========================
# POST (UPLOAD + AI)
# =========================
@app.route('/api/upload', methods=['POST'])
@token_required
def upload_post(current_user):
    # Validasi NIK - User harus memiliki NIK untuk bisa upload
    if current_user.nik is None:
        return jsonify({'error': 'Anda harus memasukkan NIK terlebih dahulu untuk menggunakan fitur ini'}), 403
    
    if 'image' not in request.files:
        return jsonify({'error': 'Wajib upload gambar'}), 400

    lat = request.form.get('latitude')
    lng = request.form.get('longitude')
    address = request.form.get('address', 'Tidak diketahui')

    file = request.files['image']
    file_bytes = np.frombuffer(file.read(), np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

    if img is None:
        return jsonify({'error': 'File tidak valid'}), 400

    h, w, _ = img.shape
    results = CLIENT.infer(img, model_id=MODEL_ID)
    severity, count = analyze_severity(results, w, h)

    if count == 0:
        return jsonify({'message': 'Tidak terdeteksi lubang'}), 406

    filename = secure_filename(f"{int(datetime.now().timestamp())}_{current_user.id}.jpg")
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    with open(path, 'wb') as f:
        f.write(file_bytes)

    post = Post(
        user_id=current_user.id,
        image_path=filename,
        latitude=float(lat),
        longitude=float(lng),
        address=address,
        pothole_count=count,
        severity=severity,
        caption=f"Terdeteksi {count} lubang ({severity})"
    )

    current_user.points += 10
    db.session.add(post)
    db.session.commit()

    return jsonify({'message': 'Upload berhasil', 'data': post.to_dict()})

# =========================
# FEED & VERIFICATION
# =========================
@app.route('/api/posts', methods=['GET'])
def get_posts():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return jsonify([p.to_dict() for p in posts])


@app.route('/api/posts/<int:post_id>/verify', methods=['POST'])
@token_required
def verify_post(current_user, post_id):
    # Validasi NIK - User harus memiliki NIK untuk bisa memberikan vote
    if current_user.nik is None:
        return jsonify({'error': 'Anda harus memasukkan NIK terlebih dahulu untuk menggunakan fitur ini'}), 403
    
    post = Post.query.get_or_404(post_id)
    vtype = request.json.get('type')

    action = VerificationType.CONFIRM if vtype == 'CONFIRM' else VerificationType.FALSE
    existing = PostVerification.query.filter_by(
        post_id=post_id,
        user_id=current_user.id
    ).first()

    if existing:
        existing.verification_type = action
    else:
        db.session.add(PostVerification(
            post_id=post_id,
            user_id=current_user.id,
            verification_type=action
        ))

    db.session.commit()

    # --- UPDATE POLLING COUNTS ---
    # Hitung ulang jumlah vote agar data di tabel Post selalu update
    c_count = PostVerification.query.filter_by(post_id=post_id, verification_type=VerificationType.CONFIRM).count()
    f_count = PostVerification.query.filter_by(post_id=post_id, verification_type=VerificationType.FALSE).count()

    post.confirm_count = c_count
    post.false_count = f_count
    db.session.commit()

    return jsonify({
        'message': 'Verifikasi disimpan',
        'data': {
            'valid': c_count,
            'false': f_count
        }
    })

# =========================
# ADMIN ENDPOINTS
# =========================
# ... (imports)
from sentiment_service import init_analyzer, predict_sentiment

# ... (existing code)

# =========================
# ADMIN ENDPOINTS
# =========================
@app.route('/api/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    """Statistik untuk dashboard admin"""
    total_posts = Post.query.count()
    total_users = User.query.count()
    serious_damage = Post.query.filter_by(severity='SERIUS').count()
    
    # Hitung ulasan rata-rata
    from sqlalchemy import func
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

@app.route('/api/dashboard/growth', methods=['GET'])
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

def check_and_migrate_db():
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
        
        # 2. Cek users.nik
        if 'nik' not in user_cols:
            print("⚠️ Column 'nik' missing in 'users', migrating...")
            try:
                db.session.execute(text("ALTER TABLE users ADD COLUMN nik BIGINT UNIQUE"))
                db.session.commit()
                print("✅ Migration: Added 'nik' to 'users'")
            except Exception as e:
                print(f"❌ Migration failed: {e}")

        # 3. Cek reviews.sentiment
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
        
        # 4. Cek posts.status
        if 'posts' in inspector.get_table_names():
            post_cols = [c['name'] for c in inspector.get_columns('posts')]
            if 'status' not in post_cols:
                print("⚠️ Column 'status' missing in 'posts', migrating...")
                try:
                    db.session.execute(text("ALTER TABLE posts ADD COLUMN status VARCHAR(20) DEFAULT 'waiting'"))
                    db.session.commit()
                    print("✅ Migration: Added 'status' to 'posts'")
                except Exception as e:
                    print(f"❌ Migration failed: {e}")

@app.route('/api/users', methods=['GET'])
def get_all_users():
    """Daftar semua user untuk admin"""
    users = User.query.all()
    return jsonify([u.to_dict() for u in users])

@app.route('/api/admin/users', methods=['POST'])
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
    
    # Cek NIK jika disediakan
    nik = data.get('nik')
    if nik is not None:
        existing_nik = User.query.filter(User.nik == int(nik)).first()
        if existing_nik:
            return jsonify({'error': 'NIK sudah digunakan oleh user lain'}), 400
    
    user = User(
        username=data['username'],
        email=data['email'],
        full_name=data['full_name'],
        phone=data.get('phone', ''),
        bio=data.get('bio', 'Dibuat oleh Admin'),
        points=int(data.get('points', 0)),
        nik=int(nik) if nik else None
    )
    user.set_password(data['password'])
    
    if data.get('role') == 'admin':
        user.role = UserRole.ADMIN
    elif data.get('role') == 'moderator':
        user.role = UserRole.MODERATOR
    else:
        user.role = UserRole.USER
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({'message': 'User berhasil dibuat', 'user': user.to_dict()}), 201

@app.route('/api/posts/<int:post_id>', methods=['DELETE'])
@token_required
def delete_post(current_user, post_id):
    post = Post.query.get_or_404(post_id)
    if current_user.role != UserRole.ADMIN and current_user.id != post.user_id:
        return jsonify({'error': 'Akses ditolak'}), 403
    
    PostVerification.query.filter_by(post_id=post_id).delete()
    import os
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], post.image_path)
    if os.path.exists(image_path):
        os.remove(image_path)
    
    db.session.delete(post)
    db.session.commit()
    return jsonify({'message': 'Laporan berhasil dihapus'})

@app.route('/api/admin/users/<int:user_id>', methods=['PUT'])
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
        if data['role'] == 'admin':
            user.role = UserRole.ADMIN
        elif data['role'] == 'moderator':
            user.role = UserRole.MODERATOR
        else:
            user.role = UserRole.USER
    if 'password' in data and data['password']:
        user.set_password(data['password'])
    if 'points' in data: user.points = int(data['points'])
    if 'nik' in data:
        if data['nik'] is not None:
            # Cek apakah NIK sudah digunakan user lain
            existing_nik = User.query.filter(User.nik == data['nik'], User.id != user_id).first()
            if existing_nik:
                return jsonify({'error': 'NIK sudah digunakan oleh user lain'}), 400
            user.nik = int(data['nik'])
        else:
            user.nik = None
    
    db.session.commit()
    return jsonify({'message': 'User berhasil diperbarui', 'user': user.to_dict()})

# =========================
# USER UPDATE NIK
# =========================
@app.route('/api/users/<int:user_id>/nik', methods=['PUT'])
@token_required
def update_user_nik(current_user, user_id):
    """User dapat mengupdate NIK mereka sendiri"""
    if current_user.id != user_id:
        return jsonify({'error': 'Anda hanya dapat mengupdate NIK akun sendiri'}), 403
    
    data = request.json
    nik = data.get('nik')
    
    if nik is None:
        return jsonify({'error': 'NIK wajib diisi'}), 400
    
    try:
        nik = int(nik)
    except (ValueError, TypeError):
        return jsonify({'error': 'NIK harus berupa angka'}), 400
    
    # Validasi panjang NIK (16 digit untuk Indonesia)
    if len(str(nik)) != 16:
        return jsonify({'error': 'NIK harus 16 digit'}), 400
    
    # Cek apakah NIK sudah digunakan user lain
    existing_nik = User.query.filter(User.nik == nik, User.id != user_id).first()
    if existing_nik:
        return jsonify({'error': 'NIK sudah digunakan oleh akun lain'}), 400
    
    current_user.nik = nik
    db.session.commit()
    
    return jsonify({'message': 'NIK berhasil diperbarui', 'user': current_user.to_dict()})

# =========================
# MODERATOR UPDATE POST STATUS
# =========================
@app.route('/api/posts/<int:post_id>/status', methods=['PUT'])
@token_required
def update_post_status(current_user, post_id):
    """Moderator atau Admin dapat mengubah status post"""
    # Cek apakah user adalah moderator atau admin
    if current_user.role not in [UserRole.MODERATOR, UserRole.ADMIN]:
        return jsonify({'error': 'Akses ditolak. Hanya moderator atau admin yang dapat mengubah status.'}), 403
    
    post = Post.query.get_or_404(post_id)
    data = request.json
    new_status = data.get('status')
    
    if not new_status:
        return jsonify({'error': 'Status wajib diisi'}), 400
    
    # Validasi status yang valid
    valid_statuses = ['waiting', 'processing', 'finished']
    if new_status.lower() not in valid_statuses:
        return jsonify({'error': f'Status tidak valid. Gunakan salah satu dari: {valid_statuses}'}), 400
    
    # Set status baru
    if new_status.lower() == 'waiting':
        post.status = PostStatus.WAITING
    elif new_status.lower() == 'processing':
        post.status = PostStatus.PROCESSING
    elif new_status.lower() == 'finished':
        post.status = PostStatus.FINISHED
    
    db.session.commit()
    
    return jsonify({
        'message': f'Status post berhasil diubah menjadi {new_status}',
        'data': post.to_dict()
    })

## =========================
# CHATBOT ROUTE
# =========================
@app.route('/api/chat', methods=['POST'])
@token_required
def chat_with_bot(current_user):
    if not chatbot:
        return jsonify({'error': 'Chatbot sedang tidak aktif (Model belum dimuat)'}), 503

    data = request.json
    question = data.get('message')

    if not question:
        return jsonify({'error': 'Pesan (message) wajib diisi'}), 400

    try:
        # Panggil fungsi chat dari SIMChatbot
        answer = chatbot.chat(question)
        return jsonify({'answer': answer})
    except Exception as e:
        print(f"Chat Error: {e}")
        return jsonify({'error': 'Terjadi kesalahan pada chatbot'}), 500
        
# =========================
# REVIEWS
# =========================
@app.route('/api/reviews', methods=['POST'])
@token_required
def create_review(current_user):
    # Validasi NIK - User harus memiliki NIK untuk bisa submit review
    if current_user.nik is None:
        return jsonify({'error': 'Anda harus memasukkan NIK terlebih dahulu untuk menggunakan fitur ini'}), 403
    
    data = request.json
    rating = data.get('rating')
    comment = data.get('comment')

    if not rating or not isinstance(rating, int) or not (1 <= rating <= 5):
        return jsonify({'error': 'Rating harus berupa angka 1-5'}), 400

    # Analisis Sentimen Otomatis
    sentiment = None
    if comment:
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

@app.route('/api/reviews', methods=['GET'])
def get_reviews():
    reviews = Review.query.order_by(Review.created_at.desc()).all()
    
    # Lazy Analysis: Analisis sentimen untuk review yang belum punya label
    updated = False
    for r in reviews:
        if r.comment and r.sentiment is None:
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

@app.route('/api/reviews/<int:review_id>', methods=['DELETE'])
@token_required
def delete_review(current_user, review_id):
    if current_user.role != UserRole.ADMIN:
        return jsonify({'error': 'Akses ditolak'}), 403

    review = Review.query.get_or_404(review_id)
    db.session.delete(review)
    db.session.commit()
    return jsonify({'message': 'Review berhasil dihapus'})

# =========================
# STATIC FILE
# =========================
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# =========================
# RUN
# =========================
if __name__ == '__main__':
    # Init Sentiment Analyzer
    init_analyzer(app.config['BASE_DIR'])
    
    check_and_migrate_db()
    app.run(host='0.0.0.0', port=5000, debug=True)

