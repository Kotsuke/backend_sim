import os

class Config:
    # Format: mysql+pymysql://USERNAME:PASSWORD@HOST/NAMA_DATABASE
    # Sesuaikan dengan settingan MySQL kamu (XAMPP biasanya user='root', pass='')
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:@localhost/database_sim'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # Limit upload 16M
