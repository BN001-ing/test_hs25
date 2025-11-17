import streamlit as st
import Logik.IFC as IFC
import pandas as pd
import time
import Logik.Datenbank as db
from Logik.Logic import build_material_kubaturen
from Logik.Logic import apply_session_overrides

@st.cache_data(show_spinner=False)
def compute_tab2(df_ifc: pd.DataFrame, df_prices: pd.DataFrame, text_match: int) -> pd.DataFrame:
    return build_material_kubaturen(
        df_ifc=df_ifc,
        df_prices=df_prices,
        text_match=text_match,
        col_map={"Bauteil": "Namen"}  # falls deine Bauteil-Spalte 'Namen' heißt
    )

# Session-Container für Preis-Overrides (nur für diese Sitzung)
if "price_overrides" not in st.session_state:
    st.session_state["price_overrides"] = {}  # dict[(grund,geb,ges,bauteil,material)] = preis(float)

#---------------Variablen-------------------
#Leerer Panda Dataframe erstellen.
columns = [
    "GlobalID",
    "Grundstück",
    "Gebäude",
    "Geschoss",
    "Namen",
    "IFCClass",
    "Material",
    "Volumen_m3"
]
df_ifc = pd.DataFrame(columns=columns)

#---DB VERBINDUNG---
conn = db.connect()
db.create_tables(conn)


text_match = 90

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

#-----------------------------Import------------------
st.set_page_config(layout="wide")
st.title("📊 Kubeko")

col1, col2 = st.columns(2,gap="small",vertical_alignment="center")

with col1:
    if st.button("Optionen",icon="⚙️", width="stretch"):
        text_match = show_options(text_match)

with col2:
    if st.button("Materialdatenbank",icon="📝" ,width="stretch"):
        st.switch_page("views/material list.py")

#Upload knopf
uploaded_file = st.file_uploader(
    "Upload data", accept_multiple_files=False, type="ifc"
)
if not uploaded_file:
    st.stop()


#-----------------Auswertung der IFC Datei (Dataframe erstellen--------------
with st.spinner("Ich mache gerade deinen Job, also lehn dich zurück😉", show_time=True):
    
    #Datei Importieren
    ifc_model = IFC.IMPORT_IFC(uploaded_file)

    #GlobaleID abfüllen für Sämtliche Elemente um sie zuordnen zu können
    df_new = IFC.get_all_global_ids_df(ifc_model)
    df_ifc = df_ifc.merge(
    df_new[["GlobalID", "IFCClass"]],
    on=["GlobalID", "IFCClass"],
    how="outer"
    )
    df_ifc = df_ifc.set_index("GlobalID")

    #Verortung des Bauteils aus dem IFC auslesen (GGrundstück,Gebäude,Geschoss)
    df_temp=IFC.Verortung(ifc_model)
    df_ifc.loc[df_temp.index, "Gebäude"] = df_temp["Gebäude"]
    df_ifc.loc[df_temp.index, "Geschoss"] = df_temp["Geschoss"]
    df_ifc.loc[df_temp.index, "Grundstück"] = df_temp["Grundstück"]

    #bauteil nach Materialien Filtern ()
    df_temp = IFC.material_series_by_element(ifc_model)
    df_ifc.loc[df_temp.index, "Material"] = df_temp["Material"]

    #Nach Namen filtern
    df_temp = IFC.KomponentenName(ifc_model)
    df_ifc.loc[df_temp.index, "Namen"] = df_temp["Name"]

    #Volumen ergänzen
    df_temp = IFC.Volumen_geom(ifc_model)
    df_ifc.loc[df_temp.index, "Volumen_m3"] = df_temp["Volumen_m3"]

    # --- DB VERBINDUNG ---
    conn = db.connect()
    db.create_tables(conn)

    # Preise aus SQLite in einen DataFrame laden und auf Standard-Namen bringen
    rows = db.get_all_materials()  # [(id, material_name, einheit, preis_chf, datum_aktualisiert), ...]
    df_prices = pd.DataFrame(
        rows,
        columns=["ID", "material_name", "Einheit", "preis_chf", "Aktualisiert"]
    )

    if not df_prices.empty:
        df_prices = df_prices.rename(columns={"material_name": "Material", "preis_chf": "Preis"})
    else:
        # Leerer DF mit erwarteten Spalten, damit der weitere Code robust bleibt
        df_prices = pd.DataFrame(columns=["ID", "Material", "Einheit", "Preis", "Aktualisiert"])


#---------------Visuelles--------------------

#Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📄Dashboard", "🧱Material Kubaturen", "Bewehrung","🧑‍💻Dataframe(debug)"])

#Dashboard
with tab1:
    st.write("Dashboard")

