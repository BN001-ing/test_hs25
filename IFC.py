import pandas as pd
import streamlit as st
import ifcopenshell
import ifcopenshell.util.element
import tempfile
from pathlib import Path
import tempfile, os
import numpy as np
import ifcopenshell.geom

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

def get_all_global_ids_df(ifc) -> pd.DataFrame:

    """
    Gibt einen DataFrame mit GlobalId und IFCClass zurück.
    """
    rows = []

    for elem in ifc.by_type("IfcProduct") or []:
        rows.append({
            "GlobalID": getattr(elem, "GlobalId", ""),
            "IFCClass": elem.is_a()
        })

    df = pd.DataFrame(rows)
    return df

def material_series_by_element(ifc) -> pd.Series:
    rows = []
    for e in ifc.by_type("IfcBuildingElement") or []:
        gid = getattr(e, "GlobalId", "")
        if not gid:
            continue
        mat_name = ""
        for rel in getattr(e, "HasAssociations", []) or []:
            if rel.is_a("IfcRelAssociatesMaterial"):
                m = rel.RelatingMaterial
                if not m:
                    continue
                if m.is_a("IfcMaterial"):
                    mat_name = m.Name or ""
                elif m.is_a("IfcMaterialLayerSetUsage") and m.ForLayerSet and m.ForLayerSet.MaterialLayers:
                    first = m.ForLayerSet.MaterialLayers[0]
                    mat_name = (first.Material.Name if first.Material else "") or ""
                elif m.is_a("IfcMaterialList") and m.Materials:
                    mat_name = (m.Materials[0].Name or "")
                # ggf. weitere Fälle ignorieren
                if mat_name:
                    break
        rows.append({"GlobalId": gid, "Material": mat_name})
        df_filterd = pd.DataFrame(rows)
        df_filterd = df_filterd.set_index("GlobalId")
    return (df_filterd)

def Verortung(ifc) -> pd.DataFrame:
    """
    Für alle IfcBuildingElement:
    - GlobalId (Index)
    - Grundstück  (IfcSite.Name)
    - Gebäude     (IfcBuilding.Name)
    - Geschoss    (IfcBuildingStorey.Name)
    """
    def climb_parents(spatial):
        """Generator: läuft per Decomposes→RelatingObject nach oben (Storey→Building→Site)."""
        curr = spatial
        seen = 0
        while curr and seen < 10:
            yielded = False
            for rel in getattr(curr, "Decomposes", []) or []:
                if rel.is_a("IfcRelAggregates"):
                    parent = rel.RelatingObject
                    if parent:
                        yield parent
                        curr = parent
                        yielded = True
                        break
            if not yielded:
                break
            seen += 1

    rows = []
    for e in ifc.by_type("IfcBuildingElement") or []:
        gid = getattr(e, "GlobalId", "")
        if not gid:
            continue

        grundst, geb, ges = "", "", ""

        # Element -> räumlicher Container (Storey/Building/Site)
        for rel in getattr(e, "ContainedInStructure", []) or []:
            if not rel or not rel.is_a("IfcRelContainedInSpatialStructure"):
                continue
            container = rel.RelatingStructure
            if not container:
                continue

            # Direkte Ebene
            if container.is_a("IfcBuildingStorey"):
                ges = container.Name or ""
            elif container.is_a("IfcBuilding"):
                geb = container.Name or ""
            elif container.is_a("IfcSite"):
                grundst = container.Name or ""

            # Eltern hochlaufen (bis Building / Site gefunden sind)
            for parent in climb_parents(container):
                if not geb and parent.is_a("IfcBuilding"):
                    geb = parent.Name or ""
                if not grundst and parent.is_a("IfcSite"):
                    grundst = parent.Name or ""
                if geb and grundst:
                    break

            # wir haben alles Wichtige – nächste Entity
            break

        rows.append({
            "GlobalId": gid,
            "Grundstück": grundst,
            "Gebäude": geb,
            "Geschoss": ges,
        })
        df_filterd = pd.DataFrame(rows)
        df_filterd = df_filterd.set_index("GlobalId")
    return (df_filterd)

