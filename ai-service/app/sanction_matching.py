# app/sanction_matching.py
from dataclasses import dataclass
from typing import List, Literal, Tuple

from Levenshtein import ratio as levenshtein_ratio  # similarity [0..1]

from .sanctions_loader import get_sanctions, _normalize, SanctionEntry


MatchType = Literal["exact", "fuzzy", "phonetic"]


@dataclass
class SanctionMatch:
    entry: SanctionEntry
    match_type: MatchType
    similarity: float   # 0..1
    matched_name: str


def _soundex(name: str) -> str:
    """
    Very simple Soundex-like algorithm for phonetic matching.
    Works on normalized ASCII (we already transliterate with Unidecode).
    """
    name = _normalize(name)
    if not name:
        return ""

    first_letter = name[0].upper()
    mapping = {
        "bfpv": "1", "cgjkqsxz": "2", "dt": "3",
        "l": "4", "mn": "5", "r": "6",
    }

    def code_for_char(c: str) -> str:
        for group, code in mapping.items():
            if c in group:
                return code
        return ""

    digits = []
    for c in name[1:]:
        d = code_for_char(c)
        if not d:
            continue
        if not digits or digits[-1] != d:
            digits.append(d)

    code = first_letter + "".join(digits)[:3]
    return code.ljust(4, "0")


def _phonetic_equal(a: str, b: str) -> bool:
    return _soundex(a) == _soundex(b) and _soundex(a) != ""


def match_sanctions_by_name(full_name: str, min_similarity: float = 0.8) -> List[SanctionMatch]:
    """
    Fuzzy + phonetic matching of a customer name against all sanctions.
    Returns ranked matches with metadata for LLM/scoring.
    """
    normalized = _normalize(full_name)
    if not normalized:
        return []

    data = get_sanctions()
    results: List[SanctionMatch] = []

    for entry in data.sanctions:
        entry_name_norm = _normalize(entry.name)
        if not entry_name_norm:
            continue

        # Exact normalized match
        if entry_name_norm == normalized:
            results.append(
                SanctionMatch(
                    entry=entry,
                    match_type="exact",
                    similarity=1.0,
                    matched_name=full_name,
                )
            )
            continue

        # Fuzzy similarity
        sim = levenshtein_ratio(normalized, entry_name_norm)
        if sim >= min_similarity:
            results.append(
                SanctionMatch(
                    entry=entry,
                    match_type="fuzzy",
                    similarity=float(sim),
                    matched_name=full_name,
                )
            )
            continue

        # Phonetic (when spelling differs but pronunciation is similar)
        if _phonetic_equal(normalized, entry_name_norm):
            results.append(
                SanctionMatch(
                    entry=entry,
                    match_type="phonetic",
                    similarity=0.85,  # heuristic
                    matched_name=full_name,
                )
            )

    # Sort by best similarity first, prefer exact > fuzzy > phonetic
    priority = {"exact": 3, "fuzzy": 2, "phonetic": 1}

    results.sort(
        key=lambda m: (priority[m.match_type], m.similarity),
        reverse=True,
    )
    return results
