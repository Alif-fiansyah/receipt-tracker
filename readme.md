# ExpenseLog

Aplikasi manajemen pengeluaran personal dan digitalisasi bukti transaksi berbasis web. **ExpenseLog** dirancang untuk mencatat arus kas secara instan melalui pemindaian foto struk kasir, verifikasi mandiri, pemantauan batas anggaran bulanan, sistem multi-user dengan isolasi data akun, serta penyimpanan data cloud persisten.

---

## Fitur Utama

* **Sistem Akun & Multi-User:** Registrasi dan login mandiri; data transaksi serta konfigurasi anggaran terisolasi penuh per pengguna.
* **Digitalisasi Bukti Bayar:** Memindai foto struk kasir secara langsung melalui kamera perangkat atau unggahan berkas (PNG/JPG/JPEG/HEIC/HEIF).
* **Ekstraksi Data Terstruktur:** Mengekstrak nama entitas (merchant), tanggal transaksi, total nominal, kategori belanja, hingga perincian item secara otomatis menggunakan Gemini AI.
* **Validasi Data (Human-in-the-Loop):** Formulir verifikasi sebelum data disimpan permanen ke basis data untuk memastikan akurasi OCR.
* **Manajemen Parameter Anggaran:** Menetapkan batas anggaran bulanan fleksibel yang tersimpan permanen di cloud per akun.
* **Log & Analisis Transaksi:** Visualisasi tren pengeluaran harian, agregasi total belanja bulanan, evaluasi ringkasan finansial, dan ekspor data dalam format CSV.
* **Penyimpanan Persisten (Turso Cloud):** Terintegrasi dengan basis data LibSQL/Turso Cloud via protokol HTTPS yang stabil sehingga data tidak hilang saat server melakukan restart atau hibernasi.

---

## Arsitektur & Teknologi

* **Antarmuka (Frontend):** Streamlit
* **Ekstraksi Dokumen:** Google Generative AI (`gemini-3.8-flash`) via SDK `google-genai`
* **Pemrosesan Gambar:** Pillow & `pillow-heif` (dukungan foto kamera iPhone)
* **Validasi Skema Data:** Pydantic
* **Basis Data:** Turso Cloud (LibSQL) via HTTPS REST Client dengan mekanisme *fallback* lokal ke SQLite
* **Autentikasi:** Hash SHA-256 bawaan Python
* **Manipulasi Data & Visualisasi:** Pandas, Altair

---

## 🏗️ Architecture

```text
┌───────────────────────┐
│     Client User       │
│  (Mobile / Desktop)   │
└──────────┬────────────┘
           │ HTTPS / Streamlit UI
           ▼
┌───────────────────────────────────────────────┐
│              Streamlit Engine                 │
│                  (app.py)                     │
└──────────┬────────────────────────┬───────────┘
           │                        │
           │ Upload Image           │ Auth & CRUD
           │ (JPG/PNG/HEIC)         │ Payload
           ▼                        ▼
┌───────────────────────┐  ┌────────────────────┐
│    Receipt Parser     │  │  Data Persistence  │
│     (tracker.py)      │  │      (db.py)       │
└──────────┬────────────┘  └────────┬───────────┘
           │                        │
           │ Part Bytes + Prompt    │ REST over HTTPS
           ▼                        ▼
┌───────────────────────┐  ┌────────────────────┐
│     Google Gemini     │  │    Turso Cloud     │
│  (gemini-3.8-flash)   │  │  (LibSQL Database) │
└──────────┬────────────┘  └────────────────────┘
           │
           │ Structured JSON
           ▼
┌───────────────────────┐
│   Schema Validator    │
│      (Pydantic)       │
└───────────────────────┘
```

---

## Struktur Direktori

 ```text
receipt-tracker/
├── assets/
│   └── style.css          # Kustomisasi tema dan tampilan antarmuka
├── app.py                 # Titik masuk utama aplikasi (UI Auth & Transaksi)
├── db.py                  # Lapisan abstraksi basis data (Turso Cloud / SQLite)
├── tracker.py             # Logika ekstraksi dokumen dan skema Pydantic
├── requirements.txt       # Daftar dependensi pustaka Python
├── .env                   # Variabel lingkungan lokal (kredensial API & DB)
└── README.md              # Dokumentasi proyek
