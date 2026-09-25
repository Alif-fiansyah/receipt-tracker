import streamlit as st
import pandas as pd
import altair as alt
from PIL import Image
import io
import db
import tracker

# Inisialisasi konfigurasi dasar Streamlit
st.set_page_config(
    page_title="ExpenseLog",
    page_icon="■",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load tema/gaya kustom
try:
    with open("assets/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

# Inisialisasi basis data
db.init_db()

# State login di session
if "user" not in st.session_state:
    st.session_state.user = None

# ==========================================
# HALAMAN LOGIN / REGISTER (JIKA BELUM LOGIN)
# ==========================================
if not st.session_state.user:
    # Buat 3 kolom: kiri (kosong), tengah (konten form), kanan (kosong)
    _, col_center, _ = st.columns([1, 1.2, 1])

    with col_center:
        st.markdown("<h2 style='text-align: center; margin-bottom: 0px;'>ExpenseLog</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #888; font-size: 0.9rem; margin-bottom: 2rem;'>Pencatatan transaksi harian dan manajemen anggaran belanja.</p>", unsafe_allow_html=True)

        tab_login, tab_register = st.tabs(["Masuk", "Daftar Akun"])

        with tab_login:
            st.markdown("##### Masuk ke Akun Anda")
            with st.form("form_login"):
                login_user = st.text_input("Username").strip()
                login_pwd = st.text_input("Password", type="password")
                btn_login = st.form_submit_button("Masuk", type="primary", use_container_width=True)

                if btn_login:
                    if not login_user or not login_pwd:
                        st.warning("Mohon lengkapi username dan password.")
                    else:
                        user_data = db.authenticate_user(login_user, login_pwd)
                        if user_data:
                            st.session_state.user = user_data
                            st.rerun()
                        else:
                            st.error("Username atau password salah.")

        with tab_register:
            st.markdown("##### Buat Akun Baru")
            with st.form("form_register"):
                reg_user = st.text_input("Buat Username").strip()
                reg_pwd = st.text_input("Buat Password", type="password")
                btn_reg = st.form_submit_button("Daftar Akun", use_container_width=True)

                if btn_reg:
                    if not reg_user or not reg_pwd:
                        st.warning("Mohon isi username dan password.")
                    else:
                        success = db.register_user(reg_user, reg_pwd)
                        if success:
                            st.success("Akun berhasil dibuat! Silakan masuk pada tab 'Masuk'.")
                        else:
                            st.error("Username sudah terdaftar. Gunakan username lain.")
        st.stop()

# ==========================================
# HALAMAN UTAMA (SETELAH BERHASIL LOGIN)
# ==========================================
current_user = st.session_state.user
user_id = current_user["id"]

# Sidebar Navigasi & Informasi User
with st.sidebar:
    st.markdown(f"**Akun:** `{current_user['username']}`")
    if st.button("Keluar (Logout)"):
        st.session_state.user = None
        st.session_state.temp_extracted_data = None
        st.rerun()

    st.divider()
    st.markdown("#### Parameter Anggaran")
    current_budget = db.get_budget(user_id, default_val=3000000.0)

    monthly_budget = st.number_input(
        "Batas Anggaran Bulanan (Rp):",
        min_value=100000,
        max_value=100000000,
        value=int(current_budget),
        step=250000,
    )

    if monthly_budget != int(current_budget):
        db.set_budget(user_id, float(monthly_budget))
        st.success("Anggaran diperbarui!")
        st.rerun()

    st.caption("Batas anggaran ini tersimpan khusus untuk akun Anda.")

# Header
st.markdown("### ExpenseLog")
st.caption("Digitalisasi bukti bayar dan manajemen anggaran belanja.")
st.write("")

tab_input, tab_history = st.tabs(["Pindai Bukti Bayar", "Log & Analisis Transaksi"])

# --- TAB 1: INPUT STRUK ---
with tab_input:
    col_input, col_preview = st.columns([1, 1], gap="medium")

    with col_input:
        st.markdown("##### Unggah Berkas Transaksi")
        input_method = st.radio("Pilih metode:", ["Pindai Kamera", "Unggah Berkas"], horizontal=True)

        if input_method == "Pindai Kamera":
            camera_img = st.camera_input("Ambil foto bukti bayar")
            if camera_img is not None:
                st.session_state.active_image = camera_img.getvalue()
        else:
            uploaded_file = st.file_uploader("Pilih gambar...", type=["jpg", "jpeg", "png"])
            if uploaded_file is not None:
                st.session_state.active_image = uploaded_file.getvalue()

        if st.session_state.get("active_image"):
            if st.button("Pindai Bukti Bayar", type="primary", use_container_width=True):
                with st.spinner("Memproses digitalisasi dokumen..."):
                    try:
                        # Buat stream baru dan pastikan pointer berada di byte ke-0
                        image_stream = io.BytesIO(st.session_state.active_image)
                        image_stream.seek(0)
                        img = Image.open(image_stream)

                        result = tracker.extract_receipt(img)
                        if result:
                            st.session_state.temp_extracted_data = result
                            st.success("Dokumen berhasil diekstraksi. Lakukan verifikasi di bawah.")
                        else:
                            st.error("Gagal membaca bukti bayar. Pastikan foto terbaca jelas.")
                    except Exception as err:
                        st.error(f"Terjadi kesalahan: {err}")

    with col_preview:
        if st.session_state.get("active_image"):
            st.markdown("##### Pratinjau Dokumen")
            st.image(st.session_state.active_image, use_container_width=True)

    # Human-in-the-Loop Verification Form
    if st.session_state.get("temp_extracted_data"):
        st.divider()
        st.markdown("##### Verifikasi & Konfirmasi Data")
        data = st.session_state.temp_extracted_data

        with st.form("verify_receipt_form"):
            col_v1, col_v2 = st.columns(2)
            with col_v1:
                v_merchant = st.text_input("Nama Merchant", value=data.get("merchant", ""))
                v_category = st.text_input("Kategori", value=data.get("category", "Lainnya"))
            with col_v2:
                v_date = st.text_input("Tanggal Transaksi (YYYY-MM-DD)", value=data.get("transaction_date", ""))
                v_total = st.number_input("Total Pembayaran (Rp)", value=float(data.get("total_amount", 0.0)), step=1000.0)

            st.caption("Rincian Item Terdeteksi:")
            if data.get("items"):
                items_df = pd.DataFrame(data["items"])
                st.dataframe(items_df, use_container_width=True)

            btn_confirm = st.form_submit_button("Simpan ke Basis Data", type="primary", use_container_width=True)

            if btn_confirm:
                final_payload = {
                    "merchant": v_merchant,
                    "transaction_date": v_date,
                    "total_amount": v_total,
                    "category": v_category,
                    "items": data.get("items", []),
                }
                receipt_id = db.save_receipt_data(final_payload, user_id=user_id)
                st.success(f"Transaksi tersimpan dengan ID: #{receipt_id}")
                st.session_state.temp_extracted_data = None
                st.session_state.active_image = None
                st.rerun()
                
# --- TAB 2: LOG & ANALITIK ---
with tab_history:
    raw_data = db.get_all_receipts(user_id=user_id)

    if not raw_data:
        st.info("Belum ada riwayat transaksi yang tersimpan untuk akun Anda.")
    else:
        df = pd.DataFrame(
            raw_data,
            columns=["ID", "Merchant", "Tanggal", "Nominal", "Kategori", "Waktu Simpan"],
        )

        # Ringkasan Anggaran
        total_spent = df["Nominal"].sum()
        remaining_budget = monthly_budget - total_spent
        spent_percent = min(100.0, (total_spent / monthly_budget) * 100.0) if monthly_budget > 0 else 0.0

        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Total Pengeluaran", f"Rp {total_spent:,.0f}")
        col_m2.metric("Sisa Anggaran", f"Rp {remaining_budget:,.0f}")
        col_m3.metric("Realisasi Anggaran", f"{spent_percent:.1f}%")

        st.progress(spent_percent / 100.0)
        st.write("")

        # Visualisasi Tren Pengeluaran Harian
        st.markdown("##### Tren Pengeluaran Harian")
        chart_df = df.groupby("Tanggal")["Nominal"].sum().reset_index()
        chart = (
            alt.Chart(chart_df)
            .mark_line(point=True)
            .encode(
                x=alt.X("Tanggal:T", title="Tanggal Transaksi"),
                y=alt.Y("Nominal:Q", title="Total Belanja (Rp)"),
                tooltip=["Tanggal", "Nominal"],
            )
            .interactive()
        )
        st.altair_chart(chart, use_container_width=True)

        st.divider()

        # Tabel Riwayat Transaksi
        st.markdown("##### Tabel Riwayat Transaksi")
        st.dataframe(df, use_container_width=True)

        # Tombol Download CSV
        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Unduh Log Transaksi (CSV)",
            data=csv_data,
            file_name=f"expenselog_{current_user['username']}.csv",
            mime="text/csv",
        )

        st.divider()

        # Evaluasi Ringkasan
        st.markdown("##### Analisis Pengeluaran")
        if st.button("Analisis Ringkasan Finansial"):
            with st.spinner("Menganalisis catatan pengeluaran..."):
                advice = tracker.generate_financial_advice(df.to_dict(orient="records"))
                st.markdown(advice)