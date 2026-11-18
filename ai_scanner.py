"""
AI Food Scanner Module
Menggunakan Google Gemini melalui SDK google-genai dengan Structured Output (Pydantic).
Dilengkapi optimasi gambar (Pillow), referensi gizi lokal, auto-retry, fallback model, dan portion scaling.
"""

import os
import io
import json
import time
from typing import Optional, Union, Any
from PIL import Image
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import database as db

load_dotenv()

# ==========================================
# KONSTANTA MODEL VALID GOOGLE AI STUDIO
# ==========================================
DEFAULT_MODEL = "gemini-2.5-flash"

AVAILABLE_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]


# ==========================================
# PYDANTIC SCHEMA
# ==========================================
class FoodNutrition(BaseModel):
    """Skema Pydantic untuk Structured Output dari Gemini AI."""
    nama_makanan: str = Field(description="Nama makanan atau hidangan yang terdeteksi secara spesifik")
    estimasi_berat_gram: float = Field(description="Perkiraan total berat makanan dalam satuan gram")
    kalori_kcal: float = Field(description="Estimasi total kalori dalam satuan kkal")
    protein_gram: float = Field(description="Estimasi total kandungan protein dalam satuan gram")
    karbohidrat_gram: float = Field(description="Estimasi total kandungan karbohidrat dalam satuan gram")
    lemak_gram: float = Field(description="Estimasi total kandungan lemak dalam satuan gram")
    serat_gram: float = Field(description="Estimasi total kandungan serat pangan (dietary fiber) dalam satuan gram")
    komponen_buah_sayur: str = Field(description="Daftar buah dan sayuran yang terdeteksi di piring (contoh: 'Brokoli, wortel, tomat', atau 'Tidak ada buah/sayur terdeteksi')")
    vitamin_mineral: str = Field(description="Ringkasan 3-5 vitamin dan mineral utama yang terkandung (contoh: 'Vitamin A, Vitamin C, Zat Besi, Kalium')")
    catatan_diet: str = Field(description="1 kalimat saran evaluasi nutrisi praktis yang disesuaikan dengan goal pengguna saat ini")


# ==========================================
# IMAGE OPTIMIZATION
# ==========================================
def optimize_image(image_input: Union[bytes, io.BytesIO, Image.Image, Any], max_dimension: int = 1024) -> Image.Image:
    if isinstance(image_input, (bytes, bytearray)):
        img = Image.open(io.BytesIO(image_input))
    elif isinstance(image_input, io.BytesIO):
        img = Image.open(image_input)
    elif isinstance(image_input, Image.Image):
        img = image_input.copy()
    else:
        img = Image.open(image_input)

    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    if max(img.size) > max_dimension:
        img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

    return img


