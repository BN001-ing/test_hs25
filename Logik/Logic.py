# logic.py
from __future__ import annotations
import re
import unicodedata
from typing import Dict, Iterable, Tuple
import pandas as pd

try:
    # RapidFuzz ist schneller/stabiler als fuzzywuzzy + benötigt kein Levenshtein
    from rapidfuzz import fuzz, process
except ImportError:  # Fallback (zur Not)
    from fuzzywuzzy import fuzz, process  # type: ignore


# -----------------------
# Text-Normalisierung
# -----------------------
def _norm_txt(s: str | float | None) -> str:
    """robuste Normalisierung für fuzzy matching."""
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    s = str(s)
    s = unicodedata.normalize("NFKC", s)
    # Umlaute optional „vereinfachen“
    s = (s.replace("ä", "ae").replace("Ä", "Ae")
           .replace("ö", "oe").replace("Ö", "Oe")
           .replace("ü", "ue").replace("Ü", "Ue")
           .replace("ß", "ss"))
    s = s.casefold().strip()
    s = re.sub(r"\s+", " ", s)            # Mehrfachspaces -> 1 Space
    s = re.sub(r"[^\w\s\.\-\/%]", "", s)  # sonderzeichen, aber Punkte/Zahlen erlauben
    return s


def add_normalized_columns(df: pd.DataFrame,
                           cols: Iterable[str]) -> pd.DataFrame:
    """fügt zu jeder Spalte col eine col_norm hinzu (ohne Original zu verändern)."""
    for c in cols:
        n = f"{c}_norm"
        if n not in df.columns:
            df[n] = df[c].map(_norm_txt)
    return df


# -----------------------
# Fuzzy-Cluster / Mapping
# -----------------------
def _build_canonical_map(values: Iterable[str], text_match: int = 90
                         ) -> Dict[str, Tuple[str, int]]:
    """
    bildet ein Kanon-Set aus häufigsten Werten (greedy) und weist alle Unique-Werte
    dem besten Kanon zu, sofern score >= text_match.
    Rückgabe: {original -> (kanon, score)}
    """
    uniq = pd.Series(list(values)).dropna().unique().tolist()
    if not uniq:
        return {}
    # nach Häufigkeit später sinnvoll, hier reicht Alphabet – du kannst auch counts übergeben
    uniq.sort()

    canon: list[str] = []
    mapping: Dict[str, Tuple[str, int]] = {}

    for val in uniq:
        # besten exist. Kanon suchen
        if canon:
            best = process.extractOne(val, canon, scorer=fuzz.token_sort_ratio)
            if best and best[1] >= text_match:
                mapping[val] = (best[0], int(best[1]))
                continue
        # sonst selbst Kanon werden
        canon.append(val)
        mapping[val] = (val, 100)
    return mapping


def fuzzy_map_series(s: pd.Series, text_match: int = 90
                     ) -> Tuple[pd.Series, pd.Series]:
    """
    mappt eine Text-Serie per Fuzzy auf Kanon-Werte.
    Rückgabe: (key_series, score_series)
    """
    mapping = _build_canonical_map(s.dropna().map(_norm_txt).unique(), text_match)
    # Falls Serie leer o. nur NaN
    if not mapping:
        return pd.Series(index=s.index, dtype="object"), pd.Series(index=s.index, dtype="float")

    # lookup per normalisiertem Text
    norm = s.map(_norm_txt)
    # falls nicht gefunden -> unverändert, score 0
    key = norm.map(lambda v: mapping.get(v, (v, 0))[0])
    score = norm.map(lambda v: mapping.get(v, (v, 0))[1])
    return key, score


