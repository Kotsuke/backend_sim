"""
Smart Infra Backend - Main Application
=====================================
Aplikasi backend untuk Smart Infrastructure Management System.

Struktur Kode:
- routes/auth.py    : Login, Register, Google Sign-In
- routes/users.py   : Profile, User Management
- routes/posts.py   : Upload, Feed, Verification, Filter
- routes/admin.py   : Dashboard Stats, Admin Operations
- routes/others.py  : Chatbot, Reviews, Static Files
- utils/decorators.py : JWT Token Decorator
- utils/ai_helper.py  : AI/YOLO Helper Functions
"""

import os
import sys
from flask import Flask
from flask_cors import CORS

# Local imports
from config import Config
from models import db

# =========================
# CHATBOT INIT
# =========================
sys.path.append(os.path.join(os.path.dirname(__file__), 'chatbotboti-main'))

chatbot = None
try:
    from chatbot_model import SIMChatbot
    chatbot = SIMChatbot()
    print("✅ Chatbot loaded successfully")
except Exception as e:
    print(f"⚠️ Chatbot failed to load: {e}")
    chatbot = None

# =========================
# SENTIMENT SERVICE INIT
# =========================
from sentiment_service import init_analyzer, predict_sentiment

# =========================
# APP INIT
# =========================
app = Flask(__name__)
CORS(app)
app.config.from_object(Config)
app.config['SECRET_KEY'] = 'secret_key_skripsi_smartinfra'

db.init_app(app)

# =========================
# YOLO MODEL INIT
# =========================
from ultralytics import YOLO

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'best.pt')
yolo_model = None

try:
    yolo_model = YOLO(MODEL_PATH)
    print(f"✅ YOLO model loaded successfully from: {MODEL_PATH}")
except Exception as e:
    print(f"⚠️ Failed to load YOLO model: {e}")
    yolo_model = None

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# =========================
# REGISTER BLUEPRINTS
# =========================
from routes.auth import auth_bp
from routes.users import users_bp
from routes.posts import posts_bp, set_yolo_model
from routes.admin import admin_bp, check_and_migrate_db
from routes.others import others_bp, set_chatbot, set_sentiment_service

# Inject dependencies
set_yolo_model(yolo_model)
set_chatbot(chatbot)
set_sentiment_service(predict_sentiment)

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(users_bp)
app.register_blueprint(posts_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(others_bp)

# =========================
# RUN
# =========================
if __name__ == '__main__':
    # Init Sentiment Analyzer
    init_analyzer(app.config['BASE_DIR'])
    
    # Run database migration
    check_and_migrate_db(app)
    
    # Start server
    print("\n" + "="*50)
    print("🚀 Smart Infra Backend Running!")
    print("="*50)
    print(f"📁 Upload Folder: {app.config['UPLOAD_FOLDER']}")
    print(f"🤖 YOLO Model: {'✅ Loaded' if yolo_model else '❌ Not Available'}")
    print(f"💬 Chatbot: {'✅ Active' if chatbot else '❌ Not Available'}")
    print("="*50 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
