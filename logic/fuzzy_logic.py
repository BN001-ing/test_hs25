# logic/fuzzy_logic.py

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Iterable, Tuple, Optional


def similarity(a: str, b: str) -> float:
    """
    Gibt eine Ähnlichkeit zwischen 0 und 100 zurück.
    100 = identisch, 0 = komplett verschieden.
    """
    a_clean = (a or "").strip().lower()
    b_clean = (b or "").strip().lower()
    if not a_clean and not b_clean:
        return 100.0
    if not a_clean or not b_clean:
        return 0.0

    return SequenceMatcher(None, a_clean, b_clean).ratio() * 100.0


def find_best_match(
    term: str,
    candidates: Iterable[str],
) -> Tuple[Optional[str], float]:
    """
    Sucht den ähnlichsten Eintrag in einer Kandidatenliste.

    Rückgabe:
        (bester_Treffer_oder_None, Score_0_bis_100)
    """
    best_name = None
    best_score = -1.0
    for cand in candidates:
        score = similarity(term, cand)
        if score > best_score:
            best_score = score
            best_name = cand
    if best_name is None:
        return None, 0.0
    return best_name, best_score
