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
from models import db, Post, PostVerification, User, UserRole, VerificationType
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
CLIENT = InferenceHTTPClient(
    api_url="https://serverless.roboflow.com",
    api_key="i4giE1h6TyTIijfwTuss"
)
MODEL_ID = "pothole-detection-bqu6s-ztwh1/1"

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
    preds = results.get('predictions', [])
    count = len(preds)

    if count == 0:
        return "AMAN", 0

    serious = False
    img_area = img_w * img_h

    for p in preds:
        box = p.get('width', 0) * p.get('height', 0)
        if (box / img_area) > 0.02:
            serious = True
            break

    status = "SERIUS" if (count > 3 or serious) else "TIDAK_SERIUS"
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

    db.session.commit()
    return jsonify({'message': 'Profil diperbarui', 'user': current_user.to_dict()})


@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@token_required
def delete_user(current_user, user_id):
    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        return jsonify({'error': 'Akses ditolak'}), 403

    PostVerification.query.filter_by(user_id=user_id).delete()
    Post.query.filter_by(user_id=user_id).delete()
    db.session.delete(current_user)
    db.session.commit()

    return jsonify({'message': 'Akun dihapus'})

# =========================
# POST (UPLOAD + AI)
# =========================
@app.route('/api/upload', methods=['POST'])
@token_required
def upload_post(current_user):
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
# STATIC FILE
# =========================
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# =========================
# RUN
# =========================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
