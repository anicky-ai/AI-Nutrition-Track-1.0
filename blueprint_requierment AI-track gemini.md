# Project Specification: AI Nutrition & Muscle Tracker

## 1. Project Overview
Aplikasi web berbasis **100% Python** yang membantu pengguna yang sedang menjalani program diet, pembentukan massa otot (*bulking*), atau menjaga pola makan. Aplikasi ini memungkinkan pengguna menghitung target makronutrisi harian, memindai foto makanan menggunakan kamera/galeri untuk mendeteksi kandungan gizi secara otomatis dengan **Gemini Multimodal AI**, menyesuaikan estimasi porsi, dan memantau progres harian.

- **Target Skala:** MVP (Minimum Viable Product) untuk Tugas Akhir Mahasiswa Semester 3.
- **Prinsip Utama:** Simpel, cepat dieksekusi, *mobile-responsive*, dan menggunakan *Structured Output* untuk menjamin konsistensi data AI.

---

## 2. Tech Stack & Dependencies
Buat file `requirements.txt` dengan daftar *library* berikut:
- `streamlit` (UI Frontend & alur aplikasi web)
- `google-genai` (SDK resmi Gemini API untuk analisis gambar makanan)
- `pydantic` (Validasi skema *Structured Output* JSON dari AI)
- `pillow` (Kompresi dan pengolahan gambar sebelum dikirim ke API)
- `python-dotenv` (Manajemen environment variable untuk `GEMINI_API_KEY`)

*(Database menggunakan modul bawaan Python `sqlite3`, tidak perlu instalasi eksternal).*

---

## 3. Arsitektur & Struktur Direktori
Bangun struktur proyek modular sebagai berikut:

```text
ai-nutrition-tracker/
├── .env                  # Menyimpan GEMINI_API_KEY
├── requirements.txt      # Daftar library Python
├── app.py                # Entry point utama & tampilan UI Streamlit
├── ai_scanner.py         # Modul integrasi Gemini API & skema Pydantic
├── database.py           # Operasi CRUD database SQLite (nutrition.db)
├── nutrition_calc.py     # Logika perhitungan BMR, TDEE, dan target makro
└── nutrition.db          # File database SQLite (auto-generated saat init)
```

---

## 4. Skema Database (`database.py`)
Gunakan SQLite (`nutrition.db`) dengan fungsi inisialisasi tabel otomatis saat aplikasi pertama kali dijalankan (`init_db()`).

### Tabel 1: `user_profile`
Menyimpan data profil pengguna (cukup 1 profil aktif untuk MVP atau mendukung pemilihan profil).
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `nama` (TEXT)
- `jenis_kelamin` (TEXT) — `"Laki-laki"` atau `"Perempuan"`
- `usia` (INTEGER)
- `berat_badan` (REAL) — dalam kg
- `tinggi_badan` (REAL) — dalam cm
- `tingkat_aktivitas` (TEXT) — `"Sedentary"`, `"Light"`, `"Moderate"`, `"Active"`, `"Very Active"`
- `goal` (TEXT) — `"Cutting"`, `"Maintenance"`, atau `"Bulking"`
- `target_kalori` (REAL)
- `target_protein` (REAL)
- `target_karbo` (REAL)
- `target_lemak` (REAL)

### Tabel 2: `food_logs`
Menyimpan riwayat makanan yang telah di-*scan* dan disimpan oleh pengguna.
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `tanggal` (TEXT) — format `YYYY-MM-DD`
- `waktu` (TEXT) — format `HH:MM`
- `nama_makanan` (TEXT)
- `berat_gram` (REAL)
- `kalori` (REAL)
- `protein` (REAL)
- `karbohidrat` (REAL)
- `lemak` (REAL)
- `catatan_ai` (TEXT)

---

## 5. Spesifikasi Fungsional & Logika Bisnis

### Fitur 1: Kalkulator Target Nutrisi (`nutrition_calc.py`)
1. **Hitung BMR (Rumus Mifflin-St Jeor):**
   - Laki-laki: $\text{BMR} = (10 \times \text{berat}) + (6.25 \times \text{tinggi}) - (5 \times \text{usia}) + 5$
   - Perempuan: $\text{BMR} = (10 \times \text{berat}) + (6.25 \times \text{tinggi}) - (5 \times \text{usia}) - 161$
2. **Hitung TDEE:**
   - Kalikan BMR dengan faktor aktivitas: Sedentary ($1.2$), Light ($1.375$), Moderate ($1.55$), Active ($1.725$), Very Active ($1.9$).
