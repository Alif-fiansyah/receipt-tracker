import io
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


def get_gemini_client():
    current_key = os.getenv("GEMINI_API_KEY")
    if not current_key:
        raise ValueError("GEMINI_API_KEY belum disetel!")
    return genai.Client(api_key=current_key)


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

def extract_receipt(image_input) -> dict:
    client = get_gemini_client()

    if isinstance(image_input, str):
        if not os.path.exists(image_input):
            raise FileNotFoundError(f"File gambar '{image_input}' tidak ditemukan.")
        img = Image.open(image_input)
    else:
        img = image_input

    # Konversi PIL Image ke bytes JPEG
    buffered = io.BytesIO()
    if img.mode != "RGB":
        img = img.convert("RGB")
    img.save(buffered, format="JPEG")
    img_bytes = buffered.getvalue()

    image_part = types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")

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

    # Model utama dan alternatif jika sedang overload
    kandidat_model = ["gemini-3.8-flash", "gemini-2.5-pro"]
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=ReceiptExtraction,
        temperature=0.1,
    )

    last_error = None

    for model_name in kandidat_model:
        # Coba hingga 3 kali percobaan untuk setiap model jika server sibuk (503/429)
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[prompt, image_part],
                    config=config,
                )
                parsed_data = ReceiptExtraction.model_validate_json(response.text)
                return parsed_data.model_dump()
            except Exception as e:
                last_error = e
                err_msg = str(e)
                # Jika server sibuk atau limit sementara, tunggu sebentar lalu coba lagi
                if "503" in err_msg or "429" in err_msg or "UNAVAILABLE" in err_msg:
                    time.sleep(2 * (attempt + 1))
                    continue
                else:
                    # Jika error model tidak ditemukan atau invalid, langsung ganti model
                    break

    raise RuntimeError(f"Gagal memproses struk setelah beberapa percobaan: {last_error}")


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
        model="gemini-3.8-flash",
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