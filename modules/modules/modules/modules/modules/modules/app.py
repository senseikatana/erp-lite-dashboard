# app.py
import streamlit as st
from config import COMPANIES, DEFAULT_COMPANY
from i18n import t
from database import get_engine
from seed_data import seed

# --- Configuración de página ---
st.set_page_config(
    page_title="ERP-Lite",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Sembrar datos de demo la primera vez ---
for code in COMPANIES:
    get_engine(code)
    seed(code)

# --- Estado de sesión ---
if "lang" not in st.session_state:
    st.session_state.lang = "es"
if "company" not in st.session_state:
    st.session_state.company = DEFAULT_COMPANY

# --- Sidebar ---
with st.sidebar:
    st.title("🏢 ERP-Lite")
    st.caption("Inspirado en Dynamics NAV · Multiempresa")

    st.session_state.company = st.selectbox(
        "Empresa",
        options=list(COMPANIES.keys()),
        format_func=lambda c: COMPANIES[c].name,
        index=list(COMPANIES.keys()).index(st.session_state.company),
    )

    st.session_state.lang = st.selectbox(
        "Idioma / Idioma / Language",
        options=["es", "ca", "en"],
        index=["es", "ca", "en"].index(st.session_state.lang),
    )

    st.divider()

    # Menú de navegación
    menu_items = [
        "dashboard", "ventas", "compras", "almacen", "demanda", "rutas"
    ]
    module_labels = {
        "dashboard": "📊 " + t("dashboard", st.session_state.lang),
        "ventas": "🛒 " + t("sales", st.session_state.lang),
        "compras": "📦 " + t("purchases", st.session_state.lang),
        "almacen": "🏭 " + t("warehouse", st.session_state.lang),
        "demanda": "📈 " + t("demand", st.session_state.lang),
        "rutas": "🚚 " + t("routes", st.session_state.lang),
    }

    module = st.radio(
        "Módulo",
        options=menu_items,
        format_func=lambda m: module_labels[m],
        label_visibility="collapsed",
    )

    st.divider()
    st.caption(f"Empresa: **{COMPANIES[st.session_state.company].name}**")
    st.caption(f"Moneda: {COMPANIES[st.session_state.company].currency}")

# --- Render dinámico del módulo ---
module_map = {
    "dashboard": "modules.dashboard",
    "ventas": "modules.ventas",
    "compras": "modules.compras",
    "almacen": "modules.almacen",
    "demanda": "modules.demanda",
    "rutas": "modules.rutas",
}

import importlib
mod = importlib.import_module(module_map[module])
mod.render(st.session_state.company, st.session_state.lang)