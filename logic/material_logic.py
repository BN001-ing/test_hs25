# logic/material_logic.py

from __future__ import annotations

from typing import Dict, Tuple, Optional

import pandas as pd

from database.price_utils import build_price_lookup
from .fuzzy_logic import find_best_match

KubekoKey = Tuple[str, str, str, str, str]
# (Grundstück, Gebäude, Geschoss, Bauteil, Material)


# --------------------------------------------------
# Hilfsfunktionen
# --------------------------------------------------


def _clean_str(val) -> str:
    if val is None:
        return ""
    return str(val).strip()


def _build_key(row: pd.Series) -> KubekoKey:
    return (
        _clean_str(row.get("Grundstück", "")),
        _clean_str(row.get("Gebäude", "")),
        _clean_str(row.get("Geschoss", "")),
        _clean_str(row.get("Name", "")),
        _clean_str(row.get("Material", "")),
    )


# --------------------------------------------------
# Material-Kubaturen (für Tab 2)
# --------------------------------------------------


def build_material_kubaturen(
    df_ifc: pd.DataFrame,
    df_prices: Optional[pd.DataFrame] = None,
    text_match: float = 90.0,
) -> pd.DataFrame:
    """
    Erzeugt eine aggregierte Tabelle für die Material-Kubaturen (Tab 2).

    Gruppierung:
        - Grundstück
        - Gebäude
        - Geschoss
        - Name  (Bauteil)
        - Material

    Liefert Spalten:
        - Grundstück, Gebäude, Geschoss, Bauteil, Material
        - Volumen_m3_sum
        - Anzahl_Elemente
        - Preis_auto
        - Kosten_total_auto

    Overrides (Benutzerpreise) werden HIER noch NICHT berücksichtigt.
    """

    if df_ifc is None or df_ifc.empty:
        return pd.DataFrame(
            columns=[
                "Grundstück",
                "Gebäude",
                "Geschoss",
                "Bauteil",
                "Material",
                "Volumen_m3_sum",
                "Anzahl_Elemente",
                "Preis_auto",
                "Kosten_total_auto",
            ]
        )

    # Basis-Spalten sicherstellen
    base = df_ifc.copy()
    for col in ["Grundstück", "Gebäude", "Geschoss", "Name", "Material", "Volumen_m3"]:
        if col not in base.columns:
            base[col] = "" if col != "Volumen_m3" else 0.0

    # Gruppieren
    gcols = ["Grundstück", "Gebäude", "Geschoss", "Name", "Material"]
    agg = (
        base.groupby(gcols, dropna=False)
        .agg(
            Volumen_m3_sum=("Volumen_m3", "sum"),
            Anzahl_Elemente=("Volumen_m3", "size"),
        )
        .reset_index()
    )
    agg = agg.rename(columns={"Name": "Bauteil"})

    # Preise matchen, falls vorhanden
    agg["Preis_auto"] = 0.0
    agg["Kosten_total_auto"] = 0.0

    if df_prices is not None and not df_prices.empty:
        lookup = build_price_lookup(df_prices)  # material_name_lower → preis

        for idx, row in agg.iterrows():
            mat = _clean_str(row["Material"])
            if not mat:
                continue

            # 1) exakter Treffer
            mat_lower = mat.lower()
            price = lookup.get(mat_lower, None)

            # 2) fuzzy, falls nötig
            if price is None and lookup:
                best_name, score = find_best_match(mat, lookup.keys())
                if best_name is not None and score >= float(text_match):
                    price = lookup[best_name]

            if price is None:
                price = 0.0

            vol = float(row["Volumen_m3_sum"])
            agg.at[idx, "Preis_auto"] = float(price)
            agg.at[idx, "Kosten_total_auto"] = float(price) * vol

    return agg


