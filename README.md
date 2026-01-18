# 🔧 SmartInfra Backend (Backend Sim)

Backend server untuk aplikasi **SmartInfra** (Capstone Project). Dibuat menggunakan **Flask (Python)** sebagai core framework, backend ini menangani seluruh logika bisnis, interaksi database, pemrosesan AI untuk deteksi kerusakan jalan, serta integrasi Chatbot cerdas.

---

## ✨ Fitur Utama

| Fitur | Deskripsi |
|-------|-----------|
| 🔐 **Autentikasi** | Login/Register dengan JWT, Google Sign-In |
| 👤 **User Management** | CRUD User, Role (User/Admin), Poin Gamifikasi |
| 📸 **Deteksi Lubang Jalan** | AI Detection menggunakan **YOLOv8** (Model Lokal) |
| 🗳️ **Community Verification** | Sistem voting Valid/Hoax untuk laporan |
| 💬 **AI Chatbot** | RAG-based chatbot untuk pertanyaan infrastruktur |
| ⭐ **Review & Rating** | Sistem ulasan dengan **Sentiment Analysis** (Scikit-learn) |
| 📊 **Dashboard Analytics** | Statistik, grafik pertumbuhan user/post |

---

## 🧠 AI Models

### 1. Pothole Detection (YOLOv8)
- **File**: `best.pt`
- **Library**: `ultralytics`
- **Fungsi**: Mendeteksi lubang jalan dari gambar yang diupload
- **Output**: Jumlah lubang + Severity (SERIUS / TIDAK_SERIUS)

**Logika Severity:**
- ✅ **SERIUS**: Jika ada lubang > 3.5% dari area gambar ATAU jumlah lubang > 4
- ✅ **TIDAK_SERIUS**: Lubang kecil dan sedikit

### 2. Sentiment Analysis (Scikit-learn)
- **File**: `sentiment_model_sim.pkl`
- **Library**: `scikit-learn`
- **Fungsi**: Menganalisis sentimen dari komentar review
- **Output**: `positif` atau `negatif`

### 3. RAG Chatbot
- **Folder**: `chatbotboti-main/`
- **Fungsi**: Menjawab pertanyaan tentang infrastruktur menggunakan dokumen konteks

---

## 🗄️ Struktur Database

Backend ini menggunakan Database Relasional (MySQL) dengan skema sebagai berikut:

### 1. 👤 Users (`users`)
| Column | Type | Deskripsi |
|--------|------|-----------|
| `id` | INT (PK) | ID unik user |
| `username` | VARCHAR | Username unik |
| `email` | VARCHAR | Email unik |
| `full_name` | VARCHAR | Nama lengkap |
| `password_hash` | VARCHAR | Password terenkripsi |
| `role` | ENUM | `user` atau `admin` |
| `points` | INT | Poin reputasi |
| `created_at` | DATETIME | Waktu registrasi |

### 2. 📝 Posts (`posts`)
| Column | Type | Deskripsi |
|--------|------|-----------|
| `id` | INT (PK) | ID laporan |
| `user_id` | INT (FK) | ID pelapor |
| `image_path` | VARCHAR | Path file foto |
| `latitude`, `longitude` | DECIMAL | Koordinat GPS |
| `address` | VARCHAR | Alamat lokasi |
| `severity` | ENUM | `SERIUS` / `TIDAK_SERIUS` |
| `pothole_count` | INT | Jumlah lubang terdeteksi |
| `confirm_count`, `false_count` | INT | Counter voting |

### 3. ⭐ Reviews (`reviews`)
| Column | Type | Deskripsi |
|--------|------|-----------|
| `id` | INT (PK) | ID review |
| `user_id` | INT (FK) | ID reviewer |
| `rating` | INT | Skor 1-5 |
| `comment` | TEXT | Komentar |
| `sentiment` | VARCHAR | `positif` / `negatif` |

### 4. ✅ PostVerifications (`post_verifications`)
| Column | Type | Deskripsi |
|--------|------|-----------|
| `post_id` | INT (FK) | ID post |
| `user_id` | INT (FK) | ID voter |
| `verification_type` | ENUM | `confirm` / `false` |

---

## 📁 Struktur Folder

```
backend_sim/
├── app.py                    # Main Flask application
├── config.py                 # Konfigurasi database & upload
├── models.py                 # SQLAlchemy models
├── sentiment_service.py      # Service untuk sentiment analysis
├── requirements.txt          # Python dependencies
├── best.pt                   # Model YOLOv8 untuk deteksi lubang
├── sentiment_model_sim.pkl   # Model scikit-learn untuk sentiment
├── uploads/                  # Folder penyimpanan gambar
├── chatbotboti-main/         # Modul AI Chatbot (RAG)
│   ├── chatbot_model.py
│   └── rag/
└── README.md                 # Dokumentasi ini
```

