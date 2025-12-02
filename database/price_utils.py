# database/price_utils.py

from __future__ import annotations

from typing import Optional

import pandas as pd

from . import datenbank as db


def load_price_dataframe() -> pd.DataFrame:
    """
    Lädt alle Materialien samt Preisen aus der SQLite-Datenbank und gibt
    einen übersichtlichen DataFrame zurück.

    Spalten:
        - ID
        - Material
        - Einheit
        - Preis
        - Aktualisiert
    """
    # Stellt sicher, dass die Tabelle existiert
    db.create_tables()

    materials = db.get_all_materials()
    if not materials:
        # Leeren DataFrame mit den erwarteten Spalten zurückgeben
        return pd.DataFrame(
            columns=["ID", "Material", "Einheit", "Preis", "Aktualisiert"]
        )

    df = pd.DataFrame(
        materials,
        columns=["ID", "Material", "Einheit", "Preis", "Aktualisiert"],
    )
    return df


def get_default_material_price(
    df_prices: pd.DataFrame,
    material_name: str,
    default: float = 0.0,
) -> float:
    """
    Holt den Preis für ein gegebenes Material aus einem bereits geladenen
    DataFrame (z.B. aus load_price_dataframe()).

    - Vergleicht den Materialnamen case-insensitive.
    - Gibt 'default' zurück, wenn das Material nicht gefunden wird oder
      die Preisangabe ungültig ist.
    """
    if df_prices is None or df_prices.empty:
        return float(default)

    name_clean = (material_name or "").strip().lower()
    if not name_clean:
        return float(default)

    hits = df_prices[
        df_prices["Material"].astype(str).str.strip().str.lower() == name_clean
    ]
    if hits.empty:
        return float(default)

    try:
        price = float(hits.iloc[0]["Preis"])
    except Exception:
        return float(default)

    return price


def get_price_from_db(material_name: str, default: float = 0.0) -> float:
    """
    Komfortfunktion: Lädt intern die Preisliste aus der DB und gibt
    den Preis für 'material_name' zurück.

    Wird z.B. nützlich sein, um Standardpreise wie 'Bewehrung' zu ziehen,
    ohne im UI-Code direkt SQL / DB-Aufrufe zu haben.
    """
    df = load_price_dataframe()
    return get_default_material_price(df, material_name, default=default)


def build_price_lookup(df_prices: pd.DataFrame) -> dict[str, float]:
    """
    Erstellt ein Dictionary:
        { material_name_lower: preis }

    Damit kann in der Logik später sehr schnell auf Materialpreise
    zugegriffen werden (anstatt immer wieder DataFrame-Filter zu machen).
    """
    if df_prices is None or df_prices.empty:
        return {}

    lookup = {}
    for _, row in df_prices.iterrows():
        name = str(row.get("Material", "")).strip().lower()
        if not name:
            continue
        try:
            preis = float(row.get("Preis", 0.0))
        except Exception:
            preis = 0.0
        lookup[name] = preis

    return lookup
