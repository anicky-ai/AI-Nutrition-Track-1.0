"""
Database Module — Operasi CRUD SQLite untuk AI Nutrition Tracker.
Thread-safe untuk Streamlit multi-thread runtime.
"""

import sqlite3
import os
import threading
from typing import Optional, Dict, List, Any

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nutrition.db")

# Thread-local storage agar setiap Streamlit thread punya koneksi sendiri
_local = threading.local()
_init_lock = threading.Lock()
_initialized = False


def get_connection() -> sqlite3.Connection:
    """
    Mengembalikan koneksi SQLite per-thread (thread-local).
    Koneksi di-cache agar tidak membuka/tutup terus-menerus.
    """
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging: aman multi-thread
        _local.conn = conn
    return conn


def init_db():
    """Inisialisasi tabel database (hanya berjalan sekali per proses)."""
    global _initialized
    if _initialized:
        return
    with _init_lock:
        if _initialized:
            return
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_profile (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nama TEXT NOT NULL,
                jenis_kelamin TEXT NOT NULL,
                usia INTEGER NOT NULL,
                berat_badan REAL NOT NULL,
                tinggi_badan REAL NOT NULL,
                tingkat_aktivitas TEXT NOT NULL,
                goal TEXT NOT NULL,
                target_kalori REAL NOT NULL,
                target_protein REAL NOT NULL,
                target_karbo REAL NOT NULL,
                target_lemak REAL NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS food_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tanggal TEXT NOT NULL,
                waktu TEXT NOT NULL,
                nama_makanan TEXT NOT NULL,
                berat_gram REAL NOT NULL,
                kalori REAL NOT NULL,
                protein REAL NOT NULL,
                karbohidrat REAL NOT NULL,
                lemak REAL NOT NULL,
                catatan_ai TEXT,
                serat REAL DEFAULT 0,
                vitamin_mineral TEXT DEFAULT ''
            )
        """)

        # Migrasi aman untuk database lama agar kolom baru otomatis ditambahkan
        # Migrasi aman untuk database lama agar kolom baru otomatis ditambahkan
        for col_sql in [
            "ALTER TABLE food_logs ADD COLUMN serat REAL DEFAULT 0",
            "ALTER TABLE food_logs ADD COLUMN vitamin_mineral TEXT DEFAULT ''",
        ]:
            try:
                cursor.execute(col_sql)
            except sqlite3.OperationalError:
                pass

        # ================= TEMPEL BAGIAN 1 DI SINI =================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS food_reference (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nama_bahan TEXT UNIQUE NOT NULL,
                kategori TEXT NOT NULL,
                satuan_dasar TEXT NOT NULL,
                kalori REAL NOT NULL,
                protein REAL NOT NULL,
                karbohidrat REAL NOT NULL,
                lemak REAL NOT NULL,
                serat REAL NOT NULL,
                vitamin_mineral TEXT NOT NULL
            )
        """)

        cursor.execute("SELECT COUNT(*) FROM food_reference")
        if cursor.fetchone()[0] == 0:
            seed_foods = [
                ("Nasi Putih", "Karbohidrat", "100 gram", 130.0, 2.7, 28.0, 0.3, 0.4, "Vitamin B1, B3, Zat Besi, Magnesium"),
                ("Nasi Merah", "Karbohidrat", "100 gram", 111.0, 2.6, 23.0, 0.9, 1.8, "Vitamin B1, B6, Magnesium, Fosfor, Zinc"),
                ("Dada Ayam Panggang/Rebus", "Protein", "100 gram", 165.0, 31.0, 0.0, 3.6, 0.0, "Vitamin B3, B6, Fosfor, Kalium, Selenium"),
                ("Telur Ayam Utuh", "Protein", "1 butir (55g)", 78.0, 6.3, 0.6, 5.3, 0.0, "Vitamin A, D, B12, Kolin, Zat Besi"),
                ("Tempe Goreng", "Protein", "100 gram", 225.0, 19.0, 9.0, 13.0, 3.5, "Kalsium, Zat Besi, Magnesium, Vitamin B2"),
                ("Tahu Putih", "Protein", "100 gram", 76.0, 8.0, 1.9, 4.8, 0.3, "Kalsium, Mangan, Tembaga, Selenium"),
                ("Pisang Ambon/Cavendish", "Buah", "1 buah (118g)", 105.0, 1.3, 27.0, 0.4, 3.1, "Kalium, Vitamin B6, Vitamin C, Magnesium"),
                ("Apel", "Buah", "1 buah (180g)", 95.0, 0.5, 25.0, 0.3, 4.4, "Vitamin C, Kalium, Vitamin K"),
                ("Jeruk Manis", "Buah", "1 buah (130g)", 62.0, 1.2, 15.4, 0.2, 3.1, "Vitamin C, Folat (B9), Kalium, Kalsium"),
                ("Alpukat", "Buah", "100 gram", 160.0, 2.0, 8.5, 14.7, 6.7, "Vitamin E, K, C, B5, B6, Kalium, Folat"),
                ("Brokoli Rebus", "Sayur", "100 gram", 35.0, 2.4, 7.2, 0.4, 3.3, "Vitamin C, K, A, Folat, Kalium, Zat Besi"),
                ("Bayam", "Sayur", "100 gram", 23.0, 2.9, 3.6, 0.4, 2.2, "Zat Besi, Vitamin A, C, K, Folat, Magnesium"),
                ("Wortel", "Sayur", "100 gram", 41.0, 0.9, 9.6, 0.2, 2.8, "Vitamin A (Beta-karoten), K1, B6, Kalium"),
                ("Tomat Merah", "Sayur", "1 buah (120g)", 22.0, 1.1, 4.8, 0.2, 1.5, "Vitamin C, A, K, Kalium, Likopen"),
                ("Timun", "Sayur", "100 gram", 15.0, 0.7, 3.6, 0.1, 0.5, "Vitamin K, C, Kalium, Magnesium"),
            ]
            cursor.executemany("""
                INSERT INTO food_reference
                (nama_bahan, kategori, satuan_dasar, kalori, protein, karbohidrat, lemak, serat, vitamin_mineral)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, seed_foods)
        # ===========================================================

        conn.commit()
        _initialized = True


# --------------- PROFIL PENGGUNA ---------------

def get_user_profile() -> Optional[Dict[str, Any]]:
    """Mengambil data profil pengguna aktif (paling baru)."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_profile ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    return dict(row) if row else None

def save_user_profile(
    nama: str,
    jenis_kelamin:str,
    usia: int,
    berat_badan: float,
    tinggi_badan: float,
    tingkat_aktivitas: str,
    goal: str,
    target_kalori: float,
    target_protein: float,
    target_karbo: float,
    target_lemak: float
) -> int:
    """Buat nyimpen atau memperbarui profile user."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM user_profile ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()

    params = (nama, jenis_kelamin, usia, berat_badan, tinggi_badan,
              tingkat_aktivitas, goal, target_kalori, target_protein,
              target_karbo, target_lemak)

    if row:
        profile_id = row["id"]
        cursor.execute("""
            UPDATE user_profile
            SET nama=?, jenis_kelamin=?, usia=?, berat_badan=?, tinggi_badan=?,
                tingkat_aktivitas=?, goal=?, target_kalori=?, target_protein=?,
                target_karbo=?, target_lemak=?
            WHERE id=?
        """, (*params, profile_id))
        conn.commit()
        return profile_id
    else:
        cursor.execute("""
            INSERT INTO user_profile (
                nama, jenis_kelamin, usia, berat_badan, tinggi_badan,
                tingkat_aktivitas, goal, target_kalori, target_protein,
                target_karbo, target_lemak
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, params)
        conn.commit()
        return cursor.lastrowid
# =================================================


def add_food_log(
    tanggal: str,
    waktu: str,
    nama_makanan: str,
    berat_gram: float,
    kalori: float,
    protein: float,
    karbohidrat: float,
    lemak: float,
    catatan_ai: str = "",
    serat: float = 0.0,
    vitamin_mineral: str = ""
) -> int:
    """Menambahkan catatan makanan baru ke food_logs."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO food_logs (
            tanggal, waktu, nama_makanan, berat_gram,
            kalori, protein, karbohidrat, lemak, catatan_ai,
            serat, vitamin_mineral
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (tanggal, waktu, nama_makanan, berat_gram,
          kalori, protein, karbohidrat, lemak, catatan_ai,
          serat, vitamin_mineral))
    conn.commit()
    return cursor.lastrowid


def get_food_logs_by_date(tanggal: str) -> List[Dict[str, Any]]:
    """Mengambil seluruh catatan makanan pada tanggal tertentu."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM food_logs
        WHERE tanggal = ?
        ORDER BY id DESC
    """, (tanggal,))
    return [dict(row) for row in cursor.fetchall()]


def delete_food_log(log_id: int) -> bool:
    """Menghapus catatan makanan berdasarkan ID."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM food_logs WHERE id = ?", (log_id,))
    conn.commit()
    return cursor.rowcount > 0