# ==========================================
# CORE: ANALYZE FOOD IMAGE
# ==========================================
def analyze_food_image(
    image_file: Any,
    user_goal: str = "Maintenance",
    api_key: Optional[str] = None,
    model_name: str = DEFAULT_MODEL,
) -> FoodNutrition:
    effective_api_key = (api_key or "").strip() or os.getenv("GEMINI_API_KEY", "").strip()
    if not effective_api_key:
        raise ValueError(
            "GEMINI_API_KEY belum dikonfigurasi! "
            "Silakan masukkan API Key di sidebar atau tambahkan ke file .env."
        )

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        raise ImportError(
            "Library 'google-genai' belum terinstall. "
            "Jalankan: pip install google-genai"
        )

    processed_image = optimize_image(image_file)

    # Ambil konteks standar gizi dari tabel food_reference SQLite (jika tersedia)
    try:
        ref_context = db.get_reference_prompt_context()
    except Exception:
        ref_context = ""

    prompt = f"""Peran Anda adalah Ahli Gizi & Nutrisi Profesional AI.
Analisis foto makanan yang diberikan secara akurat dan objektif:

{ref_context}

1. Kenali nama makanan/hidangan dengan tepat (mendukung makanan khas Indonesia: Nasi Padang, Ayam Geprek, Rendang, Gado-gado, Bakso, Soto, Tempe Goreng, dll., maupun makanan internasional) serta gunakan acuan standar gizi di atas sebagai patokan proporsi gramasi.
2. Perkirakan total berat porsi dalam piring/wadah (gram) secara realistis.
3. Hitung estimasi kandungan gizi untuk porsi tersebut:
  - Kalori (kkal), Protein (gram), Karbohidrat (gram), Lemak (gram), dan Serat pangan (gram).
4. Identifikasi komponen buah dan sayuran yang terlihat pada makanan tersebut.
5. Sebutkan 3-5 vitamin dan mineral dominan yang terkandung dalam hidangan tersebut.
6. Berikan 1 kalimat catatan evaluasi nutrisi praktis sesuai goal pengguna: "{user_goal}".
  - Cutting: fokus kepadatan kalori, rasa kenyang, saran defisit aman.
  - Bulking: fokus kecukupan protein dan kalori untuk pertumbuhan otot.
  - Maintenance: fokus keseimbangan makronutrisi dan porsi harian.

PENTING: Kembalikan respon dalam format JSON sesuai skema yang ditentukan."""

    client = genai.Client(api_key=effective_api_key)

    # Susun daftar model berurutan: pilihan user + cadangan aktif
    candidate_models = []
    for m in [
        model_name,
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
    ]:
        if m and m not in candidate_models:
            candidate_models.append(m)

    response = None
    last_error = None

    for current_model in candidate_models:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=current_model,
                    contents=[processed_image, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=FoodNutrition,
                        temperature=0.2,
                    ),
                )
                break
            except Exception as e:
                last_error = e
                error_msg = str(e).lower()

                if "api_key_invalid" in error_msg or "permission_denied" in error_msg:
                    raise ValueError(
                        "❌ GEMINI_API_KEY tidak valid atau tidak memiliki izin akses. "
                        "Periksa kembali key Anda di Google AI Studio."
                    ) from e
                elif any(code in error_msg for code in ["503", "unavailable", "high demand", "overloaded", "resource_exhausted", "rate_limit", "429"]):
                    time.sleep(2)
                    continue
                elif "not_found" in error_msg or ("model" in error_msg and "not found" in error_msg):
                    break
                else:
                    raise RuntimeError(
                        f"Gagal memproses gambar dengan Gemini API: {str(e)}"
                    ) from e

        if response is not None:
            break

    if response is None:
        raise RuntimeError(
            f"⏳ Semua model Gemini sedang padat sementara. Silakan klik Analisis Nutrisi sekali lagi. Detail: {str(last_error)}"
        ) from last_error

    # --- Parse Response ---
    if hasattr(response, "parsed") and response.parsed is not None:
        if isinstance(response.parsed, FoodNutrition):
            return response.parsed
        if isinstance(response.parsed, dict):
            return FoodNutrition(**response.parsed)

    if hasattr(response, "text") and response.text:
        try:
            data = json.loads(response.text)
            return FoodNutrition(**data)
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            raise ValueError(
                f"Gagal mem-parsing respon AI menjadi data nutrisi. "
                f"Respon mentah: {response.text[:300]}"
            ) from e

    raise RuntimeError("Tidak ada respon yang valid diterima dari Gemini AI.")


# ==========================================
# PORTION SCALING
# ==========================================
def scale_nutrition(original: FoodNutrition, new_weight_gram: float) -> FoodNutrition:
    ratio = (float(new_weight_gram) / float(original.estimasi_berat_gram)
             if original.estimasi_berat_gram > 0 else 1.0)

    return FoodNutrition(
        nama_makanan=original.nama_makanan,
        estimasi_berat_gram=round(float(new_weight_gram), 1),
        kalori_kcal=round(max(0.0, original.kalori_kcal * ratio), 1),
        protein_gram=round(max(0.0, original.protein_gram * ratio), 1),
        karbohidrat_gram=round(max(0.0, original.karbohidrat_gram * ratio), 1),
        lemak_gram=round(max(0.0, original.lemak_gram * ratio), 1),
        serat_gram=round(max(0.0, original.serat_gram * ratio), 1),
        komponen_buah_sayur=original.komponen_buah_sayur,
        vitamin_mineral=original.vitamin_mineral,
        catatan_diet=original.catatan_diet,
    )