---

## 🔌 API Endpoints

### Authentication
| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| POST | `/api/register` | Registrasi user baru |
| POST | `/api/login` | Login dengan username/password |
| POST | `/api/google-login` | Login via Google Sign-In |

### Users
| Method | Endpoint | Auth | Deskripsi |
|--------|----------|------|-----------|
| GET | `/api/users` | - | List semua user |
| GET | `/api/users/<id>` | - | Detail user |
| PUT | `/api/users/<id>` | ✅ | Update profil sendiri |
| DELETE | `/api/users/<id>` | ✅ Admin | Hapus user |

### Posts (Laporan)
| Method | Endpoint | Auth | Deskripsi |
|--------|----------|------|-----------|
| GET | `/api/posts` | - | List semua laporan |
| POST | `/api/upload` | ✅ | Upload laporan baru (dengan AI detection) |
| POST | `/api/posts/<id>/verify` | ✅ | Vote laporan (Valid/Hoax) |
| DELETE | `/api/posts/<id>` | ✅ | Hapus laporan |

### Reviews
| Method | Endpoint | Auth | Deskripsi |
|--------|----------|------|-----------|
| GET | `/api/reviews` | - | List semua review |
| POST | `/api/reviews` | ✅ | Kirim review baru |
| DELETE | `/api/reviews/<id>` | ✅ Admin | Hapus review |

### Chatbot
| Method | Endpoint | Auth | Deskripsi |
|--------|----------|------|-----------|
| POST | `/api/chat` | ✅ | Kirim pesan ke chatbot |

### Dashboard (Admin)
| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| GET | `/api/dashboard/stats` | Statistik dashboard |
| GET | `/api/dashboard/growth` | Data untuk grafik pertumbuhan |

### Admin Operations
| Method | Endpoint | Auth | Deskripsi |
|--------|----------|------|-----------|
| POST | `/api/admin/users` | ✅ Admin | Buat user baru |
| PUT | `/api/admin/users/<id>` | ✅ Admin | Edit user |

---

## ⚠️ Konfigurasi Environment (.env)

Buat file `.env` di direktori `backend_sim/`:

```env
# Database (optional - override config.py)
DATABASE_URL=mysql+pymysql://root:@localhost/database_sim

# Security
SECRET_KEY=rahasia_negara_jangan_disebar

# Chatbot (Gemini API Key - jika menggunakan)
GEMINI_API_KEY=masukkan_api_key_gemini_jika_pakai
```

> **Catatan**: Model YOLO dan Sentiment sudah menggunakan file lokal, tidak memerlukan API key eksternal.

---

## 🚀 Cara Menjalankan

### Prasyarat
- Python 3.8+
- MySQL Server (XAMPP/dll)
- Database `database_sim` sudah dibuat

### Langkah-langkah

```bash
# 1. Masuk ke direktori backend
cd backend_sim

# 2. Buat Virtual Environment
python -m venv venv

# 3. Aktifkan venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Jalankan server
python app.py
```

Server akan berjalan di `http://localhost:5000`

---

## 📦 Dependencies

```
flask>=2.0.0
flask-sqlalchemy>=3.0.0
flask-cors>=4.0.0
PyJWT>=2.0.0
werkzeug>=2.0.0
opencv-python>=4.5.0
numpy>=1.21.0
ultralytics>=8.0.0      # YOLO untuk deteksi lubang
scikit-learn>=1.0.0     # Sentiment analysis
pymysql                 # MySQL connector
```

---

## 🧪 Testing

Gunakan **Postman** atau **Insomnia** untuk menguji endpoint.

### Contoh Request Upload

```bash
curl -X POST http://localhost:5000/api/upload \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "image=@pothole.jpg" \
  -F "latitude=-6.200000" \
  -F "longitude=106.816666" \
  -F "address=Jl. Sudirman, Jakarta"
```

### Contoh Response

```json
{
  "message": "Upload berhasil",
  "data": {
    "id": 1,
    "severity": "SERIUS",
    "pothole_count": 3,
    "address": "Jl. Sudirman, Jakarta"
  }
}
```

---

## 📋 Changelog

### v2.0.0 (2026-01-18)
- ✅ Migrasi dari Roboflow API ke **YOLOv8 lokal** (`best.pt`)
- ✅ Migrasi sentiment analysis dari TensorFlow/Keras ke **Scikit-learn** (`sentiment_model_sim.pkl`)
- ✅ Optimasi struktur kode dan import
- ✅ Penambahan validasi koordinat di upload
- ✅ Dokumentasi API lengkap

### v1.0.0
- Initial release dengan Roboflow API
- Fitur dasar: Auth, Upload, Verification, Reviews, Chatbot

---

## 👨‍💻 Author

SmartInfra Capstone Team
