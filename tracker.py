import io
import json
import os
import re
import sys
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image
from pydantic import BaseModel, Field

# Registrasi dukungan format HEIC/HEIF dari kamera iPhone
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

import db

load_dotenv()


def get_gemini_client():
    # Cek kunci di st.secrets jika berjalan di Streamlit Cloud, fallback ke os.getenv
    current_key = os.getenv("GEMINI_API_KEY")
    if not current_key:
        try:
            import streamlit as st
            current_key = st.secrets.get("GEMINI_API_KEY")
        except Exception:
            pass

    if not current_key:
        raise ValueError("GEMINI_API_KEY belum disetel di environment atau Streamlit Secrets!")
    return genai.Client(api_key=current_key)


class ReceiptItem(BaseModel):
    item_name: str = Field(description="Nama barang atau jasa yang dibeli")
    quantity: float = Field(default=1.0, description="Jumlah item yang dibeli")
    total_price: float = Field(description="Total harga untuk item ini")


class ReceiptExtraction(BaseModel):
    merchant: str = Field(description="Nama toko, minimarket, resto, kafe, atau tujuan transfer/QRIS")
    transaction_date: str = Field(description="Tanggal transaksi format YYYY-MM-DD")
    category: str = Field(description="Pilih salah satu: Makanan & Minuman, Belanja Harian, Transportasi, Hiburan, Tagihan & Utilitas, atau Lainnya")
    items: list[ReceiptItem] = Field(description="Daftar item barang yang dibeli")
    total_amount: float = Field(description="Nominal akhir total pembayaran yang dibayarkan")


def clean_json_text(raw_text: str) -> str:
    """Membersihkan markdown fences ```json ... ``` dari respons AI."""
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip())
    return cleaned.strip()


def extract_receipt(image_input) -> dict:
    client = get_gemini_client()

    if isinstance(image_input, str):
        if not os.path.exists(image_input):
            raise FileNotFoundError(f"File gambar '{image_input}' tidak ditemukan.")
        img = Image.open(image_input)
    else:
        img = image_input

    # 1. Konversi mode warna agar aman ke format JPEG
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1])
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # 2. Resize proporsional agar hemat token & bandwidth
    max_dim = 1600
    if max(img.size) > max_dim:
        img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

    # 3. Kompresi JPEG
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=85, optimize=True)
    img_bytes = buffered.getvalue()

    image_part = types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")

    prompt = """
    Kamu adalah sistem OCR dan analisis bukti bayar otomatis (struk belanja fisik maupun tangkapan layar m-banking / QRIS).
    Ekstrak informasi dari gambar ke format JSON murni sesuai skema berikut:
    {
      "merchant": "Nama penerima, merchant, toko, atau kafe",
      "transaction_date": "YYYY-MM-DD",
      "category": "Makanan & Minuman | Belanja Harian | Transportasi | Hiburan | Tagihan & Utilitas | Lainnya",
      "items": [
        {"item_name": "Nama item atau transaksi", "quantity": 1.0, "total_price": 0.0}
      ],
      "total_amount": 0.0
    }

    Aturan:
    1. Pastikan total_amount dan total_price berupa angka (float/integer), jangan sertakan simbol mata uang atau titik ribuan.
    2. Jika tanggal berupa format teks (misal '25 Sep 2026'), konversikan ke angka '2026-09-25'.
    3. Jika rincian item belanja tidak tertulis satuan (misal pada bukti transfer QRIS), isi 1 item dengan item_name sesuai tujuan transaksi dan total_price sama dengan total_amount.
    4. Kembalikan HANYA teks JSON valid tanpa tambahan penjelasan lain.
    """

    kandidat_model = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0.1,
    )

    last_error = None

    for model_name in kandidat_model:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[prompt, image_part],
                    config=config,
                )
                raw_json = clean_json_text(response.text)
                data_dict = json.loads(raw_json)

                # Validasi format dengan Pydantic
                validated = ReceiptExtraction.model_validate(data_dict)
                return validated.model_dump()
            except Exception as e:
                last_error = e
                err_msg = str(e)
                if any(k in err_msg for k in ["503", "429", "UNAVAILABLE", "ResourceExhausted"]):
                    time.sleep(2 * (attempt + 1))
                    continue
                break

    raise RuntimeError(f"Gagal memproses struk: {last_error}")

scan_receipt_with_gemini = extract_receipt


def generate_financial_advice(summary_text) -> str:
    """Menganalisis pola pengeluaran dan memberikan rekomendasi finansial singkat."""
    client = get_gemini_client()
    prompt = f"""
    Kamu adalah Financial Advisor profesional. Analisis ringkasan data transaksi pengeluaran berikut:
    {summary_text}

    Berikan 2 sampai 3 kalimat evaluasi finansial yang tajam, objektif, dan actionable dalam bahasa Indonesia formal tanpa basa-basi atau emoji berlebihan.
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        return f"Evaluasi gagal dimuat: {e}"


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
        hasil = extract_receipt(path_gambar)
    except Exception as err:
        print(f"[-] Gagal mengekstrak struk: {err}")
        return

    print("\n✅ Ekstraksi Berhasil!")
    print(f"- Toko / Merchant : {hasil['merchant']}")
    print(f"- Tanggal         : {hasil['transaction_date']}")
    print(f"- Kategori        : {hasil['category']}")
    print(f"- Total Bayar     : Rp {hasil['total_amount']:,.2f}")

    print("\n[Rincian Belanja]")
    for item in hasil.get("items", []):
        print(f"  • {item['item_name']} (x{item['quantity']}) - Rp {item['total_price']:,.2f}")


if __name__ == "__main__":
    main()