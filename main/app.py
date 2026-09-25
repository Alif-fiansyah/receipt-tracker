import io
import streamlit as st
import pandas as pd
import altair as alt
from PIL import Image

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
username_display = current_user.get("username", st.session_state.get("username", "User"))

# Sidebar Navigasi & Informasi User
with st.sidebar:
    initial = (username_display[:2] if len(username_display) >= 2 else username_display).upper()
    st.markdown(
        f"""
        <div style="display: flex; align-items: center; gap: 12px; padding: 12px; background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; margin-bottom: 12px;">
            <div style="width: 36px; height: 36px; border-radius: 50%; background: #262930; color: #e0e0e0; display: flex; align-items: center; justify-content: center; font-weight: 600; font-size: 0.82rem; border: 1px solid rgba(255, 255, 255, 0.12);">
                {initial}
            </div>
            <div style="flex: 1; min-width: 0;">
                <div style="font-size: 0.88rem; font-weight: 600; color: #f0f2f6; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                    {username_display}
                </div>
                <div style="font-size: 0.72rem; color: #8b949e;">
                    Akun Terverifikasi
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("Keluar", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.username = None
        st.session_state.user = None
        st.rerun()

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    st.caption("ANGGARAN & MONITORING")

    saved_budget = db.get_user_budget(user_id) if hasattr(db, "get_user_budget") else 2500000.0
    monthly_budget = st.number_input(
        "Batas Bulanan (Rp)",
        min_value=0,
        value=int(saved_budget),
        step=100000,
        label_visibility="collapsed",
    )

    if hasattr(db, "set_user_budget") and monthly_budget != saved_budget:
        db.set_user_budget(user_id, monthly_budget)

    user_txs = db.get_user_transactions(user_id) if hasattr(db, "get_user_transactions") else []
    total_spent = sum(t.get("total_amount", 0) for t in user_txs)

    if monthly_budget > 0:
        ratio = min(total_spent / monthly_budget, 1.0)
        st.progress(ratio)
        sisa = monthly_budget - total_spent
        pct = (total_spent / monthly_budget) * 100

        badge_bg = "rgba(46, 160, 67, 0.15)" if pct <= 75 else ("rgba(210, 153, 34, 0.15)" if pct <= 95 else "rgba(248, 81, 73, 0.15)")
        badge_fg = "#3fb950" if pct <= 75 else ("#d29922" if pct <= 95 else "#f85149")

        st.markdown(
            f"""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 4px; margin-bottom: 12px;">
                <span style="font-size: 0.75rem; color: #8b949e;">Status Pemakaian</span>
                <span style="font-size: 0.72rem; font-weight: 600; padding: 2px 7px; border-radius: 4px; background: {badge_bg}; color: {badge_fg};">
                    {pct:.1f}%
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.caption("Terpakai")
            st.markdown(f"<span style='font-size: 0.95rem; font-weight: 600; color: #e6edf3;'>Rp{total_spent:,.0f}</span>", unsafe_allow_html=True)
        with col_s2:
            st.caption("Sisa Saldo")
            sisa_color = "#3fb950" if sisa >= 0 else "#f85149"
            st.markdown(f"<span style='font-size: 0.95rem; font-weight: 600; color: {sisa_color};'>Rp{sisa:,.0f}</span>", unsafe_allow_html=True)

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    st.caption("EKSPOR DATA")
    if user_txs:
        df_export = pd.DataFrame(user_txs)
        csv_data = df_export.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Unduh CSV Transaksi",
            data=csv_data,
            file_name=f"transaksi_{username_display}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    else:
        st.caption("Belum ada data transaksi.")



tab_input, tab_history = st.tabs(["Pindai Bukti Bayar", "Log & Analisis Transaksi"])

# --- TAB 1: INPUT STRUK ---
with tab_input:
    _, col_center, _ = st.columns([0.18, 0.64, 0.18])
    with col_center:
        input_method = st.radio("Pilih metode:", ["Pindai Kamera", "Unggah Berkas", "Input Manual"], horizontal=True)

        if input_method == "Input Manual":
            st.session_state.active_image = None
            if "manual_success_notif" in st.session_state:
                st.success(st.session_state.pop("manual_success_notif"))
            st.markdown("##### Catat Transaksi Tunai / Manual")
            with st.form("form_manual_expense", clear_on_submit=True):
                m_merchant = st.text_input("Nama Merchant / Tempat", placeholder="Contoh: Burjo Rafa, Parkir, Warung Makan")
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    m_date = st.date_input("Tanggal Transaksi")
                with col_m2:
                    m_cat = st.selectbox("Kategori", ["Makanan & Minuman", "Belanja Harian", "Transportasi", "Kebutuhan Pokok", "Hiburan", "Tagihan & Utilitas", "Lainnya"])
                m_item = st.text_input("Deskripsi / Nama Item", placeholder="Contoh: Nasi Goreng + Es Teh")
                m_total = st.number_input("Nominal (Rp)", min_value=0.0, step=1000.0)
                if st.form_submit_button("Simpan Transaksi", use_container_width=True):
                    if not m_merchant.strip():
                        st.warning("Mohon isi nama merchant/tempat.")
                    elif m_total <= 0:
                        st.warning("Nominal transaksi harus lebih dari 0.")
                    else:
                        manual_payload = {
                            "merchant": m_merchant.strip(),
                            "transaction_date": str(m_date),
                            "total_amount": float(m_total),
                            "category": m_cat,
                            "items": [{"item_name": m_item.strip() if m_item.strip() else m_merchant.strip(), "quantity": 1.0, "total_price": float(m_total)}],
                        }
                        r_id = db.save_receipt_data(manual_payload, user_id=user_id)
                        st.toast(f"Transaksi berhasil disimpan! (ID: #{r_id})", icon="✅")
                        st.session_state["manual_success_notif"] = f"Transaksi sebesar Rp{m_total:,.0f} di {m_merchant.strip()} berhasil dicatat! (ID: #{r_id})"
                        st.rerun()

        elif input_method == "Pindai Kamera":
            st.markdown("##### Pindai Kamera")
            camera_img = st.camera_input("Ambil foto bukti bayar")
            if camera_img is not None:
                st.session_state.active_image = camera_img.getvalue()

        elif input_method == "Unggah Berkas":
            st.markdown("##### Unggah Berkas Transaksi")
            uploaded_file = st.file_uploader("Pilih gambar...", type=["jpg", "jpeg", "png", "heic", "heif"])
            if uploaded_file is not None:
                st.session_state.active_image = uploaded_file.getvalue()

        if input_method in ["Pindai Kamera", "Unggah Berkas"] and st.session_state.get("active_image"):
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

        total_spent = df["Nominal"].sum()
        remaining_budget = monthly_budget - total_spent
        spent_percent = min(100.0, (total_spent / monthly_budget) * 100.0) if monthly_budget > 0 else 0.0

        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Total Pengeluaran", f"Rp {total_spent:,.0f}")
        col_m2.metric("Sisa Anggaran", f"Rp {remaining_budget:,.0f}")
        col_m3.metric("Realisasi Anggaran", f"{spent_percent:.1f}%")

        st.progress(spent_percent / 100.0)
        st.write("")

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

        st.markdown("##### Tabel Riwayat Transaksi")
        st.dataframe(df, use_container_width=True)

        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Unduh Log Transaksi (CSV)",
            data=csv_data,
            file_name=f"expenselog_{current_user['username']}.csv",
            mime="text/csv",
        )

        st.divider()

        st.markdown("##### Analisis Pengeluaran")
        if st.button("Analisis Ringkasan Finansial"):
            with st.spinner("Menganalisis catatan pengeluaran..."):
                advice = tracker.generate_financial_advice(df.to_dict(orient="records"))
                st.markdown(advice)