import streamlit as st

# --- PAGE SETUP ---

about_page = st.Page(
    page="ui/about_tab.py",
    title="About",
    icon="🏠",
    default=True,
)

# KuBeKo-Seiten
kubeko_dashboard_page = st.Page(
    page="ui/dashboard.py",
    title="Dashboard",
    icon="📊",
)

kubeko_material_page = st.Page(
    page="ui/material_tab.py",
    title="Material Kubaturen",
    icon="🧱",
)

kubeko_rebars_page = st.Page(
    page="ui/rebars_tab.py",
    title="Bewehrung",
    icon="🧵",
)

# Material-Admin (Preisdatenbank)
material_admin_page = st.Page(
    page="ui/material_admin.py",
    title="Materialien",
    icon="📦",
)

# Debug-Dataframe
debug_page = st.Page(
    page="ui/debug_tab.py",
    title="Dataframe (debug)",
    icon="👩‍💻",
)

# DaReCo (Attribute entfernen)
dareco_page = st.Page(
    page="ui/dareco_tab.py",
    title="DaReCo",
    icon="🧹",
)

# --- NAVIGATION ---

pg = st.navigation(
    {
        "Info": [about_page],
        "KuBeKo": [
            kubeko_material_page,
            kubeko_rebars_page,
            kubeko_dashboard_page,
            material_admin_page,
            debug_page,
        ],
        "Weitere Tools": [
            dareco_page,
        ],
    }
)

# --- SHARED ON ALL PAGES ---
st.logo("assets/Logo.png")
st.sidebar.text("Made with ❤️ by Niels")

# --- RUN ---
pg.run()
