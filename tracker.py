import os
import sys
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image
from pydantic import BaseModel, Field

import db

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("[-] Error: GEMINI_API_KEY belum diatur di file .env")
    sys.exit(1)

client = genai.Client(api_key=api_key)


# Definisi Skema Data Ekstraksi Struk
class ReceiptItem(BaseModel):
    item_name: str = Field(description="Nama barang atau jasa yang dibeli")
    quantity: float = Field(default=1.0, description="Jumlah item yang dibeli")
    total_price: float = Field(description="Total harga untuk item ini")


class ReceiptExtraction(BaseModel):
    merchant: str = Field(description="Nama toko, minimarket, resto, kafe, atau merchant")
    transaction_date: str = Field(description="Tanggal transaksi format YYYY-MM-DD. Jika tidak terlihat, gunakan tanggal hari ini.")
    category: str = Field(description="Pilih salah satu: Makanan & Minuman, Belanja Harian, Transportasi, Hiburan, Tagihan & Utilitas, atau Lainnya")
    items: list[ReceiptItem] = Field(description="Daftar item barang yang dibeli")
    total_amount: float = Field(description="Nominal akhir total pembayaran yang dibayarkan")


def scan_receipt_with_gemini(image_path: str) -> ReceiptExtraction:
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"File gambar '{image_path}' tidak ditemukan.")

    image = Image.open(image_path)

    prompt = """
    Kamu adalah sistem OCR dan ekstraksi struk pengeluaran otomatis.
    Tugasmu adalah menganalisis foto struk/nota pembayaran ini secara presisi.

    Aturan:
    1. Ambil nama toko (merchant) dengan jelas.
    2. Identifikasi tanggal transaksi (formatkan ke YYYY-MM-DD).
    3. Klasifikasikan pengeluaran ke dalam kategori yang paling tepat.
    4. Ekstrak nama item dan harganya. Jika struk terpotong atau tidak ada rincian item, masukkan 1 item representatif.
    5. Ambil nilai TOTAL pembayaran akhir yang valid (setelah diskon/pajak jika ada).
    """

    daftar_model = ["gemini-3.6-flash", "gemini-2.5-flash", "gemini-2.0-flash"]
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=ReceiptExtraction,
        temperature=0.1,
        tools=[],
    )

    for nama_model in daftar_model:
        try:
            response = client.models.generate_content(
                model=nama_model,
                contents=[prompt, image],
                config=config,
            )
            return ReceiptExtraction.model_validate_json(response.text)
        except Exception as e:
            if "503" in str(e) or "404" in str(e):
                time.sleep(1)
                continue
            raise e

    raise RuntimeError("Layanan Gemini sedang sibuk, coba beberapa saat lagi.")


def main():
    db.init_db()

    print("==================================================")
    print("      SMART EXPENSE TRACKER (OCR + GEMINI)        ")
    print("==================================================")

    if len(sys.argv) < 2:
        print("Penggunaan: python tracker.py <path_ke_foto_struk>")
        print("Contoh    : python tracker.py struk.jpg")
        return

    path_gambar = sys.argv[1]
    print(f"\n[*] Membaca dan menganalisis struk: {path_gambar} ...")

    try:
        hasil = scan_receipt_with_gemini(path_gambar)
    except Exception as err:
        print(f"[-] Gagal mengekstrak struk: {err}")
        return

    print("\n✅ Ekstraksi Berhasil!")
    print(f"- Toko / Merchant : {hasil.merchant}")
    print(f"- Tanggal         : {hasil.transaction_date}")
    print(f"- Kategori        : {hasil.category}")
    print(f"- Total Bayar     : Rp {hasil.total_amount:,.2f}")

    print("\n[Rincian Belanja]")
    for item in hasil.items:
        print(f"  • {item.item_name} (x{item.quantity}) - Rp {item.total_price:,.2f}")

    # Simpan ke SQLite
    receipt_id = db.save_receipt_data(hasil.model_dump())
    print(f"\n[+] Berhasil tersimpan ke database SQLite (ID Transaksi: {receipt_id})")


if __name__ == "__main__":
    main()

def generate_financial_advice(summary_text: str) -> str:
    """Menganalisis pola pengeluaran dan memberikan rekomendasi finansial singkat."""
    prompt = f"""
    Kamu adalah Financial Advisor profesional. Analisis ringkasan data transaksi pengeluaran berikut:
    {summary_text}

    Berikan 2 sampai 3 kalimat evaluasi finansial yang tajam, objektif, dan actionable dalam bahasa Indonesia formal tanpa basa-basi atau emoji berlebihan.
    """
    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        return f"Evaluasi gagal dimuat: {e}"