"""
AI Nutrition & Muscle Tracker
Entry point Streamlit — UI modern, mobile-responsive, Material Icons.
"""

import os
import datetime
import streamlit as st
from dotenv import load_dotenv

import database as db
import nutrition_calc as calc
import ai_scanner as ai

load_dotenv()

# ==========================================
# PAGE CONFIG
# ==========================================
st.set_page_config(
    page_title="AI Nutrition Tracker",
    page_icon="🥗",
    layout="centered",
    initial_sidebar_state="collapsed",
)

db.init_db()

# ==========================================
# HELPER: 3-TIER API KEY RESOLUTION
# ==========================================
def resolve_api_key(sidebar_key: str) -> str:
    """
    Prioritas API Key:
    1. Input manual dari sidebar UI (untuk demo/presentasi)
    2. st.secrets (untuk deployment Streamlit Cloud)
    3. os.getenv / .env lokal (untuk dev lokal)
    """
    if sidebar_key and sidebar_key.strip():
        return sidebar_key.strip()
    try:
        secret = st.secrets.get("GEMINI_API_KEY", "")
        if secret and secret.strip():
            return secret.strip()
    except (FileNotFoundError, AttributeError):
        pass
    return os.getenv("GEMINI_API_KEY", "").strip()


# ==========================================
# CUSTOM CSS — RESPONSIVE, DARK-MODE AWARE
# ==========================================
st.markdown("""
<style>
    /* ---- Container ---- */
    .block-container {
        padding: 1.2rem 1rem 3rem 1rem;
        max-width: 740px;
    }

    /* ---- Header ---- */
    .app-header { text-align: center; margin-bottom: 1rem; }
    .app-title {
        font-size: 1.9rem; font-weight: 800;
        background: linear-gradient(135deg, #10B981, #06B6D4);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .app-subtitle { font-size: 0.92rem; opacity: 0.7; }

    /* ---- Nutrient Card (dashboard summary, history items) ---- */
    .n-card {
        border-radius: 14px; padding: 14px 16px;
        margin-bottom: 12px;
        border: 1px solid rgba(100,116,139,0.15);
        background: var(--secondary-background-color, #F0FDF4);
        transition: box-shadow 0.2s;
    }
    .n-card:hover { box-shadow: 0 2px 10px rgba(0,0,0,0.06); }

    .n-card .card-title {
        font-weight: 700; font-size: 1.05rem; margin-bottom: 4px;
    }
    .n-card .card-sub {
        font-size: 0.85rem; opacity: 0.72; line-height: 1.6;
    }

    /* ---- AI Result Card ---- */
    .ai-result {
        border: 2px solid #10B981; border-radius: 16px;
        padding: 18px 20px; margin: 1rem 0;
        background: linear-gradient(145deg,
            rgba(16,185,129,0.06), rgba(6,182,212,0.06));
    }
    .ai-food-name {
        font-size: 1.3rem; font-weight: 800; color: #059669;
    }

    /* ---- Buttons ---- */
    div.stButton > button {
        border-radius: 12px; font-weight: 600;
        padding: 0.55rem 1.2rem;
        transition: transform 0.15s, box-shadow 0.15s;
    }
    div.stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(16,185,129,0.25);
    }
    div.stButton > button[kind="primary"] {
        min-height: 48px;         /* touch-friendly for mobile */
    }

    /* ---- Progress bar color ---- */
    div[data-testid="stProgress"] > div > div {
        background-color: #10B981;
    }

    /* ---- Sidebar brand ---- */
    section[data-testid="stSidebar"] .block-container {
        padding-top: 1rem;
    }

    /* ---- Mobile tweaks ---- */
    @media (max-width: 640px) {
        .block-container { padding: 0.8rem 0.6rem 2rem 0.6rem; }
        .app-title { font-size: 1.5rem; }
        div.stButton > button { min-height: 50px; font-size: 1rem; }
    }
</style>
""", unsafe_allow_html=True)


# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    st.markdown("### :material/settings: Konfigurasi")

    custom_api_key = st.text_input(
        ":material/key: Gemini API Key",
        value=st.session_state.get("sidebar_api_key", ""),
        type="password",
        placeholder="AIzaSy...",
        help="Prioritas: Sidebar → st.secrets (Cloud) → .env lokal",
    )
    if custom_api_key:
        st.session_state["sidebar_api_key"] = custom_api_key

    effective_key = resolve_api_key(custom_api_key)

    if effective_key:
        st.success(":material/check_circle: API Key Aktif", icon="✅")
    else:
        st.warning(":material/warning: API Key Belum Diisi")
        st.caption("Dapatkan key gratis di [Google AI Studio](https://aistudio.google.com/)")

    st.divider()

    selected_model = st.selectbox(
        ":material/smart_toy: Model AI",
        options=ai.AVAILABLE_MODELS,
        index=0,
        help="gemini-3.8-flash (cepat & hemat), gemini-2.5-pro (lebih akurat)",
    )

    st.divider()

    profile = db.get_user_profile()
    if profile:
        st.markdown(f"**:material/person: {profile['nama']}**")
        goal_icons = {"Cutting": "🔻", "Maintenance": "⚖️", "Bulking": "💪"}
        st.markdown(f"**:material/flag: Goal:** {goal_icons.get(profile['goal'], '🎯')} {profile['goal']}")
        st.markdown(f"**:material/monitor_weight: BB/TB:** {profile['berat_badan']} kg / {profile['tinggi_badan']} cm")
        st.markdown(f"**:material/local_fire_department: Kalori:** {profile['target_kalori']:.0f} kkal/hari")
    else:
        st.info("Belum ada profil tersimpan.")

    st.divider()
    st.caption("AI Nutrition Tracker v2.0 — Gemini AI")


