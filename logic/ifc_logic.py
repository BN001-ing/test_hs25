# logic/ifc_logic.py

from __future__ import annotations

from typing import Tuple

import pandas as pd
import ifcopenshell

from ifc.extractor import IFCExtractor, import_ifc


def load_ifc_from_upload(uploaded_file) -> Tuple[ifcopenshell.file.file, pd.DataFrame]:
    """
    Nimmt eine von Streamlit hochgeladene IFC-Datei (st.file_uploader)
    und gibt zurück:

        - das ifcopenshell IFC-Modell
        - einen vorbereiteten Basis-DataFrame für KuBeKo

    Der DataFrame enthält mindestens:
        - Index: GlobalID
        - Spalten: Grundstück, Gebäude, Geschoss, Name, IFCClass, Material, Volumen_m3
    """
    if uploaded_file is None:
        raise ValueError("Kein IFC-File übergeben (uploaded_file is None).")

    ifc_model = import_ifc(uploaded_file)
    extractor = IFCExtractor(ifc_model)
    df_ifc = extractor.to_base_dataframe()
    df_ifc = normalize_ifc_dataframe(df_ifc)
    return ifc_model, df_ifc


def build_ifc_base_table(ifc_model: "ifcopenshell.file.file") -> pd.DataFrame:
    """
    Erzeugt aus einem vorhandenen ifcopenshell IFC-Modell
    den Basis-DataFrame für KuBeKo.

    Siehe auch: load_ifc_from_upload(...)
    """
    extractor = IFCExtractor(ifc_model)
    df_ifc = extractor.to_base_dataframe()
    df_ifc = normalize_ifc_dataframe(df_ifc)
    return df_ifc


def normalize_ifc_dataframe(df_ifc: pd.DataFrame) -> pd.DataFrame:
    """
    Vereinheitlicht den Basis-DataFrame:
        - stellt sicher, dass alle erwarteten Spalten vorhanden sind
        - entfernt "leere" Zeilen (ohne Gebäude, Geschoss, Name und ohne Volumen)
        - sortiert nach Gebäude, Geschoss, Name
    """
    if df_ifc is None or df_ifc.empty:
        return pd.DataFrame(
            columns=[
                "Grundstück",
                "Gebäude",
                "Geschoss",
                "Name",
                "IFCClass",
                "Material",
                "Volumen_m3",
            ]
        )

    df = df_ifc.copy()

    # Erwartete Spalten
    for col in ["Grundstück", "Gebäude", "Geschoss", "Name", "IFCClass", "Material", "Volumen_m3"]:
        if col not in df.columns:
            df[col] = "" if col != "Volumen_m3" else 0.0

    # "Leere" Zeilen entfernen:
    # → kein Gebäude, kein Geschoss, kein Name, Volumen_m3 == 0
    mask_nonempty = (
        df["Gebäude"].astype(str).str.strip().ne("")
        | df["Geschoss"].astype(str).str.strip().ne("")
        | df["Name"].astype(str).str.strip().ne("")
        | (df["Volumen_m3"].astype(float) != 0.0)
    )
    df = df[mask_nonempty].copy()

    # Sortierung für eine schönere Darstellung
    df = df.sort_values(by=["Grundstück", "Gebäude", "Geschoss", "Name"]).copy()

    # Index-Name konsistent halten
    if df.index.name != "GlobalID":
        df.index.name = "GlobalID"

    return df
