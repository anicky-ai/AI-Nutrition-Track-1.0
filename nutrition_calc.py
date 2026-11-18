"""
Modul Kalkulator Target Nutrisi (BMR, TDEE, Makronutrisi)
Berdasarkan rumus Mifflin-St Jeor dan distribusi makronutrisi sesuai blueprint.
"""

from typing import Dict

ACTIVITY_FACTORS: Dict[str, float] = {
    "Sedentary": 1.2,      # Sedikit atau tidak berolahraga
    "Light": 1.375,        # Olahraga ringan 1-3 hari/minggu
    "Moderate": 1.55,      # Olahraga sedang 3-5 hari/minggu
    "Active": 1.725,       # Olahraga berat 6-7 hari/minggu
    "Very Active": 1.9     # Latihan fisik intensif / pekerjaan fisik berat
}

GOAL_CALORIE_ADJUSTMENTS: Dict[str, float] = {
    "Cutting": -400.0,     # Defisit kalori untuk penurunan lemak
    "Maintenance": 0.0,    # Menjaga berat badan stabil
    "Bulking": 300.0       # Surplus kalori untuk pembentukan massa otot
}


def calculate_bmr(berat_kg: float, tinggi_cm: float, usia_tahun: int, jenis_kelamin: str) -> float:
    """
    Menghitung Basal Metabolic Rate (BMR) menggunakan formula Mifflin-St Jeor.
    - Laki-laki: (10 * berat) + (6.25 * tinggi) - (5 * usia) + 5
    - Perempuan: (10 * berat) + (6.25 * tinggi) - (5 * usia) - 161
    """
    base = (10.0 * berat_kg) + (6.25 * tinggi_cm) - (5.0 * usia_tahun)
    if jenis_kelamin.lower() in ["laki-laki", "pria", "male"]:
        return base + 5.0
    else:
        return base - 161.0


def calculate_tdee(bmr: float, tingkat_aktivitas: str) -> float:
    """Menghitung Total Daily Energy Expenditure (TDEE)."""
    factor = ACTIVITY_FACTORS.get(tingkat_aktivitas, 1.2)
    return bmr * factor


def calculate_nutrition_targets(
    berat_badan: float,
    tinggi_badan: float,
    usia: int,
    jenis_kelamin: str,
    tingkat_aktivitas: str,
    goal: str
) -> Dict[str, float]:
    """
    Menghitung target kalori dan makronutrisi lengkap:
    - BMR & TDEE
    - Target Kalori berdasarkan goal (Cutting: -400, Maintenance: 0, Bulking: +300)
    - Protein: 2.0 gram per kg berat badan (4 kkal/gram)
    - Lemak: 25% dari total kalori dibagi 9 (9 kkal/gram)
    - Karbohidrat: Sisa kalori dibagi 4 (4 kkal/gram)
    """
    bmr = calculate_bmr(berat_badan, tinggi_badan, usia, jenis_kelamin)
    tdee = calculate_tdee(bmr, tingkat_aktivitas)
    
    adjustment = GOAL_CALORIE_ADJUSTMENTS.get(goal, 0.0)
    target_kalori = max(1000.0, tdee + adjustment)
    
    # Protein: 2.0g per kg berat badan
    target_protein = berat_badan * 2.0
    protein_kalori = target_protein * 4.0
    
    # Lemak: 25% dari total kalori
    lemak_kalori = target_kalori * 0.25
    target_lemak = lemak_kalori / 9.0
    
    # Karbohidrat: sisa kalori dibagi 4
    sisa_kalori = max(0.0, target_kalori - protein_kalori - lemak_kalori)
    target_karbo = sisa_kalori / 4.0
    
    return {
        "bmr": round(bmr, 1),
        "tdee": round(tdee, 1),
        "target_kalori": round(target_kalori, 1),
        "target_protein": round(target_protein, 1),
        "target_karbo": round(target_karbo, 1),
        "target_lemak": round(target_lemak, 1),
    }
