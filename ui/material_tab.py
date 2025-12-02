import streamlit as st
import pandas as pd

from logic.ifc_logic import load_ifc_from_upload, build_ifc_base_table
from logic.material_logic import build_material_kubaturen, apply_price_overrides
from database.price_utils import load_price_dataframe

st.set_page_config(layout="wide")

#Optionen
@st.dialog("Optionen")
def show_options(text_match: str):
    st.markdown("**Fuzzymatch optionen**")
    st.write("""
             Hier kann eingestellt werden bis zu welcher abweichung atributtexte kombiniert werden sollen

             Beispiel:
             Wand / wand = 97% Übereinstimmung
             """)
    text_match = st.slider("", 70, 100, 90, 1)
    return(text_match)

def main():
    text_match = 90
    st.title("🧱 Material Kubaturen")

    col1, col2 = st.columns(2,gap="small",vertical_alignment="center")

    with col1:
        if st.button("Optionen",icon="⚙️", width="stretch"):
            text_match = show_options(text_match)

    with col2:
        if st.button("Materialdatenbank",icon="📝" ,width="stretch"):
            st.switch_page("UI/material_admin.py")


    # -----------------------------
    # IFC Upload / Auswahl
    # -----------------------------
    uploaded = st.file_uploader("IFC-Datei wählen", type=["ifc"])

    if uploaded is not None:
        # Neues IFC wurde gewählt → neu einlesen
        try:
            ifc_model, df_ifc = load_ifc_from_upload(uploaded)
        except Exception as e:
            st.error(f"Fehler beim Laden der IFC-Datei: {e}")
            return

        st.session_state["ifc_model"] = ifc_model
        st.session_state["df_ifc"] = df_ifc
        st.success(f"IFC-Modell geladen: {uploaded.name}")
    else:
        # Kein Upload im aktuellen Lauf → versuchen, aus Session zu lesen
        if "df_ifc" not in st.session_state:
            st.info("Bitte zuerst eine IFC-Datei hochladen, um Materialkubaturen zu berechnen.")
            return
        df_ifc = st.session_state["df_ifc"]

    # -----------------------------
    # Preisdatenbank laden
    # -----------------------------
    df_prices = load_price_dataframe()
    if df_prices.empty:
        st.warning(
            "In der Materialdatenbank sind noch keine Materialien hinterlegt. "
            "Öffne die Seite **Materialien**, um dort Preise anzulegen."
        )

    # -----------------------------
    # Material-Kubaturen berechnen
    # -----------------------------
    with st.spinner("Berechne Materialkubaturen ..."):
        df_material_base = build_material_kubaturen(
            df_ifc=df_ifc,
            df_prices=df_prices,
            text_match=float(text_match),
        )

    if df_material_base.empty:
        st.info("Es konnten keine Bauteile für die Materialauswertung gefunden werden.")
        return

    # -----------------------------
    # Session-State für Overrides
    # -----------------------------
    if "price_overrides" not in st.session_state:
        st.session_state["price_overrides"] = {}
    price_overrides = st.session_state["price_overrides"]

    # Lookup für automatische Preise (Basis)
    base_price_lookup = {}
    for _, row in df_material_base.iterrows():
        key = (
            str(row.get("Grundstück", "")).strip(),
            str(row.get("Gebäude", "")).strip(),
            str(row.get("Geschoss", "")).strip(),
            str(row.get("Bauteil", "")).strip(),
            str(row.get("Material", "")).strip(),
        )
        base_price_lookup[key] = float(row.get("Preis_auto", 0.0))

    # Zuerst die Overrides anwenden → df_material_view
    df_material_view = apply_price_overrides(
        df_material=df_material_base,
        overrides=price_overrides,
    )

    # Für Dashboard und andere Tabs speichern
    st.session_state["df_material_view"] = df_material_view

    # -----------------------------
    # Projekt-Summen
    # -----------------------------
    total_vol = float(df_material_view["Volumen_m3_sum"].sum())
    total_cost = float(df_material_view["Kosten_total_eff"].sum())

    c1, c2 = st.columns(2)
    with c1:
        st.metric("Projektvolumen [m³]", f"{total_vol:,.1f}")
    with c2:
        st.metric("Materialkosten gesamt [CHF]", f"{total_cost:,.0f}")

    st.divider()

    # -----------------------------
    # Anzeige pro Gebäude / Geschoss
    # -----------------------------
    st.subheader("📦 Aufstellung nach Gebäude und Geschoss")

    geb_group = df_material_view.groupby("Gebäude", dropna=False)

    for geb_name, df_geb in geb_group:
        geb_name_display = geb_name if str(geb_name).strip() else "Ohne Gebäudename"

        geb_total_vol = float(df_geb["Volumen_m3_sum"].sum())
        geb_total_cost = float(df_geb["Kosten_total_eff"].sum())

        with st.expander(f"Gebäude: {geb_name_display}", expanded=False):
            g1, g2 = st.columns(2)
            with g1:
                st.write(f"**Volumen Gebäude:** {geb_total_vol:,.1f} m³")
            with g2:
                st.write(f"**Kosten Gebäude:** {geb_total_cost:,.0f} CHF")

            st.markdown("---")

            # pro Geschoss
            storey_group = df_geb.groupby("Geschoss", dropna=False)

            for storey_name, df_storey in storey_group:
                storey_display = storey_name if str(storey_name).strip() else "Ohne Geschossname"

                with st.expander(f"Geschoss: {storey_display}", expanded=False, width="stretch"):
                    # Verwende ein Formular pro Geschoss für die Eingabefelder
                    form = st.form(f"form-{geb_name}-{storey_name}")

                    # Header-Zeile mit CSS für konsistente Darstellung
                    form.markdown(
                        "<div style='display:flex; gap:12px; font-weight:600;'>"
                        "<div style='width:25%'>Bauteil</div>"
                        "<div style='width:25%'>Material</div>"
                        "<div style='width:15%'>Kubatur [m³]</div>"
                        "<div style='width:15%'>Anzahl</div>"
                        "<div style='width:15%'>Preis [CHF/m³]</div>"
                        "<div style='width:15%; text-align:right'>Total [CHF]</div>"
                        "</div><hr>",
                        unsafe_allow_html=True
                    )

                    # Lokale Zwischensumme und Overrides nur innerhalb der Form (Pending)
                    storey_total_preview = 0.0
                    pending_overrides = {}

                    # WICHTIG: Iteration über Index (idx) und Row
                    for idx, row in df_storey.iterrows():
                        grund = str(row.get("Grundstück", "")).strip()
                        geb = str(row.get("Gebäude", "")).strip()
                        ges = str(row.get("Geschoss", "")).strip()
                        bau = str(row.get("Bauteil", "")).strip()
                        mat = str(row.get("Material", "")).strip()

                        vol = float(row.get("Volumen_m3_sum", 0.0))
                        anzahl = int(row.get("Anzahl_Elemente", 0))

                        # Basis-Preis (Auto-Preis) aus dem Lookup holen
                        auto_price = base_price_lookup.get((grund, geb, ges, bau, mat), 0.0)

                        key_tuple = (grund, geb, ges, bau, mat)

                        # Startwert: Override, falls vorhanden, sonst Auto-Preis
                        start_value = float(price_overrides.get(key_tuple, auto_price))

                        # Generiere einen stabilen, eindeutigen String-Key inkl. Index (idx)
                        # HINWEIS: Ersetze Leerzeichen und Punkte, um Konflikte zu vermeiden.
                        stable_key = f"price-{idx}-{grund}-{geb}-{ges}-{bau}-{mat}".replace(" ", "_").replace(".", "-")

                        col1, col2, col3, col4, col5, col6 = form.columns([3.2, 3.2, 1.9, 1.5, 2.0, 2.0], gap="small")
                        col1.markdown(f"<div style='padding:4px 0'>{bau or '—'}</div>", unsafe_allow_html=True)
                        col2.markdown(f"<div style='padding:4px 0'>{mat or '—'}</div>", unsafe_allow_html=True)
                        col3.markdown(f"<div style='padding:4px 0'>{vol:,.2f}</div>", unsafe_allow_html=True)
                        col4.markdown(f"<div style='padding:4px 0'>{anzahl}</div>", unsafe_allow_html=True)

                        # Eingabefeld für den Preis
                        new_price = col5.number_input(
                            label=" ", label_visibility="collapsed",
                            min_value=0.0, step=0.05, format="%.2f",
                            value=start_value,
                            key=stable_key, # <--- STABILER KEY VERWENDET
                        )
                        pending_overrides[key_tuple] = float(new_price)

                        line_total = vol * float(new_price)
                        storey_total_preview += line_total
                        col6.markdown(
                            f"<div style='padding:4px 0; text-align:right; font-weight:600'>{line_total:,.2f}</div>",
                            unsafe_allow_html=True
                        )

                    form.markdown("<hr>", unsafe_allow_html=True)
                    form.markdown(f"**Zwischensumme {storey_display} (Vorschau):** {storey_total_preview:,.2f} CHF")

                    # Speichern-Button und Logik
                    if form.form_submit_button("💾 Änderungen dieses Geschosses übernehmen"):

                        # Overrides verarbeiten
                        for key, edited_price in pending_overrides.items():
                            base_price = base_price_lookup.get(key, 0.0)

                            if edited_price != base_price:
                                # Override setzen
                                price_overrides[key] = edited_price
                            else:
                                # Override entfernen, wenn er identisch zum Auto-Preis ist
                                if key in price_overrides:
                                    del price_overrides[key]

                        st.session_state["price_overrides"] = price_overrides
                        st.success(f"Preise für Geschoss {storey_display} übernommen und Overrides aktualisiert.")
                        st.rerun() # Rerun, um die Gesamt- und Gebäudesummen neu zu berechnen


    st.success("Materialkubaturen wurden erfolgreich berechnet und Overrides übernommen.")


if __name__ == "__main__":
    main()
else:
    # Wenn via Main.py über st.navigation geladen
    main()