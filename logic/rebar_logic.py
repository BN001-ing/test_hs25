# logic/rebar_logic.py

from __future__ import annotations

from typing import Dict, Tuple

import pandas as pd

from .material_logic import _clean_str, KubekoKey


def build_rebar_kubaturen(
    df_ifc: pd.DataFrame,
    beton_keywords=None,
) -> pd.DataFrame:
    """
    Filtert df_ifc auf betonrelevante Bauteile und aggregiert nach:
        - Grundstück
        - Gebäude
        - Geschoss
        - Bauteil (Name)
        - Material

    beton_keywords:
        Liste von Stichwörtern, die im Materialnamen vorkommen müssen,
        z.B. ["beton", "c25/30"] (case-insensitive).
        Wenn None → es wird nur geprüft, ob 'beton' im Material steht.

    Rückgabe-DataFrame:
        - Grundstück, Gebäude, Geschoss, Bauteil, Material
        - Volumen_m3_sum
        - Anzahl_Elemente
        - kg_m3_auto (Standard = 0.0)
        - kg_m3_eff  (wird durch apply_rebar_overrides gesetzt)
        - Bewehrung_kg
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
                "kg_m3_auto",
                "kg_m3_eff",
                "Bewehrung_kg",
            ]
        )

    base = df_ifc.copy()
    for col in ["Grundstück", "Gebäude", "Geschoss", "Name", "Material", "Volumen_m3"]:
        if col not in base.columns:
            base[col] = "" if col != "Volumen_m3" else 0.0

    # Beton-Filter
    if beton_keywords is None:
        beton_keywords = ["beton"]

    def is_beton(material: str) -> bool:
        m = (material or "").lower()
        return any(kw.lower() in m for kw in beton_keywords)

    base = base[base["Material"].astype(str).apply(is_beton)]
    if base.empty:
        return pd.DataFrame(
            columns=[
                "Grundstück",
                "Gebäude",
                "Geschoss",
                "Bauteil",
                "Material",
                "Volumen_m3_sum",
                "Anzahl_Elemente",
                "kg_m3_auto",
                "kg_m3_eff",
                "Bewehrung_kg",
            ]
        )

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

    agg["kg_m3_auto"] = 0.0
    agg["kg_m3_eff"] = 0.0
    agg["Bewehrung_kg"] = 0.0

    return agg


def apply_rebar_overrides(
    df_rebar: pd.DataFrame,
    overrides: Dict[KubekoKey, float],
    default_kg_m3: float = 0.0,
) -> pd.DataFrame:
    """
    Wendet Benutzer-Overrides (kg/m³) auf die Rebar-Kubaturen an.

    overrides:
        Dict[ (Grundstück, Gebäude, Geschoss, Bauteil, Material) ] -> kg_m3_eff

    Ergänzt/aktualisiert im DataFrame:
        - kg_m3_eff
        - Bewehrung_kg
    """

    if df_rebar is None or df_rebar.empty:
        return df_rebar

    df = df_rebar.copy()

    if "kg_m3_auto" not in df.columns:
        df["kg_m3_auto"] = float(default_kg_m3)

    if "Volumen_m3_sum" not in df.columns:
        df["Volumen_m3_sum"] = 0.0

    kg_eff_list = []
    kg_total_list = []

    for _, row in df.iterrows():
        key = (
            _clean_str(row.get("Grundstück", "")),
            _clean_str(row.get("Gebäude", "")),
            _clean_str(row.get("Geschoss", "")),
            _clean_str(row.get("Bauteil", "")),
            _clean_str(row.get("Material", "")),
        )

        vol = float(row["Volumen_m3_sum"])
        base_kg_m3 = float(row.get("kg_m3_auto", default_kg_m3))

        eff_kg_m3 = float(overrides.get(key, base_kg_m3))
        kg_eff_list.append(eff_kg_m3)
        kg_total_list.append(eff_kg_m3 * vol)

    df["kg_m3_eff"] = kg_eff_list
    df["Bewehrung_kg"] = kg_total_list

    return df


# --------------------------------------------------
# Rebar-Split (Fix, BG1, BG2, BGS, Matten)
# --------------------------------------------------


def compute_rebar_split_totals(
    project_total_kg: float,
    rebar_split: dict,
    matten_pct: float,
    default_rebar_price: float,
) -> dict:
    """
    Rechnet aus:
        - kg und CHF pro Gruppe (Fix, BG1, BG2, BGS)
        - kg und CHF für Matten
        - Gesamtsummen kg + CHF
        - Summe aller Prozente

    Erwartete Struktur von rebar_split:

    rebar_split = {
        "Fix": {
            "grp_pct": 40.0,
            "bins": {"8-10": 50.0, "12-16": 35.0, "18-26": 10.0, "30-46": 5.0},
            "prices": {"8-10": 2.0, "12-16": 2.1, "18-26": 2.2, "30-46": 2.5},
        },
        "BG 1": { ... },
        ...
    }
    """

    groups_result = {}
    groups_total_kg = 0.0
    groups_total_cost = 0.0
    groups_total_pct = 0.0

    for label, data in rebar_split.items():
        grp_pct = float(data.get("grp_pct", 0.0))
        bins = data.get("bins", {}) or {}
        prices = data.get("prices", {}) or {}

        groups_total_pct += grp_pct

        group_kg = project_total_kg * (grp_pct / 100.0)
        groups_total_kg += group_kg

        bin_results = {}
        group_cost = 0.0

        for bin_name in ["8-10", "12-16", "18-26", "30-46"]:
            bin_pct = float(bins.get(bin_name, 0.0))
            price = float(prices.get(bin_name, default_rebar_price))

            kg_bin = group_kg * (bin_pct / 100.0)
            cost_bin = kg_bin * price

            group_cost += cost_bin
            bin_results[bin_name] = {
                "pct": bin_pct,
                "kg": kg_bin,
                "price": price,
                "cost": cost_bin,
            }

        groups_total_cost += group_cost

        groups_result[label] = {
            "grp_pct": grp_pct,
            "group_kg": group_kg,
            "group_cost": group_cost,
            "bins": bin_results,
        }

    # Matten
    matten_pct = float(matten_pct)
    matten_kg = project_total_kg * (matten_pct / 100.0)
    matten_cost = matten_kg * float(default_rebar_price)

    total_pct = groups_total_pct + matten_pct
    total_kg = groups_total_kg + matten_kg
    total_cost = groups_total_cost + matten_cost

    return {
        "groups": groups_result,
        "groups_total_kg": groups_total_kg,
        "groups_total_cost": groups_total_cost,
        "groups_total_pct": groups_total_pct,
        "matten_kg": matten_kg,
        "matten_cost": matten_cost,
        "total_pct": total_pct,
        "total_kg": total_kg,
        "total_cost": total_cost,
    }
