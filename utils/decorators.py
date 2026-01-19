"""
JWT Token Decorator untuk autentikasi
"""
import jwt
from functools import wraps
from flask import request, jsonify, current_app
from models import User


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
                current_app.config['SECRET_KEY'],
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