#Material Kubaturen
with tab2:
    st.write("Kubaturen")
    df_tab2 = compute_tab2(df_ifc, df_prices, text_match)

    if df_tab2 is None or df_tab2.empty:
        st.info("Keine Daten vorhanden.")
        st.stop()

    # Overrides anwenden für Anzeige/Totalberechnung
    df_view = apply_session_overrides(df_tab2, st.session_state["price_overrides"])

        # Gruppieren fürs Rendering
    geb_group = df_view.groupby("Gebäude", dropna=False)

    grand_total = 0.0

    # Optional: Reset-Button für alle Overrides (nur Sitzung)
    cols_top = st.columns([1, 1, 2])
    if cols_top[0].button("🔁 Overrides zurücksetzen (nur Sitzung)"):
        st.session_state["price_overrides"].clear()
        st.success("Overrides zurückgesetzt.")

    for geb_name, df_g in geb_group:
        st.markdown(f"### 🏢 Gebäude: **{geb_name or '—'}**")

        # Pro Gebäude nach Geschoss
        storey_group = df_g.groupby("Geschoss", dropna=False)
        geb_total = 0.0

        for storey_name, df_s in storey_group:
            with st.expander(f"Geschoss: {storey_name or '—'}", expanded=False, width="stretch"):
                form = st.form(f"form-{geb_name}-{storey_name}")  # ← eigene Form pro Geschoss

                form.markdown(
                "<div style='display:flex; gap:12px; font-weight:600;'>"
                "<div style='width:26%'>Bauteil</div>"
                "<div style='width:26%'>Material</div>"
                "<div style='width:16%'>Kubatur [m³]</div>"
                "<div style='width:16%'>Preis [CHF/m³]</div>"
                "<div style='width:16%; text-align:right'>Total [CHF]</div>"
                "</div><hr>",
                unsafe_allow_html=True
                )

            # lokale Zwischensumme nur innerhalb der Form berechnen
            storey_total_preview = 0.0
            pending_overrides = {}

            for _, row in df_s.iterrows():
                grund = str(row["Grundstück"]); geb = str(row["Gebäude"])
                ges = str(row["Geschoss"]);     bau = str(row["Bauteil"])
                mat = str(row["Material"])

                vol = float(row["Volumen_m3_sum"] or 0.0)
                auto_price = float(row["Preis_CHF"] or 0.0)

                key_tuple = (grund, geb, ges, bau, mat)
                start_value = float(st.session_state["price_overrides"].get(key_tuple, auto_price))

                col1, col2, col3, col4, col5 = form.columns([3.2, 3.2, 2.0, 2.0, 2.0], gap="small")
                col1.markdown(f"<div style='padding:4px 0'>{bau}</div>", unsafe_allow_html=True)
                col2.markdown(f"<div style='padding:4px 0'>{mat}</div>", unsafe_allow_html=True)
                col3.markdown(f"<div style='padding:4px 0'>{vol:,.2f}</div>", unsafe_allow_html=True)

                new_price = col4.number_input(
                    label=" ", label_visibility="collapsed",
                    min_value=0.0, step=1.0, format="%.2f",
                    value=start_value,
                    key=f"price-form-{hash(key_tuple)}",
                )
                pending_overrides[key_tuple] = float(new_price)

                line_total = vol * float(new_price)
                storey_total_preview += line_total
                col5.markdown(
                    f"<div style='padding:4px 0; text-align:right; font-weight:600'>{line_total:,.2f}</div>",
                    unsafe_allow_html=True
                )

            form.markdown("<hr>", unsafe_allow_html=True)
            form.markdown(f"**Zwischensumme {storey_name or '—'} (Vorschau):** {storey_total_preview:,.2f} CHF")

            # Nur hier löst du den Rerun aus – wenn bewusst gespeichert wird
            if form.form_submit_button("💾 Änderungen dieses Geschosses übernehmen"):
                st.session_state["price_overrides"].update(pending_overrides)
                st.success("Änderungen übernommen.")
                st.rerun()

        # Gebäude-Summe
        # nachdem df_view = apply_session_overrides(...) berechnet ist:
        geb_df = df_view[df_view["Gebäude"] == geb_name]
        geb_total = float(geb_df["Kosten_total_eff"].sum())
        st.markdown(f"### Summe Gebäude: {geb_total:,.2f} CHF")
        st.divider()
        grand_total += geb_total


    # Gesamtsumme
    st.subheader(f"💰 Projektsumme: {grand_total:,.2f} CHF")


#Bewehrung
with tab3:
    st.write("Bewehrung")

#Dataframe
with tab4:
    st.write("🧱 IFC-Datenrahmen für Debugging:", df_ifc)