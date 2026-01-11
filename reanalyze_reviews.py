from app import app, db
from models import Review
from sentiment_service import init_analyzer, predict_sentiment
import os

# Set working directory to this file's directory
basedir = os.path.abspath(os.path.dirname(__file__))

print("⏳ Initializing Sentiment Analyzer...")
init_analyzer(basedir)

with app.app_context():
    print("🔍 Fetching reviews...")
    reviews = Review.query.all()
    count = 0
    updated = 0
    
    for r in reviews:
        count += 1
        if r.comment:
            old_sentiment = r.sentiment
            new_sentiment = predict_sentiment(r.comment)
            
            if new_sentiment:
                r.sentiment = new_sentiment
                updated += 1
                print(f"[{count}] Review ID {r.id}: '{r.comment[:30]}...' -> {old_sentiment} => {new_sentiment}")
            else:
                print(f"[{count}] Review ID {r.id}: Failed to predict.")
        else:
            print(f"[{count}] Review ID {r.id}: No comment, skip.")
            
    if updated > 0:
        db.session.commit()
        print(f"\n✅ Successfully updated {updated} reviews.")
    else:
        print("\nℹ️ No reviews needed update or analysis failed.")