3. **Penyesuaian Kalori & Makro Berdasarkan Goal:**
   - **Cutting (Defisit):** $\text{Target Kalori} = \text{TDEE} - 400\text{ kkal}$
   - **Maintenance:** $\text{Target Kalori} = \text{TDEE}$
   - **Bulking (Bangun Otot):** $\text{Target Kalori} = \text{TDEE} + 300\text{ kkal}$
   - **Distribusi Makronutrisi:**
     - **Protein:** $2.0\text{ g} \times \text{berat\_badan}$ ($1\text{ g protein} = 4\text{ kkal}$)
     - **Lemak:** $25\%$ dari total $\text{Target Kalori}$ dibagi $9$ ($1\text{ g lemak} = 9\text{ kkal}$)
     - **Karbohidrat:** Sisa kalori dibagi $4$ ($1\text{ g karbo} = 4\text{ kkal}$)

### Fitur 2: AI Food Scanner (`ai_scanner.py`)
- **Model AI:** `gemini-2.5-flash` menggunakan SDK `google-genai`.
- **Optimasi Gambar:** Sebelum dikirim ke API, gambar di-*resize* maksimal dimensi $1024 \times 1024$ piksel menggunakan `Pillow` agar hemat kuota dan cepat diproses.
- **Pydantic Schema (`FoodNutrition`):**
  ```python
  class FoodNutrition(BaseModel):
      nama_makanan: str
      estimasi_berat_gram: float
      kalori_kcal: float
      protein_gram: float
      karbohidrat_gram: float
      lemak_gram: float
      catatan_diet: str
  ```
- **Prompting:** Instruksikan AI untuk mengenali makanan lokal Indonesia maupun internasional, memperkirakan berat porsi dalam gram secara realistis, menghitung nilai gizi, dan memberikan 1 kalimat saran evaluasi yang disesuaikan dengan *goal* pengguna saat ini (`Cutting`/`Bulking`/`Maintenance`).

### Fitur 3: Koreksi Porsi Manual (Portion Adjustment)
- Setelah hasil AI muncul di UI, simpan hasilnya ke `st.session_state`.
- Tampilkan input angka atau *slider* untuk mengubah **Berat Porsi (gram)**.
- Jika pengguna mengubah berat dari $W_{\text{awal}}$ menjadi $W_{\text{baru}}$, hitung ulang seluruh nilai nutrisi secara proporsional menggunakan rasio $R = \frac{W_{\text{baru}}}{W_{\text{awal}}}$ sebelum disimpan ke database.

### Fitur 4: Dashboard Monitoring Harian (`app.py`)
- Tampilkan ringkasan asupan hari ini dibandingkan dengan target dari `user_profile`.
- Gunakan `st.progress` dan `st.metric` untuk 4 indikator utama: **Kalori (kkal)**, **Protein (g)**, **Karbohidrat (g)**, dan **Lemak (g)**.
- Berikan indikator visual (misal: peringatan jika kalori melebihi target, atau pesan sukses jika target protein harian tercapai).

### Fitur 5: Riwayat Konsumsi Harian (Food Logs)
- Menampilkan daftar makanan yang dikonsumsi pada tanggal yang dipilih (`st.date_input`, default hari ini).
- Menyediakan tombol **Hapus** pada setiap item log jika pengguna ingin membatalkan catatan makanan tertentu.

---

## 6. Alur Antarmuka Pengguna (UI/UX Flow di `app.py`)
Gunakan tata letak bersih (*mobile-first friendly*) dengan navigasi berbasis `st.tabs` atau `st.sidebar`:

1. **Pengecekan Awal:** Jika tabel `user_profile` masih kosong, arahkan pengguna langsung ke tab **Profil & Target** untuk mengisi data tubuh terlebih dahulu.
2. **Tab 1: Dashboard & Scan Makanan (Halaman Utama)**
   - Bagian Atas: *Progress bar* Kalori & Protein hari ini.
   - Bagian Tengah: Pilihan input gambar menggunakan `st.tabs(["📷 Kamera", "📁 Upload Galeri"])` yang masing-masing berisi `st.camera_input` dan `st.file_uploader`.
   - Tombol **"Analisis Nutrisi Makanan"** $\rightarrow$ memunculkan kartu hasil AI + input koreksi gramasi + tombol **"Simpan ke Log Harian"**.
3. **Tab 2: Riwayat Makan**
   - Filter tanggal dan daftar makanan yang sudah tercatat hari itu beserta rincian makronya dan opsi hapus.
4. **Tab 3: Profil & Target Diet**
   - Form untuk mengatur ulang berat badan, tinggi, aktivitas, dan *goal* diet kapan saja.

---

## 7. Instruksi Eksekusi untuk AI Agent (Antigravity)
1. Buat seluruh file sesuai struktur direktori pada Bagian 3.
2. Pastikan penanganan *error* (try-except) diterapkan pada pemanggilan Gemini API (misal: jika API Key belum diisi atau koneksi gagal, tampilkan pesan `st.error` yang informatif).
3. Pastikan `GEMINI_API_KEY` dapat dibaca dari file `.env` maupun diinput langsung melalui *sidebar* UI sebagai cadangan saat demo/presentasi.
4. Uji sintaks seluruh file dan pastikan aplikasi siap dijalankan dengan perintah `streamlit run app.py`.