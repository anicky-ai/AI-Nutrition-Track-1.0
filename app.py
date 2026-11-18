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
        min-height: 48px;
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
        help="gemini-3.8-flash (utama & akurat), gemini-2.5-flash-lite (hemat kuota)",
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

if st.session_state["action_feedback"]:
    fb_type, fb_msg = st.session_state["action_feedback"]
    getattr(st, fb_type, st.info)(fb_msg)
    st.session_state["action_feedback"] = None

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

    jk_user = user_profile["jenis_kelamin"] if user_profile else "Laki-laki"
    t_fiber = 30.0 if jk_user == "Laki-laki" else 25.0

    c_cal = summary["total_kalori"]
    c_pro = summary["total_protein"]
    c_carb = summary["total_karbo"]
    c_fat = summary["total_lemak"]
    c_fiber = summary.get("total_serat", 0.0)
    c_vitmin = summary.get("list_vitamin_mineral", "Belum ada asupan tercatat")