"""
Script untuk reanalyze sentiment review yang sudah ada di database.
Dijalankan standalone, tanpa melalui app.py untuk menghindari konflik import.
"""
import os
import sys

# Pastikan root dir ada di path
basedir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, basedir)

# Import config dulu untuk database URI
from config import Config

# Setup Flask app minimal (tanpa import app.py yang berat)
from flask import Flask
from models import db, Review

mini_app = Flask(__name__)
mini_app.config.from_object(Config)
db.init_app(mini_app)

# Import sentiment service
import sentiment_service

print(f"📂 Base Dir: {basedir}")
model_check = os.path.join(basedir, 'sentiment_assets', 'bilstm_model.keras')
print(f"🧐 Checking Model Path: {model_check} -> Exists? {os.path.exists(model_check)}")

print("⏳ Initializing Sentiment Analyzer...")
sentiment_service.init_analyzer(basedir)

print(f"🔍 Checking sentiment_service.analyzer = {sentiment_service.analyzer}")

if not sentiment_service.analyzer:
    print("❌ FATAL: Analyzer is None (Init failed).")
    exit(1)

if not sentiment_service.analyzer.model:
    print("❌ FATAL: Analyzer created but Model is None (Load failed).")
    exit(1)

print(f"✅ Analyzer Status: Loaded. Model: {sentiment_service.analyzer.model}")

with mini_app.app_context():
    print("🔍 Fetching reviews...")
    reviews = Review.query.all()
    count = 0
    updated = 0
    
    for r in reviews:
        count += 1
        if r.comment:
            old_sentiment = r.sentiment
            try:
                new_sentiment = sentiment_service.predict_sentiment(r.comment)
                
                if new_sentiment:
                    r.sentiment = new_sentiment
                    updated += 1
                    print(f"[{count}] Review ID {r.id}: '{r.comment[:30]}...' -> {old_sentiment} => {new_sentiment}")
                else:
                    print(f"[{count}] Review ID {r.id}: Failed to predict (Result is None).")
            except Exception as e:
                print(f"[{count}] Review ID {r.id}: EXCEPTION during prediction: {e}")
        else:
            print(f"[{count}] Review ID {r.id}: No comment, skip.")
            
    if updated > 0:
        db.session.commit()
        print(f"\n✅ Successfully updated {updated} reviews.")
    else:
        print("\nℹ️ No reviews needed update or analysis failed.")