# ==========================================
# SESSION STATE
# ==========================================
for key, default in [
    ("scanned_nutrition", None),
    ("portion_weight", 100.0),
    ("action_feedback", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

user_profile = db.get_user_profile()


# ==========================================
# HEADER
# ==========================================
st.markdown("""
<div class="app-header">
    <div class="app-title">🥗 AI Nutrition Tracker</div>
    <div class="app-subtitle">Scan makanan · Hitung makro · Pantau progres harian</div>
</div>
""", unsafe_allow_html=True)

# Action feedback toast
if st.session_state["action_feedback"]:
    fb_type, fb_msg = st.session_state["action_feedback"]
    getattr(st, fb_type, st.info)(fb_msg)
    st.session_state["action_feedback"] = None

# Peringatan profil
if not user_profile:
    st.warning(
        ":material/account_circle: **Profil belum diatur.** "
        "Buka tab **Profil & Target** untuk menghitung kebutuhan nutrisi harian Anda."
    )


# ==========================================
# TABS
# ==========================================
tab1, tab2, tab3 = st.tabs([
    ":material/dashboard: Dashboard & Scan",
    ":material/history: Riwayat Makan",
    ":material/person: Profil & Target",
])


# ==========================================
# TAB 1 — DASHBOARD & SCAN MAKANAN
# ==========================================
with tab1:
    today_str = datetime.date.today().isoformat()
    summary = db.get_daily_summary(today_str)

    st.markdown("#### :material/monitoring: Asupan Hari Ini")

    t_cal = user_profile["target_kalori"] if user_profile else 2000.0
    t_pro = user_profile["target_protein"] if user_profile else 120.0
    t_carb = user_profile["target_karbo"] if user_profile else 250.0
    t_fat = user_profile["target_lemak"] if user_profile else 55.0

    c_cal = summary["total_kalori"]
    c_pro = summary["total_protein"]
    c_carb = summary["total_karbo"]
    c_fat = summary["total_lemak"]

    def _ratio(consumed, target):
        return min(1.0, consumed / target) if target > 0 else 0.0

    # 2×2 Responsive Metric Grid
    col_l, col_r = st.columns(2)

    with col_l:
        st.metric(":material/local_fire_department: Kalori",
                  f"{c_cal:.0f} kkal",
                  delta=f"{c_cal - t_cal:+.0f} vs target")
        r = _ratio(c_cal, t_cal)
        st.progress(r, text=f"{r*100:.0f}%")

        st.metric(":material/grain: Karbohidrat",
                  f"{c_carb:.1f} g",
                  delta=f"Target: {t_carb:.0f} g")
        r = _ratio(c_carb, t_carb)
        st.progress(r, text=f"{r*100:.0f}%")

    with col_r:
        st.metric(":material/fitness_center: Protein",
                  f"{c_pro:.1f} g",
                  delta=f"Target: {t_pro:.0f} g")
        r = _ratio(c_pro, t_pro)
        st.progress(r, text=f"{r*100:.0f}%")

        st.metric(":material/water_drop: Lemak",
                  f"{c_fat:.1f} g",
                  delta=f"Target: {t_fat:.0f} g")
        r = _ratio(c_fat, t_fat)
        st.progress(r, text=f"{r*100:.0f}%")

    # Alerts
    if c_cal > t_cal > 0:
        st.warning(f":material/warning: Asupan kalori melebihi target! ({c_cal:.0f} / {t_cal:.0f} kkal)")
    if c_pro >= t_pro > 0:
        st.success(f":material/emoji_events: Target protein tercapai! ({c_pro:.1f} / {t_pro:.0f} g)")

    st.divider()

    # --- FOOD SCANNER ---
    st.markdown("#### :material/photo_camera: Scan Makanan dengan AI")

    cam_tab, upload_tab = st.tabs([
        ":material/camera: Kamera",
        ":material/upload_file: Upload Galeri",
    ])

    image_to_process = None
    with cam_tab:
        camera_img = st.camera_input("Ambil foto makanan")
        if camera_img:
            image_to_process = camera_img
    with upload_tab:
        uploaded_img = st.file_uploader(
            "Pilih foto makanan",
            type=["jpg", "jpeg", "png", "webp"],
            help="Format: JPG, PNG, WEBP",
        )
        if uploaded_img and not camera_img:
            image_to_process = uploaded_img

    if image_to_process:
        st.image(image_to_process, caption="Pratinjau Foto Makanan", use_container_width=True)

        btn_col, reset_col = st.columns([3, 1])
        with btn_col:
            scan_clicked = st.button(
                ":material/search: Analisis Nutrisi",
                type="primary", use_container_width=True,
            )
        with reset_col:
            if st.button(":material/refresh: Reset", use_container_width=True):
                st.session_state["scanned_nutrition"] = None
                st.rerun()

        if scan_clicked:
            goal = user_profile["goal"] if user_profile else "Maintenance"
            with st.spinner(":material/smart_toy: Gemini AI sedang menganalisis makanan..."):
                try:
                    result = ai.analyze_food_image(
                        image_file=image_to_process,
                        user_goal=goal,
                        api_key=effective_key,
                        model_name=selected_model,
                    )
                    st.session_state["scanned_nutrition"] = result
                    st.session_state["portion_weight"] = float(result.estimasi_berat_gram)
                    st.toast("Analisis selesai!", icon="✅")
                except ValueError as e:
                    st.error(f":material/error: {e}")
                except ConnectionError as e:
                    st.error(f":material/cloud_off: {e}")
                except Exception as e:
                    st.error(f":material/error: Terjadi kesalahan: {e}")

    # --- HASIL AI ---
    if st.session_state["scanned_nutrition"]:
        scanned: ai.FoodNutrition = st.session_state["scanned_nutrition"]
        goal_label = user_profile["goal"] if user_profile else "Diet"

        st.markdown(f"""
        <div class="ai-result">
            <div class="ai-food-name">🍽️ {scanned.nama_makanan}</div>
        </div>
        """, unsafe_allow_html=True)

        st.info(f":material/lightbulb: **Saran AI ({goal_label}):** {scanned.catatan_diet}")

        st.markdown("##### :material/scale: Koreksi Berat Porsi")
        new_weight = st.number_input(
            "Berat Makanan (gram):",
            min_value=1.0, max_value=5000.0,
            value=float(st.session_state["portion_weight"]),
            step=10.0, key="portion_input_box",
        )
        st.session_state["portion_weight"] = new_weight
        scaled = ai.scale_nutrition(scanned, new_weight)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric(":material/local_fire_department: Kalori", f"{scaled.kalori_kcal:.0f} kkal")
        m2.metric(":material/fitness_center: Protein", f"{scaled.protein_gram:.1f} g")
        m3.metric(":material/grain: Karbo", f"{scaled.karbohidrat_gram:.1f} g")
        m4.metric(":material/water_drop: Lemak", f"{scaled.lemak_gram:.1f} g")

        # --- TAMBAHAN SERAT, BUAH/SAYUR & VITAMIN/MINERAL ---
        col_s1, col_s2 = st.columns([1, 2])
        col_s1.metric(":material/eco: Serat", f"{scaled.serat_gram:.1f} g")
        with col_s2:
            st.markdown(f"**🥗 Buah & Sayur:** {scaled.komponen_buah_sayur}")
            st.markdown(f"**💊 Vitamin & Mineral:** {scaled.vitamin_mineral}")

        if st.button(
            ":material/save: Simpan ke Log Harian",
            type="primary", use_container_width=True,
        ):
        
            now = datetime.datetime.now()
            db.add_food_log(
                tanggal=now.strftime("%Y-%m-%d"),
                waktu=now.strftime("%H:%M"),
                nama_makanan=scaled.nama_makanan,
                berat_gram=scaled.estimasi_berat_gram,
                kalori=scaled.kalori_kcal,
                protein=scaled.protein_gram,
                karbohidrat=scaled.karbohidrat_gram,
                lemak=scaled.lemak_gram,
                catatan_ai=scaled.catatan_diet,
            )
            st.session_state["action_feedback"] = (
                "success",
                f":material/check_circle: '{scaled.nama_makanan}' ({scaled.estimasi_berat_gram:.0f}g) tersimpan!"
            )
            st.session_state["scanned_nutrition"] = None
            st.rerun()


# ==========================================
# TAB 2 — RIWAYAT MAKAN
# ==========================================
with tab2:
    st.markdown("#### :material/history: Riwayat Konsumsi Makanan")

    sel_date = st.date_input(":material/calendar_today: Pilih Tanggal", value=datetime.date.today())
    sel_str = sel_date.isoformat()

    h_summary = db.get_daily_summary(sel_str)
    h_logs = db.get_food_logs_by_date(sel_str)

    # Daily summary card
    st.markdown(f"""
    <div class="n-card">
        <div class="card-title">📊 Ringkasan — {sel_date.strftime('%d %B %Y')}</div>
        <div class="card-sub">
            🔥 <b>{h_summary['total_kalori']:.0f}</b> kkal &nbsp;·&nbsp;
            💪 <b>{h_summary['total_protein']:.1f}</b>g protein &nbsp;·&nbsp;
            🌾 <b>{h_summary['total_karbo']:.1f}</b>g karbo &nbsp;·&nbsp;
            🫒 <b>{h_summary['total_lemak']:.1f}</b>g lemak &nbsp;·&nbsp;
            🍽️ <b>{h_summary['total_item']}</b> item
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not h_logs:
        st.info(":material/restaurant: Belum ada catatan makanan untuk tanggal ini.")
    else:
        for log in h_logs:
            with st.container():
                st.markdown(f"""
                <div class="n-card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span class="card-title">{log['nama_makanan']}</span>
                        <span style="font-size:0.82rem; opacity:0.6;">🕒 {log['waktu']}</span>
                    </div>
                    <div class="card-sub">
                        ⚖️ {log['berat_gram']:.0f}g &nbsp;·&nbsp;
                        🔥 {log['kalori']:.0f} kkal &nbsp;·&nbsp;
                        💪 {log['protein']:.1f}g &nbsp;·&nbsp;
                        🌾 {log['karbohidrat']:.1f}g &nbsp;·&nbsp;
                        🫒 {log['lemak']:.1f}g
                    </div>
                    {"<div style='font-size:0.82rem; color:#059669; margin-top:4px; font-style:italic;'>💡 " + log['catatan_ai'] + "</div>" if log.get('catatan_ai') else ""}
                </div>
                """, unsafe_allow_html=True)

                _, del_col = st.columns([5, 1])
                with del_col:
                    if st.button(":material/delete:", key=f"del_{log['id']}", use_container_width=True):
                        db.delete_food_log(log["id"])
                        st.session_state["action_feedback"] = (
                            "info",
                            f":material/delete: '{log['nama_makanan']}' dihapus."
                        )
                        st.rerun()


# ==========================================
# TAB 3 — PROFIL & TARGET DIET
# ==========================================
with tab3:
    st.markdown("#### :material/person: Profil & Kalkulator Target Nutrisi")
    st.caption("Berdasarkan rumus ilmiah Mifflin-St Jeor.")

    p = user_profile or {}
    d_nama = p.get("nama", "")
    d_jk = p.get("jenis_kelamin", "Laki-laki")
    d_usia = int(p.get("usia", 21))
    d_bb = float(p.get("berat_badan", 65.0))
    d_tb = float(p.get("tinggi_badan", 170.0))
    d_akt = p.get("tingkat_aktivitas", "Moderate")
    d_goal = p.get("goal", "Maintenance")

    with st.form("form_profile"):
        nama_in = st.text_input(":material/badge: Nama Lengkap", value=d_nama)

        c1, c2 = st.columns(2)
        with c1:
            jk_opts = ["Laki-laki", "Perempuan"]
            jk_in = st.selectbox(":material/wc: Jenis Kelamin", jk_opts,
                                 index=jk_opts.index(d_jk) if d_jk in jk_opts else 0)
        with c2:
            usia_in = st.number_input(":material/cake: Usia (tahun)",
                                      min_value=12, max_value=100, value=d_usia, step=1)

        c3, c4 = st.columns(2)
        with c3:
            bb_in = st.number_input(":material/monitor_weight: Berat Badan (kg)",
                                    min_value=30.0, max_value=250.0, value=d_bb, step=0.5)
        with c4:
            tb_in = st.number_input(":material/height: Tinggi Badan (cm)",
                                    min_value=100.0, max_value=250.0, value=d_tb, step=0.5)

        akt_opts = ["Sedentary", "Light", "Moderate", "Active", "Very Active"]
        akt_in = st.selectbox(
            ":material/directions_run: Tingkat Aktivitas Fisik", akt_opts,
            index=akt_opts.index(d_akt) if d_akt in akt_opts else 2,
            help="Sedentary (Jarang olahraga) · Light (1-3 hr/mgg) · Moderate (3-5 hr/mgg) · Active (6-7 hr/mgg) · Very Active (intensif)"
        )

        goal_opts = ["Cutting", "Maintenance", "Bulking"]
        goal_in = st.selectbox(
            ":material/flag: Goal Diet / Kebugaran", goal_opts,
            index=goal_opts.index(d_goal) if d_goal in goal_opts else 1,
            help="Cutting (-400 kkal) · Maintenance (jaga BB) · Bulking (+300 kkal)"
        )

        # Live preview
        targets = calc.calculate_nutrition_targets(
            berat_badan=bb_in, tinggi_badan=tb_in,
            usia=int(usia_in), jenis_kelamin=jk_in,
            tingkat_aktivitas=akt_in, goal=goal_in,
        )

        st.markdown("##### :material/calculate: Pratinjau Target Nutrisi")
        pc1, pc2 = st.columns(2)
        with pc1:
            st.metric(":material/heart_plus: BMR", f"{targets['bmr']:.0f} kkal")
            st.metric(":material/local_fire_department: Target Kalori", f"{targets['target_kalori']:.0f} kkal")
            st.metric(":material/grain: Karbohidrat", f"{targets['target_karbo']:.0f} g")
        with pc2:
            st.metric(":material/bolt: TDEE", f"{targets['tdee']:.0f} kkal")
            st.metric(":material/fitness_center: Protein (2g/kg)", f"{targets['target_protein']:.0f} g")
            st.metric(":material/water_drop: Lemak (25%)", f"{targets['target_lemak']:.0f} g")

        submitted = st.form_submit_button(
            ":material/save: Simpan Profil & Target",
            type="primary", use_container_width=True,
        )

    if submitted:
        db.save_user_profile(
            nama=nama_in.strip() or "Pengguna",
            jenis_kelamin=jk_in, usia=int(usia_in),
            berat_badan=float(bb_in), tinggi_badan=float(tb_in),
            tingkat_aktivitas=akt_in, goal=goal_in,
            target_kalori=targets["target_kalori"],
            target_protein=targets["target_protein"],
            target_karbo=targets["target_karbo"],
            target_lemak=targets["target_lemak"],
        )
        st.session_state["action_feedback"] = (
            "success",
            ":material/check_circle: Profil dan target nutrisi berhasil diperbarui!"
        )
        st.rerun()
