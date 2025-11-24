import streamlit as st
import Logik.IFC as IFC
import pandas as pd
import time
import math
import Logik.Datenbank as db
from Logik.Logic import build_material_kubaturen
from Logik.Logic import apply_session_overrides
from Logik.Logic import build_rebar_kubaturen, apply_rebar_overrides
from Logik.Logic import build_dashboard_data
from Logik.Logic import get_default_material_price, compute_rebar_price_table
import matplotlib.pyplot as plt

@st.cache_data(show_spinner=False)
def compute_tab2(df_ifc: pd.DataFrame, df_prices: pd.DataFrame, text_match: int) -> pd.DataFrame:
    return build_material_kubaturen(
        df_ifc=df_ifc,
        df_prices=df_prices,
        text_match=text_match,
        col_map={"Bauteil": "Namen"}  # falls deine Bauteil-Spalte 'Namen' heißt
    )

@st.cache_data(show_spinner=False)
def compute_rebar(df_ifc: pd.DataFrame, text_match: int) -> pd.DataFrame:
    return build_rebar_kubaturen(
        df_ifc=df_ifc,
        text_match=text_match,
        col_map={"Bauteil": "Namen"}
    )

# Session-Container für Preis-Overrides (nur für diese Sitzung)
if "price_overrides" not in st.session_state:
    st.session_state["price_overrides"] = {}  # dict[(grund,geb,ges,bauteil,material)] = preis(float)
# Session-Container für Bewehrungs-Overrides (nur Sitzung)
if "rebar_overrides" not in st.session_state:
    st.session_state["rebar_overrides"] = {}  # dict[(grund,geb,ges,bauteil,material)] = kg/m3
if "rebar_matten_pct" not in st.session_state:
    st.session_state["rebar_matten_pct"] = 15.0  # Default wie in deiner Vorlage
# Session-Container für Bewehrungspreise / Totale (nur Sitzung)
if "rebar_price_overrides" not in st.session_state:
    st.session_state["rebar_price_overrides"] = {}  # dict Ø_Bin -> CHF/kg
if "rebar_total_kg" not in st.session_state:
    st.session_state["rebar_total_kg"] = 0.0
if "rebar_total_cost" not in st.session_state:
    st.session_state["rebar_total_cost"] = 0.0


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
    
    default_rebar_price = get_default_material_price(df_prices, "Bewehrung")
    # ---------- rebar_split NUR HIER initialisieren (Preis ist jetzt bekannt) ----------
    if "rebar_split" not in st.session_state:
        st.session_state["rebar_split"] = {
            "Fix": {
                "grp_pct": 40.0,
                "bins": {"8-10": 50.0, "12-16": 35.0, "18-26": 10.0, "30-46": 5.0},
                "prices": {"8-10": default_rebar_price, "12-16": default_rebar_price,
                           "18-26": default_rebar_price, "30-46": default_rebar_price},
            },
            "BG 1": {
                "grp_pct": 30.0,
                "bins": {"8-10": 50.0, "12-16": 35.0, "18-26": 10.0, "30-46": 5.0},
                "prices": {"8-10": default_rebar_price, "12-16": default_rebar_price,
                           "18-26": default_rebar_price, "30-46": default_rebar_price},
            },
            "BG 2": {
                "grp_pct": 10.0,
                "bins": {"8-10": 50.0, "12-16": 35.0, "18-26": 10.0, "30-46": 5.0},
                "prices": {"8-10": default_rebar_price, "12-16": default_rebar_price,
                           "18-26": default_rebar_price, "30-46": default_rebar_price},
            },
            "BG S": {
                "grp_pct": 5.0,
                "bins": {"8-10": 50.0, "12-16": 35.0, "18-26": 10.0, "30-46": 5.0},
                "prices": {"8-10": default_rebar_price, "12-16": default_rebar_price,
                           "18-26": default_rebar_price, "30-46": default_rebar_price},
            },
        }
    else:
        # falls rebar_split aus alter Session kommt -> sicherstellen, dass prices existieren
        for g_data in st.session_state["rebar_split"].values():
            g_data.setdefault("prices", {
                "8-10": default_rebar_price, "12-16": default_rebar_price,
                "18-26": default_rebar_price, "30-46": default_rebar_price
            })
            for b in ["8-10", "12-16", "18-26", "30-46"]:
                g_data["prices"].setdefault(b, default_rebar_price)

    



