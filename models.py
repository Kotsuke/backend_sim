from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
import enum
from sqlalchemy import Enum, UniqueConstraint


# Helper function untuk mendapatkan waktu UTC saat ini (timezone-aware)
def utc_now():
    return datetime.now(timezone.utc)

db = SQLAlchemy()

# 1. Role User
class UserRole(enum.Enum):
    USER = 'user'
    ADMIN = 'admin'

# 2. Tipe Verifikasi Komunitas (PENGGANTI STATUS)
# User cuma bisa milih: "Valid nih!" atau "Enggak kok/Udah bener"
class VerificationType(enum.Enum):
    CONFIRM = 'confirm' # Jempol Atas (Masih Rusak)
    FALSE = 'false'     # Jempol Bawah (Hoax / Sudah Mulus)

# --- MODEL USER ---
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Profil Tambahan
    phone = db.Column(db.String(20), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    points = db.Column(db.Integer, default=0) 

    role = db.Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    
    posts = db.relationship('Post', backref='author', lazy=True)
    verifications = db.relationship('PostVerification', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'role': self.role.value,
            'phone': self.phone if self.phone else "",
            'bio': self.bio if self.bio else "",
            'points': self.points
        }

# --- MODEL POSTINGAN ---
class Post(db.Model):
    __tablename__ = 'posts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    image_path = db.Column(db.String(255), nullable=False)

    latitude = db.Column(db.Numeric(10, 8), nullable=False)
    longitude = db.Column(db.Numeric(11, 8), nullable=False)
    address = db.Column(db.String(255), nullable=True)

    # Info Kerusakan
    pothole_count = db.Column(db.Integer, default=0)
    severity = db.Column(db.Enum('SERIUS', 'TIDAK_SERIUS'), nullable=False)
    caption = db.Column(db.Text)
    
    # --- Polling Count (Ini penentu statusnya nanti di Frontend) ---
    confirm_count = db.Column(db.Integer, default=0) 
    false_count = db.Column(db.Integer, default=0)   
    
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now)

    @property
    def uploaded_by(self):
        return self.author.full_name if self.author else 'Unknown'

    def to_dict(self):
        from flask import request
        full_image_url = f"{request.host_url}uploads/{self.image_path}"
        
        return {
            'id': self.id,
            'user_id': self.user_id,
            'uploaded_by': self.uploaded_by,
            'image_url': full_image_url,
            'lat': float(self.latitude),
            'long': float(self.longitude),
            'address': self.address if self.address else "Lokasi tidak diketahui",
            # Kita kirim data polling biar Frontend yang nentuin warnanya
            'severity': self.severity,
            'pothole_count': self.pothole_count,
            'caption': self.caption,
            'verification': {
                'valid': self.confirm_count,
                'false': self.false_count
            },
            'date': self.created_at.strftime('%Y-%m-%d %H:%M')
        }

# --- MODEL VERIFIKASI ---
class PostVerification(db.Model):
    __tablename__ = 'post_verifications'
    
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    verification_type = db.Column(Enum(VerificationType), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now)

    __table_args__ = (UniqueConstraint('post_id', 'user_id', name='unique_user_verification'),)