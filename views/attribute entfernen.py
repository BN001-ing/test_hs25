import pandas as pd
import streamlit as st
import ifcopenshell
import ifcopenshell.util.element
import tempfile
from pathlib import Path
import tempfile, os
import Logik.IFC as IFC

st.title("🧹 DaReCo")

uploaded_files = st.file_uploader(
    "Upload data", accept_multiple_files=True, type="ifc"
)
if not uploaded_files:
    st.stop()

for uploaded_file in uploaded_files:
    st.write(f"📂 Verarbeite Datei: {uploaded_file.name}")

    #Datei Importieren
    ifc_model = IFC.IMPORT_IFC(uploaded_file)

    #Attribute Löschen
    ifc_model = IFC.DELETE_ALL_ATTRIBUTES(ifc_model)

    st.success("Alle Attribute und PropertySets wurden entfernt!")

    # Datei speichern
    output_name = uploaded_file.name.replace(".ifc", "_clean.ifc")
    ifc_model.write(output_name)
    clicked = st.download_button(
        "⬇️ Bereinigte IFC-Datei herunterladen",
        data=open(output_name, "rb").read(),
        file_name=output_name,
        mime="application/octet-stream",
        )
    if clicked:
        try:
            os.remove(Path(output_name))
            st.caption("🧽 Temporäre Datei wurde gelöscht.")
        except OSError as e:
            st.warning(f"Temp-Datei konnte nicht gelöscht werden: {e}")