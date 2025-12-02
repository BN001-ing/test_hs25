import ifcopenshell
import tempfile
from pathlib import Path

#IFC Importieren
def IMPORT_IFC(uploaded_ifc) -> "ifcopenshell.file.file":
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp:
                tmp.write(uploaded_ifc.getbuffer())
                tmp_path = Path(tmp.name)
        ifc_model = ifcopenshell.open(str(tmp_path))
        return(ifc_model)

#Atribute Löschen
def DELETE_ALL_ATTRIBUTES(ifc_model: "ifcopenshell.file.file") -> "ifcopenshell.file.file":

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
        return(ifc_model)