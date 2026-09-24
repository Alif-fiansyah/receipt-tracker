import os
import db
import pandas as pd
from PIL import Image
import streamlit as st
from tracker import scan_receipt_with_gemini, generate_financial_advice

st.set_page_config(
    page_title="ExpenseLog",
    page_icon="■",
    layout="wide",
    initial_sidebar_state="expanded",
)

db.init_db()


def load_css(file_path: str):
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


load_css("assets/style.css")

# Session State untuk Human-in-the-Loop & Advisor Cache
if "extracted_data" not in st.session_state:
    st.session_state.extracted_data = None
if "financial_advice" not in st.session_state:
    st.session_state.financial_advice = None

# Sidebar: Pengaturan Budget
with st.sidebar:
    st.markdown("#### Parameter Anggaran")
    monthly_budget = st.number_input(
        "Batas Anggaran Bulanan (Rp):",
        min_value=100000,
        max_value=100000000,
        value=3000000,
        step=250000,
    )
    st.caption("Ambang batas ini digunakan untuk mengukur rasio belanja riil.")

# Header
st.markdown("### ExpenseLog")
st.caption("Digitalisasi bukti bayar dan manajemen anggaran belanja.")
st.write("")

tab_scan, tab_history = st.tabs(["Pindai & Koreksi Dokumen", "Laporan & Log Transaksi"])

with tab_scan:
    col_input, col_result = st.columns([1, 1], gap="large")

    with col_input:
        st.markdown("##### Sumber Berkas")

        metode_input = st.radio(
            "Pilih Metode:",
            ["Unggah Berkas", "Tangkap Kamera"],
            horizontal=True,
            label_visibility="collapsed",
        )

        image_source = None

        if metode_input == "Unggah Berkas":
            uploaded_file = st.file_uploader(
                "Format: PNG, JPG, JPEG",
                type=["jpg", "jpeg", "png"],
                label_visibility="collapsed",
            )
            if uploaded_file:
                image_source = Image.open(uploaded_file)
        else:
            camera_file = st.camera_input(
                "Arahkan lensa tepat ke struk pembayaran",
                label_visibility="collapsed",
            )
            if camera_file:
                image_source = Image.open(camera_file)

        if image_source:
            st.image(image_source, caption="Pratinjau Berkas", use_container_width=True)
            if st.button("Pindai Bukti Bayar", type="primary"):
                temp_path = "temp_receipt.jpg"
                image_source.save(temp_path)

                with st.spinner("Memproses digitalisasi dokumen..."):
                    try:
                        hasil = scan_receipt_with_gemini(temp_path)
                        st.session_state.extracted_data = hasil.model_dump()
                        st.rerun()
                    except Exception as err:
                        st.error(f"Gagal memproses dokumen: {err}")
                    finally:
                        if os.path.exists(temp_path):
                            os.remove(temp_path)

    with col_result:
        st.markdown("##### Verifikasi & Konfirmasi Data")

        if st.session_state.extracted_data is not None:
            data = st.session_state.extracted_data

            st.info("Periksa dan koreksi data hasil pembacaan sebelum disimpan.")

            # Form Koreksi (Human-in-the-Loop)
            with st.form("form_koreksi"):
                val_merchant = st.text_input("Nama Merchant", value=data.get("merchant", ""))
                c_tgl, c_kat = st.columns(2)
                with c_tgl:
                    val_date = st.text_input("Tanggal Transaksi", value=data.get("transaction_date", ""))
                with c_kat:
                    val_cat = st.selectbox(
                        "Kategori",
                        ["Makanan & Minuman", "Belanja Harian", "Transportasi", "Hiburan", "Tagihan & Utilitas", "Lainnya"],
                        index=0 if data.get("category") not in ["Makanan & Minuman", "Belanja Harian", "Transportasi", "Hiburan", "Tagihan & Utilitas", "Lainnya"] else ["Makanan & Minuman", "Belanja Harian", "Transportasi", "Hiburan", "Tagihan & Utilitas", "Lainnya"].index(data.get("category")),
                    )

                val_total = st.number_input("Total Pembayaran (Rp)", value=float(data.get("total_amount", 0.0)), step=1000.0)

                st.markdown("###### Rincian Item Terdeteksi")
                items = data.get("items", [])
                st.dataframe(pd.DataFrame(items), use_container_width=True, hide_index=True)

                simpan_btn = st.form_submit_button("Simpan ke Database", type="primary")

                if simpan_btn:
                    payload = {
                        "merchant": val_merchant,
                        "transaction_date": val_date,
                        "category": val_cat,
                        "total_amount": val_total,
                        "items": items,
                    }
                    receipt_id = db.save_receipt_data(payload)
                    st.session_state.extracted_data = None
                    st.success(f"Transaksi terverifikasi dan disimpan dengan ID #{receipt_id}")
                    st.rerun()
        else:
            st.markdown("<p style='color: #8b949e;'>Pilih dan ekstrak dokumen di sisi kiri untuk memunculkan formulir verifikasi.</p>", unsafe_allow_html=True)

