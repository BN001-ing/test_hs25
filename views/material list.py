import streamlit as st
import Logik.Datenbank as db
import pandas as pd
import time

EINHEITEN = ["CHF/m³", "CHF/kg"]

@st.dialog("Material hinzufügen")
def show_add_material():
    conn = db.connect()
    db.create_tables(conn)  # kannst du auch global beim Start machen

    material_name = st.text_input("Material Name")
    
    einheit = st.selectbox(
        "Einheit",
        EINHEITEN,
        index=None,
        placeholder="Einheit wählen..."
    )

    preis_chf = st.number_input(
        "Preis [CHF]",
        min_value=0.0,      # keine negativen Preise
        step=1.0,
        format="%.2f",
    )

    if st.button("Hinzufügen"):
        if not material_name.strip():
            st.warning("Bitte einen Materialnamen eingeben.")
            return
        if einheit is None:
            st.warning("Bitte eine Einheit auswählen.")
            return
        if preis_chf <= 0:
            st.warning("Bitte einen Preis grösser 0 eingeben.")
            return
        if db.material_exists(material_name.strip()):
            st.info(f"Material '{material_name.strip()}' existiert bereits.")
            return
        db.add_material(material_name.strip(), einheit, float(preis_chf))
        st.success(f"Material '{material_name.strip()}' wurde hinzugefügt.")
        conn.close()
        st.rerun()


@st.dialog("Reset Datenbank")
def show_reset_db():
    conn = db.connect()
    db.create_tables(conn)

    st.caption("Wenn du die Rangliste wirklich **reseten** wilst tippe **JA** ein")
    st.caption("Es müssen danach alle Spieler neu erfast werden!")
    Reset = st.text_input("JA")
    if Reset == "JA":
        db.clear_database()
        st.success(f"Datenbakn resetet")


conn = db.connect()
db.create_tables(conn)

if st.button("Zurück",icon="🔙" ,width="stretch"):
        st.switch_page("views/auswertung.py")

st.title("Materialdatenbank")

if st.button("Material hinzufügen"):
    show_add_material()

#---RANGLISTE---

materials = db.get_all_materials()
if not materials:
    st.info("Noch keine Spieler vorhanden.")
else:
    rows = db.get_all_materials()
    df = pd.DataFrame(
        rows,
        columns=["ID", "Material", "Einheit", "Preis", "Aktualisiert"]
    )

    # ID nicht bearbeitbar, Index ausblenden
    edited_df = st.data_editor(
        df,
        column_config={
            "ID": st.column_config.NumberColumn("ID", disabled=True),
            "Material": st.column_config.TextColumn("Material", disabled=True),
            "Einheit": st.column_config.TextColumn("Einheit", disabled=True),
            "Preis": st.column_config.NumberColumn(
                "Preis [CHF]",
                min_value=0.0,
                step=1.0,
                format="%.2f",
            ),
            "Aktualisiert": st.column_config.TextColumn("Aktualisiert", disabled=True),
        },
        hide_index=True,
        use_container_width=True,
    )

    if st.button("Änderungen speichern"):
        for row in edited_df.itertuples(index=False):
            db.update_material(
                material_id=row.ID,
                material_name=row.Material,
                einheit=row.Einheit,
                preis_chf=float(row.Preis) if row.Preis is not None else 0.0,
            )
        st.success("Änderungen gespeichert.")
        time.sleep(1.0)  # ⏸ 1.0 Sekunden warten
        st.rerun()

    # ---Reset-Dialog---
    st.divider()
    if st.button("Reset Datenbank"):
        show_reset_db()