def apply_price_overrides(
    df_material: pd.DataFrame,
    overrides: Dict[KubekoKey, float],
) -> pd.DataFrame:
    """
    Wendet Benutzer-Overrides (Preis [CHF/m³]) auf die Material-Kubaturen an.

    overrides:
        Dict[ (Grundstück, Gebäude, Geschoss, Bauteil, Material) ] -> preis_eff

    Ergänzt/aktualisiert im DataFrame:
        - Preis_eff
        - Kosten_total_eff
    """

    if df_material is None or df_material.empty:
        return df_material

    df = df_material.copy()

    if "Preis_auto" not in df.columns:
        df["Preis_auto"] = 0.0

    if "Volumen_m3_sum" not in df.columns:
        df["Volumen_m3_sum"] = 0.0

    preis_eff_list = []
    kosten_eff_list = []

    for _, row in df.iterrows():
        key = (
            _clean_str(row.get("Grundstück", "")),
            _clean_str(row.get("Gebäude", "")),
            _clean_str(row.get("Geschoss", "")),
            _clean_str(row.get("Bauteil", "")),
            _clean_str(row.get("Material", "")),
        )

        vol = float(row["Volumen_m3_sum"])
        base_price = float(row.get("Preis_auto", 0.0))

        # Override oder Standardpreis
        eff_price = float(overrides.get(key, base_price))
        preis_eff_list.append(eff_price)
        kosten_eff_list.append(eff_price * vol)

    df["Preis_eff"] = preis_eff_list
    df["Kosten_total_eff"] = kosten_eff_list

    return df


# --------------------------------------------------
# Dashboard-Auswertung (Tab 1)
# --------------------------------------------------


def build_dashboard_data(
    df_material_view: pd.DataFrame,
    total_rebar_cost: float = 0.0,
) -> dict:
    """
    Baut die Datenbasis für das Dashboard (Tab 1).

    Erwartet df_material_view = Material-Kubaturen MIT Preis_eff und Kosten_total_eff.
    """

    if df_material_view is None or df_material_view.empty:
        return {
            "project_total_cost": float(total_rebar_cost),
            "project_total_volume": 0.0,
            "material_cost": 0.0,
            "rebar_cost": float(total_rebar_cost),
            "cost_by_building": pd.DataFrame(),
            "cost_by_storey": pd.DataFrame(),
            "vol_by_material": pd.DataFrame(),
            "cost_by_material": pd.DataFrame(),
            "elem_count": 0,
        }

    df = df_material_view.copy()

    # Fallbacks
    for col in ["Kosten_total_eff", "Volumen_m3_sum"]:
        if col not in df.columns:
            df[col] = 0.0

    # Gesamtkosten & Volumen
    material_cost = float(df["Kosten_total_eff"].sum())
    total_volume = float(df["Volumen_m3_sum"].sum())
    total_cost = material_cost + float(total_rebar_cost)

    # Summen nach Gebäude
    cost_by_building = (
        df.groupby("Gebäude", dropna=False)["Kosten_total_eff"].sum().reset_index()
    )

    # Summen nach Geschoss
    cost_by_storey = (
        df.groupby(["Gebäude", "Geschoss"], dropna=False)["Kosten_total_eff"]
        .sum()
        .reset_index()
    )

    # Volumen nach Material
    vol_by_material = (
        df.groupby("Material", dropna=False)["Volumen_m3_sum"].sum().reset_index()
    )

    # Kosten nach Material
    cost_by_material = (
        df.groupby("Material", dropna=False)["Kosten_total_eff"].sum().reset_index()
    )

    elem_count = int(df["Anzahl_Elemente"].sum())

    return {
        "project_total_cost": total_cost,
        "project_total_volume": total_volume,
        "material_cost": material_cost,
        "rebar_cost": float(total_rebar_cost),
        "cost_by_building": cost_by_building,
        "cost_by_storey": cost_by_storey,
        "vol_by_material": vol_by_material,
        "cost_by_material": cost_by_material,
        "elem_count": elem_count,
    }
