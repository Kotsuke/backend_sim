"""
Script to fix the status enum values in the database.
Converts lowercase status values to uppercase to match the MySQL ENUM definition.

Run this script on your server:
    python fix_status_enum.py
"""
from app import app
from models import db

def fix_status_values():
    """Update all lowercase status values to uppercase."""
    with app.app_context():
        # Direct SQL update for efficiency
        updates = [
            ("UPDATE posts SET status = 'MENUNGGU' WHERE status = 'menunggu'", "menunggu -> MENUNGGU"),
            ("UPDATE posts SET status = 'DIPROSES' WHERE status = 'diproses'", "diproses -> DIPROSES"),
            ("UPDATE posts SET status = 'SELESAI' WHERE status = 'selesai'", "selesai -> SELESAI"),
        ]
        
        total_updated = 0
        for sql, description in updates:
            result = db.session.execute(db.text(sql))
            count = result.rowcount
            total_updated += count
            print(f"  {description}: {count} rows updated")
        
        db.session.commit()
        print(f"\nTotal rows updated: {total_updated}")
        print("Status enum values have been fixed!")

if __name__ == '__main__':
    print("Fixing status enum values in the database...")
    print("-" * 50)
    fix_status_values()
