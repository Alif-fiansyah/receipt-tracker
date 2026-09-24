# ExpenseLog

Aplikasi manajemen pengeluaran personal dan digitalisasi bukti transaksi berbasis web. **ExpenseLog** dirancang untuk mencatat arus kas secara instan melalui pemindaian foto struk kasir, verifikasi mandiri, pemantauan batas anggaran bulanan, serta penyimpanan data cloud persisten.

---

## Fitur Utama

- **Digitalisasi Bukti Bayar:** Memindai foto struk kasir secara langsung melalui kamera perangkat atau unggahan berkas (PNG/JPG/JPEG).
- **Ekstraksi Data Terstruktur:** Mengekstrak nama entitas (merchant), tanggal transaksi, total nominal, kategori belanja, hingga perincian item secara otomatis.
- **Validasi Data (Human-in-the-Loop):** Formulir verifikasi sebelum data disimpan permanen ke basis data.
- **Manajemen Parameter Anggaran:** Menetapkan batas anggaran bulanan fleksibel yang tersimpan permanen di cloud.
- **Analisis Tren & Riwayat:** Visualisasi riwayat transaksi harian, agregasi total belanja bulanan, dan ekspor data dalam format CSV.
- **Penyimpanan Persisten (Turso Cloud):** Terintegrasi dengan database LibSQL/Turso Cloud sehingga data tidak hilang saat server melakukan restart atau hibernasi.

---

## Arsitektur & Teknologi

- **Antarmuka (Frontend):** [Streamlit](https://streamlit.io/)
- **Ekstraksi Dokumen:** Google Generative AI (Gemini Vision) via SDK `google-genai`
- **Validasi Skema:** Pydantic
- **Basis Data:** [Turso](https://turso.tech/) (LibSQL) dengan *fallback* lokal ke SQLite
- **Manipulasi Data & Grafik:** Pandas, Altair

---

## Struktur Direktori

```text
receipt-tracker/
├── assets/
│   └── style.css          # Kustomisasi tema dan tampilan antarmuka
├── app.py                 # Titik masuk utama aplikasi (Streamlit UI & kontrol alur)
├── db.py                  # Lapisan abstraksi basis data (Turso Cloud / SQLite)
├── tracker.py             # Logika ekstraksi dokumen dan skema Pydantic
├── requirements.txt       # Daftar dependensi pustaka Python
├── .env                   # Variabel lingkungan lokal (kredensial API & DB)
└── README.md              # Dokumentasi proyek
