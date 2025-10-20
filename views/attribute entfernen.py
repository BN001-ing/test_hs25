import pandas as pd
import streamlit as st
import ifcopenshell
import ifcopenshell.util.element
import tempfile
from pathlib import Path
import tempfile, os

st.title("🧹 IFC Attribut-Cleaner")

uploaded_files = st.file_uploader(
    "Upload data", accept_multiple_files=True, type="ifc"
)
if not uploaded_files:
    st.stop()

for uploaded_file in uploaded_files:
    st.write(f"📂 Verarbeite Datei: {uploaded_file.name}")

    #Datei Kurzfristig zwischenspeichern und öffnen
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp:
            tmp.write(uploaded_file.getbuffer())
            tmp_path = Path(tmp.name)
    ifc_model = ifcopenshell.open(str(tmp_path))

    # Alle PropertySets löschen
    for pset in ifc_model.by_type("IfcPropertySet"):
        ifc_model.remove(pset)

    # Mengenermittlungen Löschen
    for qto in ifc_model.by_type("IfcElementQuantity"):
        ifc_model.remove(qto)

    # Layer (CAD-Ebene)
    for layer in ifc_model.by_type("IfcPresentationLayerAssignment"):
        ifc_model.remove(layer)

    # Materialien
    for rel in ifc_model.by_type("IfcRelAssociatesMaterial"):
        ifc_model.remove(rel)
    for mtype in [
        "IfcMaterial", "IfcMaterialList",
        "IfcMaterialLayer", "IfcMaterialLayerSet", "IfcMaterialLayerSetUsage"
    ]:
        for m in ifc_model.by_type(mtype):
            ifc_model.remove(m)

    # Namen leeren
    for el in ifc_model.by_type("IfcElement"):
        if getattr(el, "Name", None):
            el.Name = None
        if getattr(el, "ObjectType", None):
            el.ObjectType = None
        if getattr(el, "Description", None):
            el.Description = None

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