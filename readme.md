# EXPENSELog · Smart Financial Assistant

Platform cerdas berbasis web untuk pencatatan transaksi harian, automasi ekstraksi nota belanja berbasis AI & OCR, serta manajemen anggaran keuangan pribadi secara presisi. **EXPENSELog** dirancang untuk mencatat arus kas secara instan melalui pemindaian foto struk kasir, analisis tren & kategori interaktif, kalkulator rencana tabungan, asisten finansial berbasis AI, hingga penyimpanan cloud persisten multi-user.

---

## Fitur Utama

- **Sistem Akun & Multi-User:** Registrasi ringkas mandiri (tanpa input rumit di awal); data transaksi serta konfigurasi anggaran terisolasi penuh per pengguna dengan proteksi sesi terpusat.
- **Tampilan Autentikasi Modern:** Antarmuka login terpusat (*center-aligned single column*) yang elegan dengan kartu ringkasan keunggulan platform (*Smart Financial Assistant*).
- **Digitalisasi Bukti Bayar:** Memindai foto struk kasir secara langsung melalui kamera perangkat atau unggahan berkas (PNG/JPG/JPEG/HEIC/HEIF).
- **Ekstraksi Data Terstruktur:** Mengekstrak nama entitas (*merchant*), tanggal transaksi, total nominal, kategori belanja, hingga perincian item secara otomatis menggunakan Gemini AI.
- **Validasi Data (Human-in-the-Loop):** Formulir verifikasi dan penyesuaian manual sebelum data disimpan permanen ke basis data untuk memastikan akurasi data.
- **Manajemen Parameter Anggaran:** Menetapkan batas anggaran bulanan fleksibel yang tersimpan permanen di cloud per akun dengan indikator progres visual di sidebar.
- **Log & Analisis Transaksi Interaktif:**
  - Filter rentang tanggal dan pencarian merchant secara *real-time*.
  - Ringkasan metrik total belanja, rata-rata harian, dan frekuensi transaksi dalam format Rupiah (`Rp`).
  - Visualisasi tren pengeluaran harian serta *Donut Chart* proporsi alokasi kategori belanja.
  - Tabel transaksi detail disertai aksi hapus transaksi (*safe delete*) yang langsung tersinkronisasi.
- **Sidebar Financial Tools:** Dilengkapi dengan kalkulator *Savings Goal Planner* dan fitur konsultasi *Interactive AI Financial Advisor* untuk evaluasi pola pengeluaran berkala.
- **Penyimpanan Persisten (Turso Cloud / SQLite):** Terintegrasi dengan basis data LibSQL/Turso Cloud via protokol HTTPS yang stabil dengan mekanisme fallback SQLite lokal sehingga data tidak hilang saat server restart.

---

## Arsitektur & Teknologi

- **Antarmuka (Frontend):** Streamlit (Custom CSS & Responsive Centered Layout)
- **Ekstraksi Dokumen:** Google Generative AI (`gemini-2.5-flash` / `gemini-1.5-flash`) via SDK `google-genai`
- **Pemrosesan Gambar:** Pillow & `pillow-heif` (dukungan penuh foto kamera iPhone/HEIC)
- **Validasi Skema Data:** Pydantic
- **Basis Data:** Turso Cloud (LibSQL) via HTTPS REST Client dengan mekanisme *fallback* lokal ke SQLite
- **Autentikasi:** Hash SHA-256 bawaan Python
- **Manipulasi Data & Visualisasi:** Pandas, Altair, Plotly Express

---

## 🏗️ Architecture

```text
+-----------------------+
|      Client User      |
|   (Mobile / Desktop)  |
+-----------------------+
           |
           | HTTPS / Streamlit UI
           v
+-----------------------+
|    Streamlit Engine   |
|        (app.py)       |
+-----------------------+
     /                 \\
    / Upload Image      \\ Auth, Log Analysis &
   / (JPG/PNG/HEIC)      \\ CRUD Payload
  v                       v
+-------------------+   +--------------------+
|  Receipt Parser   |   |  Data Persistence  |
|   (tracker.py)    |   |      (db.py)       |
+-------------------+   +--------------------+
  | Part Bytes            |
  | + Prompt              | REST over HTTPS
  v                       v
+-------------------+   +--------------------+
|   Google Gemini   |   |    Turso Cloud     |
|   (Gemini Flash)  |   |  (LibSQL Database) |
+-------------------+   +--------------------+
          |
          | Structured JSON
          v
+-------------------+
|  Schema Validator |
|    (Pydantic)     |
+-------------------+
```

---

## Struktur Direktori

 ```text
receipt-tracker/
├── assets/
│   └── style.css       # Kustomisasi tema dan tampilan antarmuka
├── app.py              # Titik masuk utama aplikasi (UI Auth, Transaksi, Log & Analisis)
├── db.py               # Lapisan abstraksi basis data (Turso Cloud / SQLite) & Auth
├── tracker.py          # Logika ekstraksi dokumen dan skema Pydantic
├── requirements.txt    # Daftar dependensi pustaka Python
├── .env                # Variabel lingkungan lokal (kredensial API & DB)
└── README.md           # Dokumentasi proyek