# -----------------------
# Preis-Matching (gegen Materialliste aus DB)
# -----------------------
def match_prices_by_material(df_grouped: pd.DataFrame,
                             df_prices: pd.DataFrame,
                             key_col: str = "Material_key",
                             text_match: int = 90) -> pd.DataFrame:
    """
    Sucht für df_grouped[key_col] per Fuzzy den besten Preis aus df_prices['Material'].
    Fügt Spalten 'Preis_CHF', 'price_matched_to', 'price_match_score' hinzu.
    """
    if df_prices is None or df_prices.empty:
        df_grouped["Preis_CHF"] = 0.0
        df_grouped["price_matched_to"] = ""
        df_grouped["price_match_score"] = 0
        return df_grouped

    # Norm-Spalte im Preis-DF
    p = df_prices.copy()
    name_col = "Material"
    if name_col not in p.columns:
        # Versuche alternative Namensgebung
        for alt in ["material_name", "material", "Name", "Bezeichnung"]:
            if alt in p.columns:
                name_col = alt
                break
    p["Material_norm"] = p[name_col].map(_norm_txt)

    # schneller Lookup: alle Zielkandidaten
    targets = p["Material_norm"].tolist()

    def _best_price(v: str) -> Tuple[float, str, int]:
        if not v:
            return 0.0, "", 0
        best = process.extractOne(v, targets, scorer=fuzz.token_sort_ratio)
        if not best:
            return 0.0, "", 0
        target_norm, score = best[0], int(best[1])
        if score < text_match:
            return 0.0, "", score
        row = p.loc[p["Material_norm"] == target_norm].iloc[0]
        # Preis-Spalte ermitteln
        price_col = None
        for c in ["Preis", "preis_chf", "Preis_CHF"]:
            if c in p.columns:
                price_col = c
                break
        price_val = float(row[price_col]) if price_col else 0.0
        return price_val, str(row[name_col]), score

    prices, matched_to, scores = [], [], []
    for v in df_grouped[key_col].map(_norm_txt):
        pr, mt, sc = _best_price(v)
        prices.append(pr)
        matched_to.append(mt)
        scores.append(sc)

    df_grouped = df_grouped.copy()
    df_grouped["Preis_CHF"] = prices
    df_grouped["price_matched_to"] = matched_to
    df_grouped["price_match_score"] = scores
    return df_grouped


# -----------------------
# Geschoss-Sortierschlüssel (UG < EG < 1.OG < 2.OG ...)
# -----------------------
_og_re = re.compile(r"(-?\d+)\s*\.?\s*og", flags=re.I)

def storey_sort_key(v: str | None) -> Tuple[int, int]:
    """macht aus 'UG','EG','1.OG','2. OG' einen sortierbaren Key."""
    if not v:
        return (999, 0)
    s = _norm_txt(v)
    if s in ("ug", "kg", "keller"):
        return (-1, 0)
    if s in ("eg", "pg", "erdgeschoss", "parterre"):
        return (0, 0)
    m = _og_re.search(s)
    if m:
        try:
            return (1, int(m.group(1)))
        except Exception:
            pass
    # sonst weit nach hinten
    return (998, 0)


