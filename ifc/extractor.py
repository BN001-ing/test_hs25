# ifc/extractor.py

from __future__ import annotations

import tempfile
from pathlib import Path
import os
from typing import Optional

import ifcopenshell
import pandas as pd

from .mapping import (
    get_all_global_ids_df,
    material_series_by_element,
    Verortung,
    KomponentenName,
)
from .geometry import compute_volumes_df


# --------------------------------------------------
# Low-Level Hilfsfunktionen
# --------------------------------------------------


def import_ifc(uploaded_ifc) -> "ifcopenshell.file.file":
    """
    IFC aus einem Streamlit UploadedFile (oder ähnlichem File-like Objekt) laden.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp:
        tmp.write(uploaded_ifc.getbuffer())
        tmp_path = Path(tmp.name)

    ifc_model = ifcopenshell.open(str(tmp_path))

    # Option: temporäre Datei wieder löschen (nicht zwingend nötig)
    try:
        os.remove(tmp_path)
    except OSError:
        pass

    return ifc_model


def delete_all_attributes(ifc_model: "ifcopenshell.file.file") -> "ifcopenshell.file.file":
    """
    Entfernt PropertySets, Mengen, Layer, Materialzuweisungen und Bezeichnungen
    aus einem IFC-Modell. (für DaReCo)
    """
    # Alle PropertySets löschen
    for pset in ifc_model.by_type("IfcPropertySet"):
        ifc_model.remove(pset)

    # Mengenermittlungen löschen
    for qto in ifc_model.by_type("IfcElementQuantity"):
        ifc_model.remove(qto)

    # Layer (CAD-Ebene)
    for layer in ifc_model.by_type("IfcPresentationLayerAssignment"):
        ifc_model.remove(layer)

    # Materialien
    for rel in ifc_model.by_type("IfcRelAssociatesMaterial"):
        ifc_model.remove(rel)
    for mtype in [
        "IfcMaterial",
        "IfcMaterialList",
        "IfcMaterialLayer",
        "IfcMaterialLayerSet",
        "IfcMaterialLayerSetUsage",
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

    return ifc_model


# --------------------------------------------------
# High-Level: IFCExtractor
# --------------------------------------------------


class IFCExtractor:
    """
    High-Level Helfer, um aus einem IFC-Modell einen einheitlichen Basis-DataFrame
    für KuBeKo zu erzeugen.

    Die Idee:
        extractor = IFCExtractor(ifc_model)
        df_ifc = extractor.to_base_dataframe()
    """

    def __init__(self, ifc_model: "ifcopenshell.file.file"):
        self.ifc = ifc_model

    def to_base_dataframe(self) -> pd.DataFrame:
        """
        Baut einen DataFrame mit folgenden Spalten:
            - GlobalID (Index)
            - Grundstück
            - Gebäude
            - Geschoss
            - Namen
            - IFCClass
            - Material
            - Volumen_m3
        """

        # 1) GlobalID + IFCClass
        df_ids = get_all_global_ids_df(self.ifc)
        df_ids = df_ids.set_index("GlobalID")

        # 2) Verortung (Grundstück, Gebäude, Geschoss)
        df_loc = Verortung(self.ifc)  # Index=GlobalId

        # 3) Material
        df_mat = material_series_by_element(self.ifc)  # Index=GlobalId

        # 4) Komponentenname
        df_name = KomponentenName(self.ifc)  # Index=GlobalId

        # 5) Volumen
        df_vol = compute_volumes_df(self.ifc)  # Index=GlobalId

        # Index-Namen angleichen
        df_loc.index.name = "GlobalID"
        df_mat.index.name = "GlobalID"
        df_name.index.name = "GlobalID"
        df_vol.index.name = "GlobalID"

        # alles der Reihe nach mergen (outer, damit nichts verloren geht)
        df = df_ids

        for extra in (df_loc, df_mat, df_name, df_vol):
            df = df.merge(extra, how="left", left_index=True, right_index=True)

        # Spalten etwas ordnen
        cols_order = [
            "Grundstück",
            "Gebäude",
            "Geschoss",
            "Name",
            "IFCClass",
            "Material",
            "Volumen_m3",
        ]
        for c in cols_order:
            if c not in df.columns:
                df[c] = ""

        df = df[cols_order]
        df.index.name = "GlobalID"
        return df
