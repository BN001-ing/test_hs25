import streamlit as st
import plotly.express as px
import pandas as pd
from logic.dashboard_logic import build_dashboard_data

st.set_page_config(layout="wide")

def main():
    st.title("📊 Dashboard – Projektübersicht")

    # ------------------------------------------------------
    # Prüfen, ob Material-Tab bereits berechnet wurde
    # ------------------------------------------------------
    if "df_material_view" not in st.session_state:
        st.warning("Bitte zuerst eine IFC-Datei laden und Tab 'Material Kubaturen' öffnen.")
        return

    df_material_view = st.session_state["df_material_view"]

    # Falls Rebar-Tab noch nicht geöffnet wurde → 0 als default
    rebar_cost = float(st.session_state.get("project_total_rebar_cost", 0.0))

    # ------------------------------------------------------
    # Dashboard-Daten erzeugen
    # ------------------------------------------------------
    dashboard = build_dashboard_data(
        df_material_view=df_material_view,
        total_rebar_cost=rebar_cost,
    )

    # ------------------------------------------------------
    # KPIs
    # ------------------------------------------------------
    st.subheader("🔎 Projekt-Kennzahlen")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Gesamtkosten [CHF]",
            f"{dashboard['project_total_cost']:,.0f}"
        )
    with col2:
        st.metric(
            "Materialkosten [CHF]",
            f"{dashboard['material_cost']:,.0f}"
        )
    with col3:
        st.metric(
            "Bewehrungskosten [CHF]",
            f"{dashboard['rebar_cost']:,.0f}"
        )
    with col4:
        st.metric(
            "Total Volumen [m³]",
            f"{dashboard['project_total_volume']:,.1f}"
        )

    st.divider()

    # ------------------------------------------------------
    # Kosten pro Gebäude
    # ------------------------------------------------------
    st.subheader("🏢 Kosten pro Gebäude")
    df_b = dashboard["cost_by_building"]

    if not df_b.empty:
        fig = px.bar(
            df_b,
            x="Gebäude",
            y="Kosten_total_eff",
            title="Kosten pro Gebäude",
            labels={"Kosten_total_eff": "Kosten [CHF]"},
            text_auto=True,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Keine Gebäudedaten verfügbar.")

    st.divider()

    # ------------------------------------------------------
    # Kosten pro Geschoss
    # ------------------------------------------------------
    st.subheader("🏗️ Kosten pro Geschoss")
    df_s = dashboard["cost_by_storey"]

    if not df_s.empty:
        fig = px.bar(
            df_s,
            x="Geschoss",
            y="Kosten_total_eff",
            color="Gebäude",
            title="Kosten pro Geschoss",
            labels={"Kosten_total_eff": "Kosten [CHF]"},
            text_auto=True,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Keine Geschossdaten verfügbar.")

    st.divider()

    # ------------------------------------------------------
    # Materialvolumen (Pie Chart)
    # ------------------------------------------------------
    st.subheader("🧱 Materialvolumen [m³]")
    df_v = dashboard["vol_by_material"]

    if not df_v.empty:
        fig = px.pie(
            df_v,
            names="Material",
            values="Volumen_m3_sum",
            title="Verteilung des Materialvolumens",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Keine Materialdaten verfügbar.")

    st.divider()

    # ------------------------------------------------------
    # Materialkosten (Pie Chart)
    # ------------------------------------------------------
    st.subheader("💰 Materialkosten nach Material")
    df_cm = dashboard["cost_by_material"]

    if not df_cm.empty:
        fig = px.pie(
            df_cm,
            names="Material",
            values="Kosten_total_eff",
            title="Kostenverteilung nach Material",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Keine Kostendaten verfügbar.")

    st.divider()

    # ------------------------------------------------------
    # Anzahl Bauteile (aus Materialgruppierungen)
    # ------------------------------------------------------
    st.subheader("📦 Anzahl ausgewerteter Bauteile")
    st.write(
        f"Im Projekt wurden **{dashboard['elem_count']} Bauteile** ausgewertet."
    )


# damit Streamlit es findet:
if __name__ == "__main__":
    main()
else:
    main()