with tab_history:
    records = db.get_all_receipts()

    if records:
        df = pd.DataFrame(
            records,
            columns=["ID", "Merchant", "Tgl Struk", "Total", "Kategori", "Waktu Pindai"],
        )

        total_belanja = df["Total"].sum()
        total_transaksi = len(df)
        rata_rata = total_belanja / total_transaksi if total_transaksi > 0 else 0

        # Feature: Budget Progress Bar
        budget_ratio = min(total_belanja / monthly_budget, 1.0)
        persen_pakai = (total_belanja / monthly_budget) * 100

        st.markdown(f"**Pemakaian Anggaran:** {persen_pakai:.1f}% dari kuota Rp {monthly_budget:,.2f}")
        st.progress(budget_ratio)
        st.write("")

        # Baris Metrik Utama
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.markdown(
                f"""
                <div class="metric-box">
                    <div class="metric-label">Akumulasi Pengeluaran</div>
                    <div class="metric-value">Rp {total_belanja:,.2f}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_m2:
            st.markdown(
                f"""
                <div class="metric-box">
                    <div class="metric-label">Volume Transaksi</div>
                    <div class="metric-value">{total_transaksi} Dokumen</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_m3:
            st.markdown(
                f"""
                <div class="metric-box">
                    <div class="metric-label">Nilai Rata-Rata</div>
                    <div class="metric-value">Rp {rata_rata:,.2f}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Feature: AI Financial Health Advisor
        st.write("")
        c_adv_btn, c_adv_space = st.columns([1, 3])
        with c_adv_btn:
            if st.button("Analisis Ringkasan Finansial"):
                ringkasan_teks = f"Total belanja: Rp {total_belanja}. Jumlah struk: {total_transaksi}. Rincian per kategori: {df.groupby('Kategori')['Total'].sum().to_dict()}."
                with st.spinner("Menghitung pola konsumsi..."):
                    st.session_state.financial_advice = generate_financial_advice(ringkasan_teks)

        if st.session_state.financial_advice:
            st.markdown(
                f"""
                <div class="advisor-card">
                    <div class="advisor-title">Analisis Ringkasan Finansial</div>
                    <div class="advisor-body">{st.session_state.financial_advice}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.write("")

        # Visualisasi (Grafik Batang Kategori & Tren Harian)
        col_chart1, col_chart2 = st.columns(2, gap="medium")

        with col_chart1:
            st.markdown("##### Distribusi Kategori")
            kategori_summary = df.groupby("Kategori")["Total"].sum()
            st.bar_chart(kategori_summary, color="#1f6feb")

        with col_chart2:
            st.markdown("##### Tren Pengeluaran Harian")
            # Urutkan berdasarkan tanggal struk
            daily_trend = df.groupby("Tgl Struk")["Total"].sum().reset_index()
            daily_trend = daily_trend.set_index("Tgl Struk")
            st.area_chart(daily_trend, color="#238636")

        st.divider()

        # Log Data & Tombol Ekspor CSV
        st.markdown("##### Catatan Log Transaksi")
        c_tbl, c_export = st.columns([4, 1])

        df_display = df.copy()
        df_display["Total"] = df_display["Total"].apply(lambda x: f"Rp {x:,.2f}")
        st.dataframe(df_display.drop(columns=["ID"]), use_container_width=True, hide_index=True)

        # Feature: Ekspor CSV
        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Unduh Log Transaksi (CSV)",
            data=csv_data,
            file_name="rekap_pengeluaran.csv",
            mime="text/csv",
        )
    else:
        st.caption("Belum ada data transaksi yang tersimpan dalam sistem lokal.")