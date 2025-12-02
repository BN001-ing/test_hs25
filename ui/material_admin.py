import streamlit as st
import pandas as pd

from database import datenbank as db


# --------------------------------------------------
# Dialog: Neues Material hinzufügen
# --------------------------------------------------
@st.dialog("Material hinzufügen")
def show_add_material_dialog() -> None:
    """Dialog zum Hinzufügen eines neuen Materials in die SQLite-DB."""
    conn = db.connect()
    db.create_tables()

    st.write("Bitte die Materialdaten eingeben:")

    material_name = st.text_input("Material", placeholder="z.B. Beton NPK B")
    einheiten_optionen = ["CHF/m³", "CHF/kg", "CHF/Stk"]
    einheit = st.selectbox("Einheit", einheiten_optionen, index=0)

    preis_chf = st.number_input(
        "Preis",
        min_value=0.0,
        step=1.0,
        format="%.2f",
        help="Einheitspreis in der gewählten Einheit",
    )

    if st.button("Speichern", type="primary", use_container_width=True):
        name_clean = material_name.strip()

        if not name_clean:
            st.warning("Bitte einen Materialnamen eingeben.")
            return

        # Preis muss > 0 sein
        if preis_chf <= 0:
            st.warning("Bitte einen Preis > 0 eingeben.")
            return

        # Prüfen, ob Material schon existiert
        if db.material_exists(name_clean):
            st.info(f"Material **'{name_clean}'** existiert bereits.")
            return

        # In DB schreiben
        db.add_material(name_clean, einheit, float(preis_chf))
        st.success(f"Material **'{name_clean}'** wurde gespeichert.")
        st.rerun()


# --------------------------------------------------
# Hauptseite: Material-Verwaltung
# --------------------------------------------------
def main() -> None:
    st.title("Materialdatenbank")

    # Verbindung / Tabellen sicherstellen
    conn = db.connect()
    db.create_tables()

    # -------------------- Toolbar --------------------
    col_btn, col_spacer = st.columns([1, 3])
    with col_btn:
        if st.button("➕ Material hinzufügen", use_container_width=True):
            show_add_material_dialog()

    st.caption("Hier verwaltest du alle Materialien und deren Preise für KuBeKo.")

    # -------------------- Daten laden --------------------
    materials = db.get_all_materials()  # erwartet: List[Tuple[id, name, einheit, preis, datum]]
    if not materials:
        st.info("Noch keine Materialien in der Datenbank. Füge oben ein erstes Material hinzu.")
        return

    df = pd.DataFrame(
        materials,
        columns=["ID", "Material", "Einheit", "Preis", "Aktualisiert"],
    )

    # ID als erste Spalte lassen, aber nicht editierbar
    # Datum ebenfalls nicht editierbar
    st.subheader("Material-Liste", anchor=False)

    edited_df = st.data_editor(
        df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "ID": st.column_config.NumberColumn("ID", help="Interne ID (nicht änderbar)"),
            "Material": st.column_config.TextColumn("Material"),
            "Einheit": st.column_config.TextColumn("Einheit"),
            "Preis": st.column_config.NumberColumn(
                "Preis",
                help="Einheitspreis",
                min_value=0.0,
                step=1.0,
                format="%.2f",
            ),
            "Aktualisiert": st.column_config.TextColumn(
                "Aktualisiert",
                help="Datum der letzten Änderung (wird automatisch gesetzt)",
            ),
        },
        disabled=["ID", "Aktualisiert"],
    )

    st.write("")  # kleiner Abstand

    # -------------------- Änderungen speichern --------------------
    col_save, col_reset = st.columns([2, 1])

    with col_save:
        if st.button("Änderungen speichern", type="primary", use_container_width=True):
            conn = db.connect()
            for _, row in edited_df.iterrows():
                material_id = int(row["ID"])
                name = str(row["Material"]).strip()
                einheit = str(row["Einheit"]).strip()
                preis = float(row["Preis"]) if row["Preis"] is not None else 0.0

                if not name:
                    st.warning(f"Material mit ID {material_id} hat keinen Namen – übersprungen.")
                    continue

                db.update_material(material_id, name, einheit, preis)

            st.success("Änderungen wurden gespeichert.")
            st.rerun()

    with col_reset:
        with st.popover("Datenbank zurücksetzen"):
            st.write(
                "⚠️ **Achtung:** Dies löscht alle Materialien aus der Datenbank.\n"
                "Dieser Schritt kann nicht rückgängig gemacht werden."
            )
            if st.button("Ja, alles löschen", type="secondary", use_container_width=True):
                db.clear_database()
                st.success("Materialdatenbank wurde geleert.")
                st.rerun()


# --------------------------------------------------
# Streamlit-Einstiegspunkt
# --------------------------------------------------
if __name__ == "__main__":
    main()
else:
    # Wenn die Seite über Main.py (st.navigation) geladen wird:
    main()
