from datetime import datetime
import calendar
import calendar
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

if "current_user" not in st.session_state:
    st.session_state["current_user"] = None


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
if not st.session_state.get("current_user"):
    st.markdown("""
    <style>
    .auth-hero-title {
        font-size: 2.3rem;
        font-weight: 800;
        line-height: 1.15;
        background: linear-gradient(135deg, #ffffff 0%, #9ca3af 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 8px;
    }
    .auth-feature-card {
        padding: 12px 14px;
        margin-bottom: 12px;
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

    col_hero, col_gap, col_auth = st.columns([1.15, 0.1, 1.0])

    with col_hero:
        st.markdown('<div class="auth-hero-title">ExpenseLog.</div>', unsafe_allow_html=True)
        st.markdown('<p style="font-size: 0.95rem; color: #8b949e; line-height: 1.5; margin-bottom: 22px;">Platform cerdas pencatatan transaksi harian, automasi ekstraksi nota belanja berbasis AI, dan manajemen anggaran keuangan pribadi secara presisi.</p>', unsafe_allow_html=True)

        st.markdown("""
        <div class="auth-feature-card">
            <div style="font-weight: 600; font-size: 0.88rem; color: #f0f2f6;">Ekstraksi Nota AI & OCR</div>
            <div style="font-size: 0.78rem; color: #8b949e; margin-top: 3px;">Pindai struk fisik secara otomatis tanpa perlu mengetik ulang merchant, tanggal, dan nominal.</div>
        </div>
        <div class="auth-feature-card">
            <div style="font-weight: 600; font-size: 0.88rem; color: #f0f2f6;">Analitik Tren & Kategori</div>
            <div style="font-size: 0.78rem; color: #8b949e; margin-top: 3px;">Visualisasi interaktif riwayat harian dan proporsi alokasi dana secara real-time.</div>
        </div>
        <div class="auth-feature-card">
            <div style="font-weight: 600; font-size: 0.88rem; color: #f0f2f6;">Financial AI Advisor</div>
            <div style="font-size: 0.78rem; color: #8b949e; margin-top: 3px;">Evaluasi pola belanja terintegrasi untuk mencegah defisit anggaran bulanan Anda.</div>
        </div>
        """, unsafe_allow_html=True)

    with col_auth:
        tab_login, tab_register = st.tabs(["Masuk", "Daftar Akun"])
        with tab_login:
            st.markdown("##### Masuk ke Akun Anda")
            with st.form("form_login"):
                login_user = st.text_input("Username").strip()
                login_pwd = st.text_input("Password", type="password")
                btn_login = st.form_submit_button("Masuk", type="primary", use_container_width=True)

                if btn_login:
                    if not login_user or not login_pwd:
                        st.warning("Username dan Password wajib diisi.")
                    else:
                        user_data = db.authenticate_user(login_user, login_pwd)
                        if user_data:
                            st.session_state.current_user = user_data
                            st.toast(f"Selamat datang kembali, {user_data.get('username', 'User')}!", icon="👋")
                            st.rerun()
                        else:
                            st.error("Username atau password salah.")

        with tab_register:
            st.markdown("##### Buat Akun Baru")
            with st.form("form_register"):
                reg_user = st.text_input("Username Baru").strip()
                reg_pwd = st.text_input("Password", type="password")
                reg_budget = st.number_input("Target Anggaran Bulanan (Rp)", min_value=0, value=2500000, step=100000, format="%d")
                btn_reg = st.form_submit_button("Daftar Akun", type="primary", use_container_width=True)

                if btn_reg:
                    if not reg_user or not reg_pwd:
                        st.warning("Semua kolom registrasi wajib diisi.")
                    else:
                        success = db.create_user(reg_user, reg_pwd, monthly_budget=float(reg_budget))
                        if success:
                            st.success("Akun berhasil dibuat! Silakan beralih ke tab Masuk.")
                        else:
                            st.error("Username sudah terdaftar. Gunakan username lain.")

    st.stop()

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
        format="%d",
        label_visibility="collapsed",
        help=f"Nilai saat ini: Rp {int(saved_budget):,}"
    )
    st.caption(f"Nominal: **Rp {int(monthly_budget):,}**")

    if hasattr(db, "set_user_budget") and monthly_budget != saved_budget:
        db.set_user_budget(user_id, monthly_budget)

        # Sinkronisasi data riwayat transaksi dengan database utama
    all_receipts = db.get_all_receipts(user_id=user_id) if hasattr(db, "get_all_receipts") else []
    total_spent = sum(r[3] for r in all_receipts if len(r) > 3 and r[3] is not None)
    sisa = monthly_budget - total_spent
    ratio = min(total_spent / monthly_budget, 1.0) if monthly_budget > 0 else 0.0

    st.progress(ratio)

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.caption("Terpakai")
        st.markdown(f"<span style='font-size: 0.95rem; font-weight: 600; color: #e6edf3;'>Rp{total_spent:,.0f}</span>", unsafe_allow_html=True)
    with col_s2:
        st.caption("Sisa Saldo")
        sisa_color = "#3fb950" if sisa >= 0 else "#f85149"
        st.markdown(f"<span style='font-size: 0.95rem; font-weight: 600; color: {sisa_color};'>Rp{sisa:,.0f}</span>", unsafe_allow_html=True)
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    st.caption("TARGET & ALOKASI TABUNGAN")
    
    with st.expander("Kalkulator Rencana Tabungan", expanded=False):
        target_tabungan = st.number_input(
            "Target Tabungan (Rp)",
            min_value=0,
            value=500000,
            step=50000,
            format="%d",
            help="Jumlah uang yang ingin Anda amankan/tabung bulan ini."
        )
        st.caption(f"Nominal: **Rp {int(target_tabungan):,}**")
        anggaran_bersih = max(monthly_budget - target_tabungan, 0)
        st.markdown(
            f"""
            <div style="background: rgba(255,255,255,0.03); padding: 10px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.08); margin-top: 8px;">
                <div style="font-size: 0.75rem; color: #8b949e;">Maksimal Belanja Bersih:</div>
                <div style="font-size: 0.95rem; font-weight: 600; color: #58a6ff;">Rp{anggaran_bersih:,.0f}</div>
                <div style="font-size: 0.72rem; color: #8b949e; margin-top: 4px;">Setelah disisihkan untuk tabungan</div>
            </div>
            """,
            unsafe_allow_html=True
        )


# Wadah Konten Utama Terpusat
_, col_center, _ = st.columns([0.18, 0.64, 0.18])
with col_center:
    tab_input, tab_history, tab_budget = st.tabs(["Catat Transaksi", "Log & Analisis Transaksi", "Kantong Anggaran"])

# --- TAB 1: INPUT STRUK ---
with tab_input:
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
        df["Tanggal_dt"] = pd.to_datetime(df["Tanggal"], errors="coerce")

        # 1. Metrik Utama
        total_spent = df["Nominal"].sum()
        remaining_budget = monthly_budget - total_spent
        spent_percent = min(100.0, (total_spent / monthly_budget) * 100.0) if monthly_budget > 0 else 0.0

        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Total Pengeluaran", f"Rp {total_spent:,.0f}")
        col_m2.metric("Sisa Anggaran", f"Rp {remaining_budget:,.0f}")
        col_m3.metric("Realisasi Anggaran", f"{spent_percent:.1f}%")
        st.progress(spent_percent / 100.0)

        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

                # 2. Kontrol Filter Lengkap (3 Kolom)
        col_f1, col_f2, col_f3 = st.columns([1, 1, 1.5])
        with col_f1:
            time_filter = st.selectbox("Rentang Waktu", ["Semua Waktu", "30 Hari Terakhir", "7 Hari Terakhir"])
        with col_f2:
            available_cats = ["Semua Kategori"] + sorted(list(df["Kategori"].dropna().unique()))
            category_filter = st.selectbox("Kategori", available_cats)
        with col_f3:
            search_query = st.text_input("Cari Merchant / Toko", placeholder="Ketik nama tempat...")

        # Terapkan Filter
        filtered_df = df.copy()
        if time_filter == "7 Hari Terakhir":
            cutoff = pd.Timestamp.now() - pd.Timedelta(days=7)
            filtered_df = filtered_df[filtered_df["Tanggal_dt"] >= cutoff]
        elif time_filter == "30 Hari Terakhir":
            cutoff = pd.Timestamp.now() - pd.Timedelta(days=30)
            filtered_df = filtered_df[filtered_df["Tanggal_dt"] >= cutoff]

        if category_filter != "Semua Kategori":
            filtered_df = filtered_df[filtered_df["Kategori"] == category_filter]

        if search_query.strip():
            filtered_df = filtered_df[filtered_df["Merchant"].str.contains(search_query.strip(), case=False, na=False)]

        # 3. Visualisasi Analisis Ganda
        col_g1, col_g2 = st.columns([1.2, 1], gap="medium")

        with col_g1:
            st.markdown("##### Tren Harian")
            if not filtered_df.empty:
                daily_df = filtered_df.groupby("Tanggal", as_index=False)["Nominal"].sum().sort_values("Tanggal")
                line_chart = (
                    alt.Chart(daily_df)
                    .mark_line(point=True, color="#ff4b4b")
                    .encode(
                        x=alt.X("Tanggal:N", title="Tanggal", axis=alt.Axis(labelAngle=-45)),
                        y=alt.Y("Nominal:Q", title="Total Belanja (Rp)"),
                        tooltip=["Tanggal", alt.Tooltip("Nominal:Q", format=",.0f")],
                    )
                    .properties(height=260)
                )
                st.altair_chart(line_chart, use_container_width=True)
            else:
                st.caption("Tidak ada data pada filter ini.")

        with col_g2:
            st.markdown("##### Pengeluaran per Kategori")
            if not filtered_df.empty:
                cat_df = filtered_df.groupby("Kategori", as_index=False)["Nominal"].sum()
                donut_chart = (
                    alt.Chart(cat_df)
                    .mark_arc(innerRadius=45)
                    .encode(
                        theta=alt.Theta("Nominal:Q"),
                        color=alt.Color("Kategori:N", legend=alt.Legend(title="Kategori", orient="bottom")),
                        tooltip=["Kategori", alt.Tooltip("Nominal:Q", format=",.0f")],
                    )
                    .properties(height=260)
                )
                st.altair_chart(donut_chart, use_container_width=True)
            else:
                st.caption("Tidak ada data pada filter ini.")

        st.divider()

        # 4. Tabel Riwayat Berformat Rupiah
        st.markdown("##### Riwayat Transaksi")
        display_df = filtered_df[["ID", "Merchant", "Tanggal", "Nominal", "Kategori", "Waktu Simpan"]].copy()
        display_df["Nominal"] = display_df["Nominal"].apply(lambda v: f"Rp {v:,.0f}")
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        # Tombol CSV & Aksi Kelola Transaksi
        col_act1, col_act2 = st.columns([1, 1])
        with col_act1:
            csv_data = filtered_df[["ID", "Merchant", "Tanggal", "Nominal", "Kategori", "Waktu Simpan"]].to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Unduh Riwayat Terpilih (CSV)",
                data=csv_data,
                file_name=f"transaksi_{current_user['username']}.csv",
                mime="text/csv",
                use_container_width=True,
            )

        with col_act2:
            with st.popover("Hapus Transaksi", use_container_width=True):
                st.write("**Pilih Transaksi yang Ingin Dihapus**")
                tx_options = {f"#{row.ID} - {row.Merchant} (Rp {row.Nominal:,.0f})": row.ID for row in df.itertuples()}
                selected_label = st.selectbox("Daftar Transaksi:", list(tx_options.keys()))
                if st.button("Konfirmasi Hapus", type="primary", use_container_width=True):
                    target_id = tx_options[selected_label]
                    if hasattr(db, "delete_receipt") and db.delete_receipt(target_id, user_id=user_id):
                        st.success(f"Transaksi {selected_label} berhasil dihapus.")
                        st.rerun()
                    else:
                        st.error("Gagal menghapus transaksi dari database.")

        st.divider()

                # 5. Financial AI Advisor Interaktif
        st.markdown("##### Konsultan Keuangan AI")
        st.caption("Dapatkan evaluasi pengeluaran instan dan saran taktis dari catatan transaksi Anda.")

        if "ai_advice_result" not in st.session_state:
            st.session_state.ai_advice_result = None

        col_q1, col_q2, col_q3 = st.columns(3)
        ask_trigger = False
        query_context = ""

        with col_q1:
            if st.button("Di mana paling boros?", use_container_width=True):
                query_context = "Analisis di kategori dan pos belanja mana pengguna paling boros, serta berikan rekomendasi penghematannya."
                ask_trigger = True
        with col_q2:
            if st.button("Tips sisa anggaran", use_container_width=True):
                query_context = f"Dengan sisa anggaran Rp{remaining_budget:,.0f} dan total belanja Rp{total_spent:,.0f}, berikan langkah taktis agar keuangan bertahan sampai akhir bulan."
                ask_trigger = True
        with col_q3:
            if st.button("Ringkasan gaya hidup", use_container_width=True):
                query_context = "Evaluasi pola gaya hidup pengguna berdasarkan waktu belanja, merchant yang sering dikunjungi, dan frekuensi transaksi."
                ask_trigger = True

        custom_query = st.text_input("Atau ajukan pertanyaan spesifik tentang riwayat pengeluaran Anda:", placeholder="Contoh: Apakah pengeluaran makan saya wajar?")
        if st.button("Tanyakan ke AI", type="secondary"):
            if custom_query.strip():
                query_context = custom_query.strip()
                ask_trigger = True
            else:
                st.warning("Silakan ketik pertanyaan terlebih dahulu.")

        if ask_trigger and query_context:
            with st.spinner("AI sedang menganalisis data riwayat transaksi Anda..."):
                try:
                    records = df.to_dict(orient="records")
                    if hasattr(tracker, "generate_custom_advice"):
                        response = tracker.generate_custom_advice(records, query_context)
                    else:
                        response = tracker.generate_financial_advice(records)
                    st.session_state.ai_advice_result = response
                except Exception as e:
                    st.session_state.ai_advice_result = f"Gagal menghasilkan analisis: {e}"

        if st.session_state.ai_advice_result:
            st.markdown(
                f"""
                <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 16px; margin-top: 14px;">
                    <div style="font-weight: 600; font-size: 0.9rem; color: #58a6ff; margin-bottom: 8px;">Rekomendasi AI:</div>
                    <div style="font-size: 0.88rem; color: #e6edf3; line-height: 1.6;">
                        {st.session_state.ai_advice_result}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )


# --- TAB 3: ALOKASI & KANTONG ANGGARAN ---
with tab_budget:
    st.markdown("##### Alokasi Anggaran per Kategori")
    st.caption("Bagi pagu bulanan Anda ke masing-masing pos pengeluaran untuk mencegah defisit anggaran.")

    # Ambil transaksi user untuk kalkulasi per kategori
    raw_data_b = db.get_all_receipts(user_id=user_id) if hasattr(db, "get_all_receipts") else []
    cat_spent_map = {}
    for r in raw_data_b:
        if len(r) > 4:
            c = r[4] or "Lainnya"
            nom = r[3] or 0.0
            cat_spent_map[c] = cat_spent_map.get(c, 0.0) + nom

    default_categories = [
        "Makanan & Minuman",
        "Belanja Harian",
        "Transportasi",
        "Kebutuhan Pokok",
        "Hiburan",
        "Tagihan & Utilitas",
        "Lainnya"
    ]

    if "category_budgets" not in st.session_state:
        st.session_state.category_budgets = {
            "Makanan & Minuman": 1000000,
            "Belanja Harian": 500000,
            "Transportasi": 300000,
            "Tagihan & Utilitas": 400000,
            "Hiburan": 200000,
            "Kebutuhan Pokok": 100000,
            "Lainnya": 0
        }

    # Layout kartu alokasi kantong
    cols_envelope = st.columns(2, gap="medium")
    for idx, category_name in enumerate(default_categories):
        target_col = cols_envelope[idx % 2]
        with target_col:
            current_allocated = st.session_state.category_budgets.get(category_name, 0)
            spent = cat_spent_map.get(category_name, 0.0)
            
            with st.container():
                st.markdown(
                    f"""
                    <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.07); border-radius: 8px; padding: 12px; margin-bottom: 12px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                            <span style="font-weight: 600; font-size: 0.9rem; color: #f0f2f6;">{category_name}</span>
                            <span style="font-size: 0.75rem; color: #8b949e;">Terpakai: Rp{spent:,.0f}</span>
                        </div>
                    """,
                    unsafe_allow_html=True
                )
                
                new_alloc = st.number_input(
                    f"Pagu {category_name}",
                    min_value=0,
                    value=int(current_allocated),
                    step=50000,
                    format="%d",
                    key=f"input_alloc_{category_name}",
                    label_visibility="collapsed"
                )
                st.session_state.category_budgets[category_name] = new_alloc
                
                ratio = min(spent / new_alloc, 1.0) if new_alloc > 0 else (1.0 if spent > 0 else 0.0)
                st.progress(ratio)
                
                sisa_kantong = new_alloc - spent
                status_color = "#3fb950" if sisa_kantong >= 0 else "#f85149"
                status_text = f"Sisa: Rp{sisa_kantong:,.0f}" if sisa_kantong >= 0 else f"Overbudget: Rp{abs(sisa_kantong):,.0f}"
                
                st.markdown(
                    f"""
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 4px; font-size: 0.75rem;">
                            <span style="color: #8b949e;">Pagu: Rp{new_alloc:,.0f}</span>
                            <span style="font-weight: 600; color: {status_color};">{status_text}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