# -----------------------
# Hauptfunktion für Tab 2
# -----------------------
def build_material_kubaturen(df_ifc: pd.DataFrame,
                             df_prices: pd.DataFrame | None = None,
                             text_match: int = 90,
                             col_map: Dict[str, str] | None = None
                             ) -> pd.DataFrame:
    """
    Erzeugt den gruppierten DataFrame für Tab 'Material Kubaturen':
    gruppiert über (Grundstück, Gebäude, Geschoss, Bauteil(Namen), Material)
    mit Fuzzy-Zusammenlegung und optionalem Preis-Match.
    """
    if df_ifc is None or df_ifc.empty:
        return pd.DataFrame(columns=[
            "Grundstück","Gebäude","Geschoss","Bauteil","Material",
            "Volumen_m3_sum","Anzahl_Elemente","Preis_CHF","Kosten_total"
        ])

    # Spaltenbelegung (falls bei dir 'Namen' anders heißt)
    col_map = col_map or {}
    c_grund = col_map.get("Grundstück", "Grundstück")
    c_gebae = col_map.get("Gebäude", "Gebäude")
    c_storey = col_map.get("Geschoss", "Geschoss")
    c_name = col_map.get("Bauteil", col_map.get("Namen", "Namen"))
    c_mat = col_map.get("Material", "Material")
    c_vol = col_map.get("Volumen", col_map.get("Volumen_m3", "Volumen_m3"))

    df = df_ifc.copy()

    # Normalisierte Spalten hinzufügen
    add_normalized_columns(df, [c_grund, c_gebae, c_storey, c_name, c_mat])

    # Fuzzy-Keys je Dimension
    df["Grundstück_key"], df["grund_score"] = fuzzy_map_series(df[c_grund], text_match)
    df["Gebäude_key"],     df["geb_score"]   = fuzzy_map_series(df[c_gebae], text_match)
    df["Geschoss_key"],    df["ges_score"]   = fuzzy_map_series(df[c_storey], text_match)
    df["Bauteil_key"],     df["name_score"]  = fuzzy_map_series(df[c_name], text_match)
    df["Material_key"],    df["mat_score"]   = fuzzy_map_series(df[c_mat], text_match)

    # Leere / nichtssagende Einträge (z. B. None oder "") entfernen
    df = df.dropna(subset=["Gebäude_key", "Geschoss_key", "Bauteil_key", "Material_key"], how="all")

    df = df[
    (df["Gebäude_key"].astype(str).str.strip() != "") &
    (df["Geschoss_key"].astype(str).str.strip() != "") &
    (df["Bauteil_key"].astype(str).str.strip() != "") &
    (df["Material_key"].astype(str).str.strip() != "")
    ]


    # Gruppieren
    grp_cols = ["Grundstück_key","Gebäude_key","Geschoss_key","Bauteil_key","Material_key"]
    g = (df
         .groupby(grp_cols, dropna=False, as_index=False)
         .agg(Volumen_m3_sum=(c_vol, "sum"),
              Anzahl_Elemente=("Material_key", "size"))
         )

    # Lesbare Spaltennamen
    g = g.rename(columns={
        "Grundstück_key":"Grundstück",
        "Gebäude_key":"Gebäude",
        "Geschoss_key":"Geschoss",
        "Bauteil_key":"Bauteil",
        "Material_key":"Material"
    })

    # Preise zuordnen (fuzzy gegen Materialliste)
    g = match_prices_by_material(g, df_prices, key_col="Material", text_match=text_match)

    # Kosten berechnen
    g["Kosten_total"] = g["Volumen_m3_sum"] * g["Preis_CHF"]

    # Sortieren: Grundstück/Gebäude alphabetisch, Geschoss über Sort-Key, dann Bauteil/Material
    g["__ges_key"] = g["Geschoss"].map(storey_sort_key)
    g = g.sort_values(by=["Grundstück","Gebäude","__ges_key","Bauteil","Material"]).drop(columns="__ges_key")

    # hübsche Ausgabe-Spalten
    out_cols = ["Grundstück","Gebäude","Geschoss","Bauteil","Material",
                "Volumen_m3_sum","Preis_CHF","Kosten_total","Anzahl_Elemente"]
    # Falls Debug des Matching gewünscht, kannst du diese weiteren Felder anzeigen:
    # ["price_matched_to","price_match_score"]

    # fehlende Spalten robust handhaben
    for c in out_cols:
        if c not in g.columns:
            g[c] = pd.NA
    return g[out_cols]

# Logic.py  (am Ende ergänzen)


OverrideKey = Tuple[str, str, str, str, str]  # (Grundstück, Gebäude, Geschoss, Bauteil, Material)

def apply_session_overrides(
    df_tab2: pd.DataFrame,
    overrides: Dict[OverrideKey, float] | None
) -> pd.DataFrame:
    """
    Wendet Preis-Overrides aus der Session auf den Tab2-DF an und berechnet Totale neu.
    - overrides: dict mit Key=(Grundstück,Gebäude,Geschoss,Bauteil,Material) -> Preis (float)
    - erwartet im df_tab2 mind. Spalten: Grundstück,Gebäude,Geschoss,Bauteil,Material,Volumen_m3_sum,Preis_CHF
    """
    if df_tab2 is None or df_tab2.empty:
        return df_tab2
    if not overrides:
        df = df_tab2.copy()
        df["Effektiver_Preis"] = df["Preis_CHF"].astype(float)
        df["Kosten_total_eff"] = df["Volumen_m3_sum"].astype(float) * df["Effektiver_Preis"]
        return df

    df = df_tab2.copy()
    # Schlüsselspalte bauen, um schnell zu mappen
    key_series = df.apply(
        lambda r: (str(r["Grundstück"]), str(r["Gebäude"]), str(r["Geschoss"]), str(r["Bauteil"]), str(r["Material"])),
        axis=1,
    )
    # effektiven Preis bestimmen
    eff_preise = []
    for k, auto in zip(key_series, df["Preis_CHF"].astype(float)):
        if k in overrides and overrides[k] is not None:
            eff_preise.append(float(overrides[k]))
        else:
            eff_preise.append(float(auto))
    df["Effektiver_Preis"] = eff_preise
    df["Kosten_total_eff"] = df["Volumen_m3_sum"].astype(float) * df["Effektiver_Preis"]
    return df
