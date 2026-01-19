"""
Posts Routes - Upload, Feed, Verification, Filter
"""
import os
import cv2
import numpy as np
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from models import db, Post, PostStatus, PostVerification, VerificationType
from utils.decorators import token_required
from utils.ai_helper import analyze_severity

posts_bp = Blueprint('posts', __name__)

# YOLO model akan di-inject dari app.py
yolo_model = None

def set_yolo_model(model):
    """Set YOLO model dari app.py"""
    global yolo_model
    yolo_model = model


# =========================
# UPLOAD POST
# =========================
@posts_bp.route('/api/upload', methods=['POST'])
@token_required
def upload_post(current_user):
    global yolo_model
    
    if 'image' not in request.files:
        return jsonify({'error': 'Wajib upload gambar'}), 400

    lat = request.form.get('latitude')
    lng = request.form.get('longitude')
    address = request.form.get('address', 'Tidak diketahui')
    
    # Data lokasi untuk filter
    province = request.form.get('province', '')
    city = request.form.get('city', '')
    district = request.form.get('district', '')

    # Validasi koordinat
    try:
        lat = float(lat) if lat else None
        lng = float(lng) if lng else None
        if lat is None or lng is None:
            return jsonify({'error': 'Koordinat latitude dan longitude wajib diisi'}), 400
        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            return jsonify({'error': 'Koordinat tidak valid'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Format koordinat tidak valid'}), 400

    file = request.files['image']
    file_bytes = np.frombuffer(file.read(), np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

    if img is None:
        return jsonify({'error': 'File tidak valid'}), 400

    if yolo_model is None:
        return jsonify({'error': 'Model AI tidak tersedia. Silakan hubungi administrator.'}), 503

    h, w, _ = img.shape
    
    # Jalankan inferensi menggunakan model YOLO lokal
    results = yolo_model.predict(source=img, conf=0.4, verbose=False)
    severity, count = analyze_severity(results, w, h)

    if count == 0:
        return jsonify({'message': 'Tidak terdeteksi lubang'}), 406

    filename = secure_filename(f"{int(datetime.now().timestamp())}_{current_user.id}.jpg")
    path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)

    with open(path, 'wb') as f:
        f.write(file_bytes)

    post = Post(
        user_id=current_user.id,
        image_path=filename,
        latitude=lat,
        longitude=lng,
        address=address,
        province=province,
        city=city,
        district=district,
        pothole_count=count,
        severity=severity,
        caption=f"Terdeteksi {count} lubang ({severity})"
    )

    current_user.points += 10
    db.session.add(post)
    db.session.commit()

    return jsonify({'message': 'Upload berhasil', 'data': post.to_dict()})


# =========================
# GET POSTS (FEED)
# =========================
@posts_bp.route('/api/posts', methods=['GET'])
def get_posts():
    """
    Mendapatkan semua posts dengan opsi sorting.
    
    Query params:
    - sort: 'terbaru' (default), 'trending', 'selesai'
    """
    sort_type = request.args.get('sort', 'terbaru').lower()
    
    if sort_type == 'trending':
        posts = Post.query.filter(Post.status != PostStatus.SELESAI)\
            .order_by((Post.confirm_count + Post.false_count).desc(), Post.created_at.desc()).all()
    elif sort_type == 'selesai':
        posts = Post.query.filter_by(status=PostStatus.SELESAI)\
            .order_by(Post.created_at.desc()).all()
    else:
        posts = Post.query.order_by(Post.created_at.desc()).all()
    
    return jsonify([p.to_dict() for p in posts])


# =========================
# GET LOCATIONS (FOR FILTER)
# =========================
@posts_bp.route('/api/posts/locations', methods=['GET'])
def get_posts_locations():
    """
    Mendapatkan daftar unik lokasi (provinsi, kota, kecamatan) dari semua posts.
    Berguna untuk mengisi dropdown filter di map.
    """
    provinces = db.session.query(Post.province).filter(Post.province != None, Post.province != '').distinct().all()
    cities = db.session.query(Post.city).filter(Post.city != None, Post.city != '').distinct().all()
    districts = db.session.query(Post.district).filter(Post.district != None, Post.district != '').distinct().all()
    
    return jsonify({
        'provinces': sorted([p[0] for p in provinces if p[0]]),
        'cities': sorted([c[0] for c in cities if c[0]]),
        'districts': sorted([d[0] for d in districts if d[0]])
    })


# =========================
# FILTER POSTS BY LOCATION
# =========================
@posts_bp.route('/api/posts/filter', methods=['GET'])
def get_posts_by_location():
    """
    Filter posts berdasarkan lokasi.
    
    Query params:
    - province: Filter berdasarkan provinsi
    - city: Filter berdasarkan kota/kabupaten
    - district: Filter berdasarkan kecamatan
    """
    province = request.args.get('province', '').strip()
    city = request.args.get('city', '').strip()
    district = request.args.get('district', '').strip()
    
    query = Post.query
    
    if province:
        query = query.filter(Post.province.ilike(f'%{province}%'))
    if city:
        query = query.filter(Post.city.ilike(f'%{city}%'))
    if district:
        query = query.filter(Post.district.ilike(f'%{district}%'))
    
    posts = query.order_by(Post.created_at.desc()).all()
    
    return jsonify([p.to_dict() for p in posts])


# =========================
# GET POSTS BY STATUS
# =========================
@posts_bp.route('/api/posts/by-status', methods=['GET'])
def get_posts_by_status():
    """
    Mendapatkan posts berdasarkan status.
    Query param: status (menunggu, diproses, selesai, atau 'all')
    """
    status_filter = request.args.get('status', 'all').lower()
    
    if status_filter == 'all':
        posts = Post.query.order_by(Post.created_at.desc()).all()
    elif status_filter == 'menunggu':
        posts = Post.query.filter_by(status=PostStatus.MENUNGGU).order_by(Post.created_at.desc()).all()
    elif status_filter == 'diproses':
        posts = Post.query.filter_by(status=PostStatus.DIPROSES).order_by(Post.created_at.desc()).all()
    elif status_filter == 'selesai':
        posts = Post.query.filter_by(status=PostStatus.SELESAI).order_by(Post.created_at.desc()).all()
    else:
        return jsonify({'error': 'Status filter tidak valid'}), 400
    
    return jsonify([p.to_dict() for p in posts])


# =========================
# VERIFY POST
# =========================
@posts_bp.route('/api/posts/<int:post_id>/verify', methods=['POST'])
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

    # Update polling counts
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
# DELETE POST
# =========================
@posts_bp.route('/api/posts/<int:post_id>', methods=['DELETE'])
@token_required
def delete_post(current_user, post_id):
    from models import UserRole
    
    post = Post.query.get_or_404(post_id)
    if current_user.role != UserRole.ADMIN and current_user.id != post.user_id:
        return jsonify({'error': 'Akses ditolak'}), 403
    
    PostVerification.query.filter_by(post_id=post_id).delete()
    image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], post.image_path)
    if os.path.exists(image_path):
        os.remove(image_path)
    
    db.session.delete(post)
    db.session.commit()
    return jsonify({'message': 'Laporan berhasil dihapus'})