def KomponentenName(ifc) -> pd.DataFrame:
    """
    Liest für alle IfcBuildingElement den Anzeigenamen aus:
      1) bevorzugt IFC-Attribut `Name`
      2) Fallback: Property namens 'Name' aus einem PropertySet
    Rückgabe: DataFrame mit Spalten ['GlobalId','Name'] und Index=GlobalId
    """
    rows = []

    for e in ifc.by_type("IfcBuildingElement") or []:
        gid = getattr(e, "GlobalId", "")
        if not gid:
            continue

        # 1) IFC-Attribut
        name = (getattr(e, "Name", None) or "").strip()

        # 2) Fallback über Properties (selten nötig, aber hilfreich)
        if not name:
            for rel in getattr(e, "IsDefinedBy", []) or []:
                if rel and rel.is_a("IfcRelDefinesByProperties"):
                    pdef = rel.RelatingPropertyDefinition
                    # Einzel-PropertySet
                    if pdef and pdef.is_a("IfcPropertySet") and getattr(pdef, "HasProperties", None):
                        for p in pdef.HasProperties or []:
                            if getattr(p, "Name", "") == "Name":
                                # Versuche gängigen Typ IfcPropertySingleValue
                                val = getattr(p, "NominalValue", None)
                                if val:
                                    name = str(getattr(val, "wrappedValue", val)) or ""
                                    break
                    if name:
                        break

        rows.append({"GlobalId": gid, "Name": name})

    df_filterd = pd.DataFrame(rows)
    df_filterd = df_filterd.set_index("GlobalId")
    return (df_filterd)

def Volumen_geom(ifc) -> pd.DataFrame:
    """
    Berechnet Volumen aller IfcBuildingElement-Objekte über die triangulierte Geometrie.
    Rückgabe: DataFrame ['GlobalId','Volumen_m3'] mit Index=GlobalId.
    """
     # --- settings sicher setzen (nur wenn vorhanden)
    settings = ifcopenshell.geom.settings()

    def safe_set(name, value):
        if hasattr(settings, name):
            settings.set(getattr(settings, name), value)

    # typische, sinnvolle Settings
    safe_set("USE_WORLD_COORDS", True)                # globale Koordinaten
    safe_set("DISABLE_OPENING_SUBTRACTIONS", False)   # Öffnungen abziehen
    safe_set("SEW_SHELLS", True)                      # Flächen vernähen (hilft bei Volumen)

    # --- IFC-Einheiten -> Meter
    try:
        from ifcopenshell.util.unit import calculate_unit_scale
        unit_scale = float(calculate_unit_scale(ifc))  # z.B. 1.0 (m), 0.001 (mm)
    except Exception:
        unit_scale = 1.0

    def mesh_volume(verts_flat, faces_flat) -> float:
        """Volumen eines geschlossenen Dreiecksnetzes (Tetraeder-Summenformel)."""
        if not verts_flat or not faces_flat:
            return 0.0
        V = np.asarray(verts_flat, dtype=float).reshape(-1, 3)
        F = np.asarray(faces_flat, dtype=int).reshape(-1, 3)
        v0 = V[F[:, 0]]
        v1 = V[F[:, 1]]
        v2 = V[F[:, 2]]
        vol = np.einsum("ij,ij->i", v0, np.cross(v1, v2)).sum() / 6.0
        return abs(vol)

    rows = []
    for elem in ifc.by_type("IfcBuildingElement") or []:
        gid = getattr(elem, "GlobalId", "")
        if not gid:
            continue
        vol_local = 0.0
        try:
            shape = ifcopenshell.geom.create_shape(settings, elem)
            geom = shape.geometry
            vol_local = mesh_volume(geom.verts, geom.faces)   # in IFC-Längeneinheit^3
        except Exception:
            vol_local = 0.0

        vol_m3 = np.round(float(vol_local) * (unit_scale ** 3),2)         # -> m³
        rows.append({"GlobalId": gid, "Volumen_m3": vol_m3})


    df_filterd = pd.DataFrame(rows)
    df_filterd = df_filterd.set_index("GlobalId")
    return (df_filterd)


