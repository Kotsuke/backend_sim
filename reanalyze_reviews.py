from app import app, db
from models import Review
import sentiment_service  # Import module, bukan variable langsung
import os

# Set working directory to this file's directory
basedir = os.path.abspath(os.path.dirname(__file__))

print(f"📂 Base Dir: {basedir}")
model_check = os.path.join(basedir, 'sentiment_assets', 'bilstm_model.keras')
print(f"🧐 Checking Model Path: {model_check} -> Exists? {os.path.exists(model_check)}")

print("⏳ Initializing Sentiment Analyzer...")
sentiment_service.init_analyzer(basedir)

# Akses analyzer via module (bukan import langsung) agar dapat nilai terbaru
if not sentiment_service.analyzer:
    print("❌ FATAL: Analyzer is None (Init failed). Assets missing?")
    exit(1)

if not sentiment_service.analyzer.model:
    print("❌ FATAL: Analyzer created but Model is None (Load failed). Check logs above.")
    exit(1)

print(f"✅ Analyzer Status: Loaded. Model: {sentiment_service.analyzer.model}")

with app.app_context():
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