# =========================
# UPDATE POST STATUS (PETUGAS)
# =========================
@posts_bp.route('/api/posts/<int:post_id>/status', methods=['PUT'])
@token_required
def update_post_status(current_user, post_id):
    """
    Update status penanganan post.
    Hanya bisa diakses oleh Petugas atau Admin.
    
    Status yang valid:
    - menunggu: Baru diupload, menunggu ditangani
    - diproses: Sedang dalam penanganan petugas
    - selesai: Sudah diperbaiki
    """
    from models import UserRole
    
    if current_user.role not in [UserRole.PETUGAS, UserRole.ADMIN]:
        return jsonify({'error': 'Akses ditolak. Hanya petugas atau admin yang bisa mengubah status.'}), 403
    
    post = Post.query.get_or_404(post_id)
    data = request.json
    
    new_status = data.get('status', '').lower()
    
    valid_statuses = ['menunggu', 'diproses', 'selesai']
    if new_status not in valid_statuses:
        return jsonify({
            'error': f'Status tidak valid. Pilihan: {valid_statuses}'
        }), 400
    
    if new_status == 'menunggu':
        post.status = PostStatus.MENUNGGU
    elif new_status == 'diproses':
        post.status = PostStatus.DIPROSES
    elif new_status == 'selesai':
        post.status = PostStatus.SELESAI
    
    db.session.commit()
    
    return jsonify({
        'message': f'Status berhasil diubah menjadi {new_status}',
        'data': post.to_dict()
    })