#---------------Visuelles--------------------
# ----------------- Tab2 Basis einmal berechnen (für Tab1 + Tab2) -----------------
df_tab2 = compute_tab2(df_ifc, df_prices, text_match)

if df_tab2 is None or df_tab2.empty:
    st.info("Keine Daten vorhanden.")
    st.stop()

df_view = apply_session_overrides(df_tab2, st.session_state["price_overrides"])

dash = build_dashboard_data(df_view)


#Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📄Dashboard", "🧱Material Kubaturen", "Bewehrung","🧑‍💻Dataframe(debug)"])

#Dashboard
with tab1:
    st.subheader("📌 Projektübersicht")

    # Tab2-DF holen (inkl. Preis-Overrides)
    df_tab2 = compute_tab2(df_ifc, df_prices, text_match)
    df_view = apply_session_overrides(df_tab2, st.session_state["price_overrides"])

    if df_view is None or df_view.empty:
        st.info("Keine Daten für Dashboard vorhanden.")
        st.stop()

    total_material_cost = float(df_view["Kosten_total_eff"].sum())
    total_rebar_cost = float(st.session_state.get("rebar_total_cost", 0.0))
    total_project_cost = total_material_cost + total_rebar_cost


    # KPIs
    k1, k2, k3 = st.columns(3, gap="medium")
    k1.metric("Gesamtpreis Projekt", f"{total_project_cost:,.2f} CHF")
    k2.metric("Materialkosten (Tab2)", f"{total_material_cost:,.2f} CHF")
    k3.metric("Bewehrungskosten (Tab3)", f"{total_rebar_cost:,.2f} CHF")

    st.divider()

    # ------------------------
    # Diagramme
    # ------------------------

    # 1) Kosten pro Gebäude
    st.markdown("### Kosten pro Gebäude")
    cost_by_building = (df_view.groupby("Gebäude", dropna=False)["Kosten_total_eff"]
                        .sum()
                        .sort_values(ascending=False)
                        .reset_index())
    st.bar_chart(cost_by_building, x="Gebäude", y="Kosten_total_eff", use_container_width=True)

    # 2) Kosten pro Geschoss (über alle Gebäude)
    st.markdown("### Kosten pro Geschoss")
    cost_by_storey = (df_view.groupby(["Gebäude","Geschoss"], dropna=False)["Kosten_total_eff"]
                      .sum()
                      .reset_index())
    cost_by_storey["Gebäude/Geschoss"] = cost_by_storey["Gebäude"].astype(str) + " | " + cost_by_storey["Geschoss"].astype(str)
    st.bar_chart(cost_by_storey, x="Gebäude/Geschoss", y="Kosten_total_eff", use_container_width=True)

    # 3) Volumen nach Material (Benchmark Materialmix)
    st.markdown("### Material-Mix (Volumen)")
    vol_by_mat = (df_view.groupby("Material", dropna=False)["Volumen_m3_sum"]
                  .sum()
                  .sort_values(ascending=False)
                  .reset_index())
    st.bar_chart(vol_by_mat, x="Material", y="Volumen_m3_sum", use_container_width=True)

    # 4) Kostenanteile nach Material
    st.markdown("### Kostenanteile nach Material")
    cost_by_mat = (df_view.groupby("Material", dropna=False)["Kosten_total_eff"]
                   .sum()
                   .sort_values(ascending=False)
                   .reset_index())
    st.bar_chart(cost_by_mat, x="Material", y="Kosten_total_eff", use_container_width=True)

    st.divider()

    st.markdown(
        f"**Bewehrungskosten (Tab3):** {total_rebar_cost:,.2f} CHF  "
        f"(mit Ø-Preisen aus Tab Bewehrung)"
    )

#Material Kubaturen
with tab2:
    st.write("Kubaturen")

    if df_tab2 is None or df_tab2.empty:
        st.info("Keine Daten vorhanden.")
        st.stop()

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
    rebar_cost = float(st.session_state.get("rebar_total_cost", 0.0))
    grand_total_with_rebar = float(grand_total) + rebar_cost

    st.subheader(f"💰 Projektsumme (Material + Bewehrung): {grand_total_with_rebar:,.2f} CHF")
    st.caption(f"Materialkosten: {grand_total:,.2f} CHF  |  Bewehrungskosten: {rebar_cost:,.2f} CHF")

