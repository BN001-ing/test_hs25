# ifc/mapping.py

from __future__ import annotations

import pandas as pd
import ifcopenshell


def get_all_global_ids_df(ifc: "ifcopenshell.file.file") -> pd.DataFrame:
    """
    Gibt einen DataFrame mit GlobalID und IFCClass zurück.
    Quelle: ifc.by_type("IfcProduct")
    """
    rows = []
    for elem in ifc.by_type("IfcProduct") or []:
        rows.append(
            {
                "GlobalID": getattr(elem, "GlobalId", ""),
                "IFCClass": elem.is_a(),
            }
        )

    df = pd.DataFrame(rows)
    return df


def material_series_by_element(ifc: "ifcopenshell.file.file") -> pd.DataFrame:
    """
    Liest das (erste) zugeordnete Material je IfcBuildingElement aus.
    Rückgabe: DataFrame mit Index=GlobalId, Spalte 'Material'
    """
    rows = []

    for e in ifc.by_type("IfcBuildingElement") or []:
        gid = getattr(e, "GlobalId", "")
        if not gid:
            continue

        mat_name = ""
        for rel in getattr(e, "HasAssociations", []) or []:
            if not rel or not rel.is_a("IfcRelAssociatesMaterial"):
                continue

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

    df = pd.DataFrame(rows)
    df = df.set_index("GlobalId")
    return df


def Verortung(ifc: "ifcopenshell.file.file") -> pd.DataFrame:
    """
    Für alle IfcBuildingElement:
    - GlobalId (Index)
    - Grundstück  (IfcSite.Name)
    - Gebäude     (IfcBuilding.Name)
    - Geschoss    (IfcBuildingStorey.Name)
    """

    def climb_parents(spatial):
        """
        Generator: läuft per Decomposes → RelatingObject nach oben
        (z.B. Storey → Building → Site).
        """
        curr = spatial
        seen = 0
        while curr and seen < 10:
            yielded = False
            for rel in getattr(curr, "Decomposes", []) or []:
                if not rel or not rel.is_a("IfcRelAggregates"):
                    continue
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

            # übergeordnete Ebenen
            for parent in climb_parents(container):
                if parent.is_a("IfcBuildingStorey") and not ges:
                    ges = parent.Name or ""
                elif parent.is_a("IfcBuilding") and not geb:
                    geb = parent.Name or ""
                elif parent.is_a("IfcSite") and not grundst:
                    grundst = parent.Name or ""

        rows.append(
            {
                "GlobalId": gid,
                "Grundstück": grundst,
                "Gebäude": geb,
                "Geschoss": ges,
            }
        )

    df = pd.DataFrame(rows)
    df = df.set_index("GlobalId")
    return df


def KomponentenName(ifc: "ifcopenshell.file.file") -> pd.DataFrame:
    """
    Liest für alle IfcBuildingElement den Anzeigenamen aus:
      1) bevorzugt IFC-Attribut `Name`
      2) Fallback: Property namens 'Name' aus einem PropertySet

    Rückgabe:
        DataFrame mit Spalten ['GlobalId', 'Name'] und Index=GlobalId
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
                if not rel or not rel.is_a("IfcRelDefinesByProperties"):
                    continue
                pdef = rel.RelatingPropertyDefinition

                # Einzel-PropertySet
                if pdef and pdef.is_a("IfcPropertySet") and getattr(pdef, "HasProperties", None):
                    for p in pdef.HasProperties or []:
                        if getattr(p, "Name", "") == "Name":
                            val = getattr(p, "NominalValue", None)
                            if val:
                                name = str(getattr(val, "wrappedValue", val)) or ""
                                break
                if name:
                    break

        rows.append({"GlobalId": gid, "Name": name})

    df = pd.DataFrame(rows)
    df = df.set_index("GlobalId")
    return df
