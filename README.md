# 🔧 SmartInfra Backend (Backend Sim)

Backend server untuk aplikasi **SmartInfra** (Capstone Project). Dibuat menggunakan **Flask (Python)** sebagai core framework, backend ini menangani seluruh logika bisnis, interaksi database, pemrosesan AI untuk deteksi kerusakan jalan, serta integrasi Chatbot cerdas.

---

## ✨ Fitur Utama

1.  **API Services**: Menyediakan endpoint RESTful untuk aplikasi mobile (Flutter).
2.  **Autentikasi & Otorisasi**: Sistem login aman menggunakan JWT dan hashing password.
3.  **Manajemen Pengguna (User Management)**:
    *   Registrasi & Login.
    *   Sistem Role (User & Admin).
    *   Profil pengguna (Bio, Poin, dll).
4.  **Sistem Postingan & Deteksi AI**:
    *   Menangani upload gambar laporan.
    *   **Integrasi Computer Vision**: Melakukan inferensi untuk mendeteksi kerusakan jalan (Lubang, Retak, dll) dan memberi label "SERIUS" atau "TIDAK SERIUS".
    *   Geotagging lokasi kerusakan.
5.  **Community Verification**:
    *   Fitur validasi komunitas (Vote Valid/Hoax) untuk setiap laporan.
6.  **Gamification**: Sistem poin untuk pengguna yang aktif melapor.
7.  **AI Chatbot (RAG / LLM Integration)**:
    *   Endpoint khusus untuk melayani pertanyaan pengguna seputar infrastruktur menggunakan konteks dokumen yang relevan.

---

## 🗄️ Struktur Database

Backend ini menggunakan Database Relasional (MySQL) dengan skema sebagai berikut:

### 1. 👤 Users (`users`)
Menyimpan data pengguna terdaftar.
*   `id` (PK): ID unik user.
*   `username`, `email`, `full_name`: Identitas user.
*   `password_hash`: Password terenkripsi.
*   `role`: Peran user (`user` atau `admin`).
*   `points`: Point reputasi user.

### 2. 📝 Posts (`posts`)
Menyimpan laporan kerusakan jalan.
*   `id` (PK): ID laporan.
*   `user_id` (FK): Pelapor.
*   `image_path`: Lokasi file foto.
*   `latitude`, `longitude`: Koordinat lokasi.
*   `severity`: Label AI (`SERIUS` / `TIDAK_SERIUS`).
*   `pothole_count`: Jumlah lubang terdeteksi.
*   `confirm_count` & `false_count`: Counter verifikasi komunitas.

### 3. ⭐ Reviews (`reviews`)
Menyimpan ulasan user terhadap aplikasi/layanan.
*   `rating`: Skala 1-5.
*   `comment`: Masukan user.

### 4. ✅ PostVerifications (`post_verifications`)
Mencatat history verifikasi agar user tidak voting ganda.
*   `post_id`, `user_id`: Relasi ke post dan user.
*   `verification_type`: `confirm` (Valid) atau `false` (Tidak Valid).

---

## ⚠️ PENTING: Konfigurasi Environment (.env)

Sebelum menjalankan aplikasi, Anda **WAJIB** membuat file `.env` di direktori `backend_sim/`. File ini berfungsi untuk menyimpan kredensial sensitif, terutama untuk fitur **API CHATBOT**.

Buat file bernama `.env` dan isi dengan konfigurasi berikut:

```env
# Konfigurasi Database (Jika ingin override config.py)
DATABASE_URL=mysql+pymysql://root:@localhost/database_sim

# API Key untuk Layanan AI Deteksi Jalan (Roboflow)
# WAJIB DIISI! Jika kosong, fitur deteksi jalan tidak akan jalan
ROBOFLOW_API_KEY=masukkan_api_key_roboflow_disini
ROBOFLOW_MODEL_ID=pothole-detection-bqu6s-ztwh1/1 

# API Key untuk Chatbot (Gemini / LLM Lain)
GEMINI_API_KEY=masukkan_api_key_gemini_jika_pakai

# Security
SECRET_KEY=rahasia_negara_jangan_disebar
```

> **Catatan:** Pastikan API Key Chatbot valid agar fitur asisten cerdas dapat berjalan normal.

---

## 🚀 Cara Menjalankan (Local Development)

### Prasyarat
*   Python 3.8+ terinstall.
*   MySQL Server (cth: via XAMPP) berjalan.
*   Database kosong bernama `database_sim` telah dibuat di MySQL.

### Langkah-langkah

1.  **Masuk ke direktori backend**
    ```bash
    cd backend_sim
    ```

2.  **Buat Virtual Environment (Sangat Disarankan)**
    ```bash
    # Windows
    python -m venv venv
    venv\Scripts\activate

    # Mac/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Setup Database**
    Pastikan XAMPP/MySQL nyala.
    ```bash
    # Aplikasi akan otomatis membuat tabel saat pertama kali dijalankan (via db.create_all() di app.py)
    # Cukup pastikan database 'database_sim' sudah ada.
    ```

5.  **Jalankan Server**
    ```bash
    python app.py
    ```
    Server akan berjalan di `http://localhost:5000` (atau port yang tertera).

---

## 🧪 Testing API
Gunakan **Postman** atau **Insomnia** untuk menguji endpoint yang tersedia. Dokumentasi endpoint lengkap dapat dilihat pada file `app.py`.
