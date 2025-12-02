# logic/dashboard_logic.py

from __future__ import annotations

import pandas as pd


def build_dashboard_data(
    df_material_view: pd.DataFrame,
    total_rebar_cost: float = 0.0,
) -> dict:
    """
    Baut die Datenbasis für das Dashboard (Tab 1).

    Erwartet:
        df_material_view:
            - ist der Material-Tab-DataFrame NACH apply_price_overrides()
            - enthält u.a.:
                - 'Gebäude'
                - 'Geschoss'
                - 'Material'
                - 'Volumen_m3_sum'
                - 'Kosten_total_eff'
                - 'Anzahl_Elemente'

        total_rebar_cost:
            - Gesamtbewehrungskosten (CHF), z.B. aus Tab 3 (Session State).

    Rückgabe:
        dict mit:
            - project_total_cost
            - project_total_volume
            - material_cost
            - rebar_cost
            - cost_by_building (DataFrame)
            - cost_by_storey  (DataFrame)
            - vol_by_material (DataFrame)
            - cost_by_material (DataFrame)
            - elem_count
    """

    if df_material_view is None or df_material_view.empty:
        return {
            "project_total_cost": float(total_rebar_cost),
            "project_total_volume": 0.0,
            "material_cost": 0.0,
            "rebar_cost": float(total_rebar_cost),
            "cost_by_building": pd.DataFrame(columns=["Gebäude", "Kosten_total_eff"]),
            "cost_by_storey": pd.DataFrame(columns=["Gebäude", "Geschoss", "Kosten_total_eff"]),
            "vol_by_material": pd.DataFrame(columns=["Material", "Volumen_m3_sum"]),
            "cost_by_material": pd.DataFrame(columns=["Material", "Kosten_total_eff"]),
            "elem_count": 0,
        }

    df = df_material_view.copy()

    # Fallback-Spalten absichern
    for col in ["Kosten_total_eff", "Volumen_m3_sum", "Anzahl_Elemente"]:
        if col not in df.columns:
            df[col] = 0.0

    # Gesamtkosten & Volumen
    material_cost = float(df["Kosten_total_eff"].sum())
    total_volume = float(df["Volumen_m3_sum"].sum())
    rebar_cost = float(total_rebar_cost)
    total_cost = material_cost + rebar_cost

    # Summen nach Gebäude
    cost_by_building = (
        df.groupby("Gebäude", dropna=False)["Kosten_total_eff"]
        .sum()
        .reset_index()
        .sort_values("Kosten_total_eff", ascending=False)
    )

    # Summen nach Geschoss
    cost_by_storey = (
        df.groupby(["Gebäude", "Geschoss"], dropna=False)["Kosten_total_eff"]
        .sum()
        .reset_index()
        .sort_values(["Gebäude", "Geschoss"])
    )

    # Volumen nach Material
    vol_by_material = (
        df.groupby("Material", dropna=False)["Volumen_m3_sum"]
        .sum()
        .reset_index()
        .sort_values("Volumen_m3_sum", ascending=False)
    )

    # Kosten nach Material
    cost_by_material = (
        df.groupby("Material", dropna=False)["Kosten_total_eff"]
        .sum()
        .reset_index()
        .sort_values("Kosten_total_eff", ascending=False)
    )

    # Anzahl Elemente (über alle Gruppen)
    try:
        elem_count = int(df["Anzahl_Elemente"].sum())
    except Exception:
        elem_count = int(len(df))

    return {
        "project_total_cost": total_cost,
        "project_total_volume": total_volume,
        "material_cost": material_cost,
        "rebar_cost": rebar_cost,
        "cost_by_building": cost_by_building,
        "cost_by_storey": cost_by_storey,
        "vol_by_material": vol_by_material,
        "cost_by_material": cost_by_material,
        "elem_count": elem_count,
    }
