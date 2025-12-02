# ifc/geometry.py

from __future__ import annotations

import pandas as pd
import numpy as np
import ifcopenshell
import ifcopenshell.geom


def compute_volumes_df(ifc: "ifcopenshell.file.file") -> pd.DataFrame:
    """
    Berechnet das Volumen aller IfcBuildingElement-Objekte über die triangulierte Geometrie.

    Rückgabe:
        DataFrame mit Spalten:
            - 'GlobalId' (Index)
            - 'Volumen_m3' (gerundet auf 2 Dezimalstellen)
    """
    # --- Settings sicher setzen (nur wenn vorhanden) ---
    settings = ifcopenshell.geom.settings()

    def safe_set(name: str, value):
        if hasattr(settings, name):
            settings.set(getattr(settings, name), value)

    # typische, sinnvolle Settings
    safe_set("USE_WORLD_COORDS", True)               # globale Koordinaten
    safe_set("DISABLE_OPENING_SUBTRACTIONS", False)  # Öffnungen abziehen
    safe_set("SEW_SHELLS", True)                     # Flächen vernähen (hilft bei Volumen)

    # --- IFC-Einheiten -> Meter ---
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
            vol_local = mesh_volume(geom.verts, geom.faces)  # in IFC-Längeneinheit^3
        except Exception:
            vol_local = 0.0

        vol_m3 = np.round(float(vol_local) * (unit_scale**3), 2)
        rows.append({"GlobalId": gid, "Volumen_m3": vol_m3})

    df = pd.DataFrame(rows)
    df = df.set_index("GlobalId")
    return df


# Alias für Kompatibilität mit deinem alten Namen
def Volumen_geom(ifc: "ifcopenshell.file.file") -> pd.DataFrame:
    return compute_volumes_df(ifc)