def get_daily_summary(tanggal: str) -> Dict[str, Any]:
    """Menghitung total asupan kalori, makronutrisi, serat, dan vitamin/mineral pada tanggal tertentu."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            COALESCE(SUM(kalori), 0)      AS total_kalori,
            COALESCE(SUM(protein), 0)     AS total_protein,
            COALESCE(SUM(karbohidrat), 0) AS total_karbo,
            COALESCE(SUM(lemak), 0)       AS total_lemak,
            COALESCE(SUM(serat), 0)       AS total_serat,
            COUNT(id)                     AS total_item
        FROM food_logs
        WHERE tanggal = ?
    """, (tanggal,))
    row = cursor.fetchone()

    # Ambil daftar vitamin & mineral yang dikonsumsi hari ini
    cursor.execute("""
        SELECT vitamin_mineral FROM food_logs
        WHERE tanggal = ? AND vitamin_mineral IS NOT NULL AND vitamin_mineral != ''
    """, (tanggal,))
    vit_list = []
    for r in cursor.fetchall():
        for item in r["vitamin_mineral"].split(","):
            clean_item = item.strip()
            if clean_item and clean_item not in vit_list:
                vit_list.append(clean_item)

    return {
        "total_kalori": round(float(row["total_kalori"]), 1),
        "total_protein": round(float(row["total_protein"]), 1),
        "total_karbo": round(float(row["total_karbo"]), 1),
        "total_lemak": round(float(row["total_lemak"]), 1),
        "total_serat": round(float(row["total_serat"]), 1),
        "total_item": int(row["total_item"]),
        "list_vitamin_mineral": ", ".join(vit_list) if vit_list else "Belum ada asupan tercatat",
    }


# --------------- FOOD REFERENCE (KAMUS GIZI) ---------------

def get_all_food_references() -> List[Dict[str, Any]]:
    """Mengambil seluruh daftar referensi kandungan gizi bahan makanan."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM food_reference ORDER BY kategori, nama_bahan")
    return [dict(row) for row in cursor.fetchall()]


def get_reference_prompt_context() -> str:
    """Mengubah data tabel referensi menjadi teks acuan kalibrasi untuk prompt Gemini AI."""
    refs = get_all_food_references()
    lines = ["ACUAN STANDAR GIZI LOKAL (Gunakan sebagai patokan proporsi gramasi):"]
    for r in refs:
        lines.append(
            f"- {r['nama_bahan']} ({r['satuan_dasar']}): {r['kalori']} kkal, "
            f"Protein {r['protein']}g, Karbo {r['karbohidrat']}g, Lemak {r['lemak']}g, "
            f"Serat {r['serat']}g | Mikronutrisi: {r['vitamin_mineral']}"
        )
    return "\n".join(lines)