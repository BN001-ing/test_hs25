import streamlit as st
import pandas as pd


def main():
    st.title("👩‍💻 Debug – Dataframes & Session State")

    st.markdown(
        """
        Dieser Tab dient nur zum Debuggen und zur Kontrolle der Daten, 
        die in den anderen KuBeKo-Tabs verwendet werden.
        """
    )

    st.divider()

    # --------------------------------------------------
    # Übersicht: welche Objekte sind im Session-State?
    # --------------------------------------------------
    st.subheader("🧠 Session-State Übersicht")

    if not st.session_state:
        st.info("Der Session-State ist noch leer.")
    else:
        st.write("Aktuell vorhandene Keys im `st.session_state`:")
        st.code("\n".join(sorted(st.session_state.keys())), language="text")

    st.divider()

    # --------------------------------------------------
    # IFC-DataFrame (Rohdaten aus IFC)
    # --------------------------------------------------
    st.subheader("🧱 df_ifc – Basis-Bauteiltabelle aus IFC")

    df_ifc = st.session_state.get("df_ifc")
    if isinstance(df_ifc, pd.DataFrame) and not df_ifc.empty:
        st.write(f"Form: {df_ifc.shape[0]} Zeilen × {df_ifc.shape[1]} Spalten")
        with st.expander("Spalten anzeigen", expanded=False):
            st.write(list(df_ifc.columns))

        with st.expander("Vorschau (erste 50 Zeilen)", expanded=True):
            st.dataframe(df_ifc.head(50), use_container_width=True)
    else:
        st.info("`df_ifc` ist noch nicht gesetzt oder leer.")

    st.divider()

    # --------------------------------------------------
    # Material-View (Tab 2 – nach Overrides)
    # --------------------------------------------------
    st.subheader("📦 df_material_view – Material-Kubaturen (mit Overrides)")

    df_material_view = st.session_state.get("df_material_view")
    if isinstance(df_material_view, pd.DataFrame) and not df_material_view.empty:
        st.write(
            f"Form: {df_material_view.shape[0]} Zeilen × {df_material_view.shape[1]} Spalten"
        )
        with st.expander("Spalten anzeigen", expanded=False):
            st.write(list(df_material_view.columns))

        with st.expander("Vorschau (erste 50 Zeilen)", expanded=True):
            st.dataframe(df_material_view.head(50), use_container_width=True)
    else:
        st.info("`df_material_view` ist noch nicht gesetzt oder leer (Tab 2 evtl. noch nicht geöffnet).")

    st.divider()

    # --------------------------------------------------
    # Rebar-View (Tab 3 – nach kg/m³-Overrides)
    # --------------------------------------------------
    st.subheader("🔩 df_rebar_view – Bewehrung (mit Overrides)")

    df_rebar_view = st.session_state.get("df_rebar_view")
    if isinstance(df_rebar_view, pd.DataFrame) and not df_rebar_view.empty:
        st.write(
            f"Form: {df_rebar_view.shape[0]} Zeilen × {df_rebar_view.shape[1]} Spalten"
        )
        with st.expander("Spalten anzeigen", expanded=False):
            st.write(list(df_rebar_view.columns))

        with st.expander("Vorschau (erste 50 Zeilen)", expanded=True):
            st.dataframe(df_rebar_view.head(50), use_container_width=True)
    else:
        st.info("`df_rebar_view` ist noch nicht gesetzt oder leer (Tab 3 evtl. noch nicht geöffnet).")

    st.divider()

    # --------------------------------------------------
    # Preis-Overrides & Rebar-Overrides
    # --------------------------------------------------
    st.subheader("✏️ Overrides")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**price_overrides (Materialpreise)**")
        price_overrides = st.session_state.get("price_overrides", {})
        if price_overrides:
            st.write(f"{len(price_overrides)} Einträge")
            with st.expander("Details anzeigen", expanded=False):
                st.json({str(k): v for k, v in price_overrides.items()})
        else:
            st.caption("Keine Preis-Overrides gesetzt.")

    with col2:
        st.markdown("**rebar_overrides (kg/m³)**")
        rebar_overrides = st.session_state.get("rebar_overrides", {})
        if rebar_overrides:
            st.write(f"{len(rebar_overrides)} Einträge")
            with st.expander("Details anzeigen", expanded=False):
                st.json({str(k): v for k, v in rebar_overrides.items()})
        else:
            st.caption("Keine Rebar-Overrides gesetzt.")

    st.divider()

    # --------------------------------------------------
    # Projekt-Summen aus anderen Tabs
    # --------------------------------------------------
    st.subheader("📊 Projektsummen aus anderen Tabs")

    material_total_cost = st.session_state.get("material_total_cost")
    project_total_rebar_kg = st.session_state.get("project_total_rebar_kg")
    project_total_rebar_cost = st.session_state.get("project_total_rebar_cost")

    c1, c2, c3 = st.columns(3)

    with c1:
        if material_total_cost is not None:
            st.metric("Materialkosten (aus Tab 2)", f"{material_total_cost:,.2f} CHF")
        else:
            st.caption("Materialkosten noch nicht im Session-State.")

    with c2:
        if project_total_rebar_kg is not None:
            st.metric("Bewehrung gesamt (kg)", f"{project_total_rebar_kg:,.0f} kg")
        else:
            st.caption("Rebar-kg noch nicht im Session-State.")

    with c3:
        if project_total_rebar_cost is not None:
            st.metric("Bewehrungskosten (aus Tab 3)", f"{project_total_rebar_cost:,.2f} CHF")
        else:
            st.caption("Rebar-Kosten noch nicht im Session-State.")


if __name__ == "__main__":
    main()
