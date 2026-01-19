"""
Auth Routes - Login, Register, Google Sign-In
"""
import secrets
import jwt
from datetime import datetime, timedelta, timezone
from flask import Blueprint, request, jsonify, current_app
from models import db, User, UserRole

auth_bp = Blueprint('auth', __name__)


# =========================
# REGISTER
# =========================
@auth_bp.route('/api/register', methods=['POST'])
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


# =========================
# LOGIN
# =========================
@auth_bp.route('/api/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data.get('username')).first()

    if not user or not user.check_password(data.get('password')):
        return jsonify({'error': 'Username atau password salah'}), 401

    token = jwt.encode({
        'user_id': user.id,
        'role': user.role.value,
        'exp': datetime.now(timezone.utc) + timedelta(hours=6)
    }, current_app.config['SECRET_KEY'], algorithm='HS256')

    return jsonify({
        'message': 'Login berhasil',
        'token': token,
        'user': user.to_dict()
    })


# =========================
# GOOGLE SIGN-IN
# =========================
@auth_bp.route('/api/google-login', methods=['POST'])
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
    }, current_app.config['SECRET_KEY'], algorithm='HS256')

    return jsonify({
        'message': 'Login Google berhasil',
        'token': token,
        'user': user.to_dict()
    })