#Bewehrung
with tab3:
    st.subheader("🧰 Bewehrung (nur Beton)")

    # gleiche Schwelle wie Tab 2 verwenden
    df_rebar0 = compute_rebar(df_ifc, text_match)
    if df_rebar0 is None or df_rebar0.empty:
        st.info("Keine betonrelevanten Bauteile gefunden.")
        st.stop()

    # Session-Overrides anwenden (kg/m³ & Total kg)
    df_rebar = apply_rebar_overrides(
        df_rebar0,
        st.session_state["rebar_overrides"],
        default_kg_m3=0.0
    )

    # Reset-Button kg/m³
    topc1, _, _ = st.columns([1, 2, 2])
    if topc1.button("🔁 kg/m³-Overrides zurücksetzen (nur Sitzung)"):
        st.session_state["rebar_overrides"].clear()
        st.success("Overrides zurückgesetzt.")
        st.rerun()

    # -----------------------------
    # A) kg/m³ pro Bauteil (wie bisher)
    # -----------------------------
    geb_group = df_rebar.groupby("Gebäude", dropna=False)
    project_total_kg = 0.0

    for geb_name, df_g in geb_group:
        st.markdown(f"### 🏢 Gebäude: **{geb_name or '—'}**")
        storey_group = df_g.groupby("Geschoss", dropna=False)
        geb_total_kg = 0.0

        for storey_name, df_s in storey_group:
            with st.expander(f"Geschoss: {storey_name or '—'}", expanded=False):
                form = st.form(f"rebar-form-{geb_name}-{storey_name}")

                # Kopfzeile
                form.markdown(
                    "<div style='display:flex; gap:12px; font-weight:600;'>"
                    "<div style='width:26%'>Bauteil</div>"
                    "<div style='width:26%'>Material</div>"
                    "<div style='width:16%'>Kubatur [m³]</div>"
                    "<div style='width:16%'>kg/m³</div>"
                    "<div style='width:16%; text-align:right'>Total [kg]</div>"
                    "</div><hr>",
                    unsafe_allow_html=True
                )

                storey_total_preview_kg = 0.0
                pending_overrides = {}

                for _, row in df_s.iterrows():
                    grund = str(row["Grundstück"])
                    geb   = str(row["Gebäude"])
                    ges   = str(row["Geschoss"])
                    bau   = str(row["Bauteil"])
                    mat   = str(row["Material"])
                    vol   = float(row["Volumen_m3_sum"] or 0.0)

                    key_tuple = (grund, geb, ges, bau, mat)
                    start_value = float(
                        st.session_state["rebar_overrides"].get(key_tuple, row.get("kg_m3_eff", 0.0))
                    )

                    col1, col2, col3, col4, col5 = form.columns([3.2, 3.2, 2.0, 2.0, 2.0], gap="small")
                    col1.markdown(f"<div style='padding:4px 0'>{bau}</div>", unsafe_allow_html=True)
                    col2.markdown(f"<div style='padding:4px 0'>{mat}</div>", unsafe_allow_html=True)
                    col3.markdown(f"<div style='padding:4px 0'>{vol:,.2f}</div>", unsafe_allow_html=True)

                    kg_m3 = col4.number_input(
                        label=" ", label_visibility="collapsed",
                        min_value=0.0, step=5.0, format="%.0f",
                        value=start_value,
                        key=f"rebar-kgm3-{hash(key_tuple)}",
                    )
                    pending_overrides[key_tuple] = float(kg_m3)

                    total_kg = vol * float(kg_m3)
                    storey_total_preview_kg += total_kg
                    col5.markdown(
                        f"<div style='padding:4px 0; text-align:right; font-weight:600'>{total_kg:,.0f}</div>",
                        unsafe_allow_html=True
                    )

                form.markdown("<hr>", unsafe_allow_html=True)
                form.markdown(f"**Zwischensumme {storey_name or '—'} (Vorschau):** {storey_total_preview_kg:,.0f} kg")

                if form.form_submit_button("💾 kg/m³ dieses Geschosses übernehmen"):
                    st.session_state["rebar_overrides"].update(pending_overrides)
                    st.success("Änderungen übernommen.")
                    st.rerun()

            # Gebäude-Zwischensumme aufsummieren (gespeicherter Stand)
            geb_total_kg += float(
                apply_rebar_overrides(
                    df_g[df_g["Geschoss"] == storey_name],
                    st.session_state["rebar_overrides"]
                )["Bewehrung_kg"].sum()
            )

        st.markdown(f"### Summe Gebäude **{geb_name or '—'}**: {geb_total_kg:,.0f} kg")
        st.divider()
        project_total_kg += geb_total_kg

    st.subheader(f"🧮 Projekt-Gesamtsumme Bewehrung: {project_total_kg:,.0f} kg")
    st.session_state["rebar_total_kg"] = float(project_total_kg)

    # Wenn keine Bewehrung vorhanden ist, Kosten sicher auf 0 setzen
    if project_total_kg <= 0:
        st.session_state["rebar_total_cost"] = 0.0

    # -----------------------------
    # B) Aufteilung Fix / BG1 / BG2 / BGS + PREIS IM EXPANDER
    # -----------------------------
    st.divider()
    st.subheader("Aufteilung Bewehrung (B500B)")

    def _row(title_left: str, value_right: str, bold_right=False):
        cL, cR = st.columns([1, 1], gap="small")
        cL.write(title_left)
        cR.markdown(
            f"<div style='text-align:right;{'font-weight:600;' if bold_right else ''}'>{value_right}</div>",
            unsafe_allow_html=True
        )

    def render_rebar_group(label: str, img_name: str):
        with st.expander(f"B500B {label}", expanded=False):

            left, right = st.columns([1, 2], gap="large")
            with left:
                st.image("./assets/" + img_name, use_container_width=True)

            with right:
                form = st.form(f"rebar-split-{label}")
                data = st.session_state["rebar_split"][label]

                grp_pct = float(data.get("grp_pct", 0.0))
                b = {k: float(v) for k, v in data.get("bins", {}).items()}
                p = {k: float(v) for k, v in data.get("prices", {}).items()}

                form.markdown("**Anteile setzen**")

                c1, c2, c3 = form.columns([1, 1, 1])
                with c1:
                    grp_pct = form.number_input(
                        "Anteil Gruppe [%]",
                        min_value=0.0, max_value=100.0, step=1.0, format="%.1f",
                        value=grp_pct, key=f"grp-{label}"
                    )
                with c2:
                    b["8-10"] = form.number_input("Ø 8–10 [%]",  min_value=0.0, max_value=100.0, step=1.0, format="%.1f",
                                                  value=b.get("8-10", 0.0), key=f"bin1-{label}")
                    b["18-26"] = form.number_input("Ø 18–26 [%]", min_value=0.0, max_value=100.0, step=1.0, format="%.1f",
                                                   value=b.get("18-26", 0.0), key=f"bin3-{label}")
                with c3:
                    b["12-16"] = form.number_input("Ø 12–16 [%]", min_value=0.0, max_value=100.0, step=1.0, format="%.1f",
                                                   value=b.get("12-16", 0.0), key=f"bin2-{label}")
                    b["30-46"] = form.number_input("Ø 30–46 [%]", min_value=0.0, max_value=100.0, step=1.0, format="%.1f",
                                                   value=b.get("30-46", 0.0), key=f"bin4-{label}")

                # --- PREIS-FELDER DIREKT UNTER PROZENTEN ---
                form.markdown("---")
                form.markdown("**Preise setzen [CHF/kg]**")

                pc1, pc2, pc3, pc4 = form.columns(4, gap="small")
                p["8-10"]  = pc1.number_input(f"Preis Ø 8–10",  min_value=0.0, step=0.05, format="%.2f",
                                              value=p.get("8-10", default_rebar_price), key=f"price1-{label}")
                p["12-16"] = pc2.number_input(f"Preis Ø 12–16", min_value=0.0, step=0.05, format="%.2f",
                                              value=p.get("12-16", default_rebar_price), key=f"price2-{label}")
                p["18-26"] = pc3.number_input(f"Preis Ø 18–26", min_value=0.0, step=0.05, format="%.2f",
                                              value=p.get("18-26", default_rebar_price), key=f"price3-{label}")
                p["30-46"] = pc4.number_input(f"Preis Ø 30–46", min_value=0.0, step=0.05, format="%.2f",
                                              value=p.get("30-46", default_rebar_price), key=f"price4-{label}")

                # Vorschau
                total_grp_kg = project_total_kg * (grp_pct / 100.0)
                sum_bins_pct = b["8-10"] + b["12-16"] + b["18-26"] + b["30-46"]

                bin_kg_1 = total_grp_kg * (b["8-10"] / 100.0)
                bin_kg_2 = total_grp_kg * (b["12-16"] / 100.0)
                bin_kg_3 = total_grp_kg * (b["18-26"] / 100.0)
                bin_kg_4 = total_grp_kg * (b["30-46"] / 100.0)

                cost_1 = bin_kg_1 * p["8-10"]
                cost_2 = bin_kg_2 * p["12-16"]
                cost_3 = bin_kg_3 * p["18-26"]
                cost_4 = bin_kg_4 * p["30-46"]
                cost_grp = cost_1 + cost_2 + cost_3 + cost_4

                form.markdown("---")
                _row("Total Gruppe (Vorschau)", f"{total_grp_kg:,.0f} kg", bold_right=True)
                _row("Ø 8–10",  f"{bin_kg_1:,.0f} kg  →  {cost_1:,.2f} CHF")
                _row("Ø 12–16", f"{bin_kg_2:,.0f} kg  →  {cost_2:,.2f} CHF")
                _row("Ø 18–26", f"{bin_kg_3:,.0f} kg  →  {cost_3:,.2f} CHF")
                _row("Ø 30–46", f"{bin_kg_4:,.0f} kg  →  {cost_4:,.2f} CHF")
                _row("Check Summe Bins", f"{sum_bins_pct:.1f} %")
                _row("Kosten Gruppe (Vorschau)", f"{cost_grp:,.2f} CHF", bold_right=True)

                if form.form_submit_button("💾 Werte übernehmen"):
                    st.session_state["rebar_split"][label] = {"grp_pct": grp_pct, "bins": b, "prices": p}
                    st.success("Übernommen.")
                    st.rerun()

    # Vier Gruppen rendern
    render_rebar_group("Fix", "B500B fix.png")
    render_rebar_group("BG 1", "B500B bg1.png")
    render_rebar_group("BG 2", "B500B bg2.png")
    render_rebar_group("BG S", "B500B bgs.png")

    # -----------------------------
    # C) Matten-Zeile (wie Excel)
    # -----------------------------
    if "rebar_matten_pct" not in st.session_state:
        st.session_state["rebar_matten_pct"] = 15.0

    st.markdown("---")
    st.markdown("#### B500B Bewehrungsmatten")

    c1, c2, c3, c4 = st.columns([2.2, 1.0, 0.8, 2.0], gap="small")
    with c1:
        st.markdown("**B500B Bewehrungsmatten**")
    with c2:
        st.markdown("521.111")
    with c3:
        st.session_state["rebar_matten_pct"] = st.number_input(
            label="Anteil [%]",
            value=float(st.session_state["rebar_matten_pct"]),
            min_value=0.0,
            step=0.5,
            format="%.1f",
            label_visibility="collapsed",
            key="rebar_matten_pct_input",
        )

    matten_pct = float(st.session_state["rebar_matten_pct"])
    matten_kg  = project_total_kg * (matten_pct / 100.0)
    matten_cost = matten_kg * float(default_rebar_price)

    with c4:
        st.markdown(f"{matten_kg:,.0f} kg (inkl. 300 kg Firipa)")

    # -----------------------------
    # D) Totale kg + CHF Projektweit speichern
    # -----------------------------
    # Gruppen-Kosten aus Session lesen
    groups_total_kg = 0.0
    groups_total_cost = 0.0
    sum_groups_pct = 0.0

    for g_label, g_data in st.session_state["rebar_split"].items():
        gp = float(g_data["grp_pct"])
        bins = g_data["bins"]
        prices = g_data["prices"]

        sum_groups_pct += gp
        g_kg = project_total_kg * (gp / 100.0)
        groups_total_kg += g_kg

        for bin_name, bin_pct in bins.items():
            bin_kg = g_kg * (float(bin_pct) / 100.0)
            groups_total_cost += bin_kg * float(prices.get(bin_name, default_rebar_price))

    total_pct = sum_groups_pct + matten_pct
    total_rebar_cost = groups_total_cost + matten_cost

    st.markdown("---")
    st.markdown(
        f"**Total Devis Bewehrung:** {(groups_total_kg + matten_kg):,.0f} kg  "
        f"• **Kosten Bewehrung:** {total_rebar_cost:,.2f} CHF",
        unsafe_allow_html=True
    )

    st.session_state["rebar_total_cost"] = float(total_rebar_cost)

    if abs(total_pct - 100.0) > 1e-6:
        diff_kg = project_total_kg * ((100.0 - total_pct) / 100.0)
        st.warning(
            f"Prozent-Summe = {total_pct:.1f}% (abweichend von 100%). "
            f"Fehlende/Überschüssige Masse: {diff_kg:,.0f} kg."
        )


#Dataframe
with tab4:
    st.write("🧱 IFC-Datenrahmen für Debugging:", df_ifc)