# app/sanctions_loader.py
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

from bs4 import BeautifulSoup  # type: ignore
from PyPDF2 import PdfReader  # type: ignore
from unidecode import unidecode


BASE_DIR = Path(__file__).resolve().parent
SANCTIONS_DIR = BASE_DIR.parent / "sunction-lists"


@dataclass
class FATFCategory:
    key: str
    name: str
    description: str
    countries: List[str]


@dataclass
class SanctionEntry:
    id: str
    name: str
    list_type: str  # "UN" | "EU" | "LOCAL"
    raw: dict


@dataclass
class SanctionsData:
    fatf_by_country: Dict[str, FATFCategory]           # normalized country -> category
    sanctions: List[SanctionEntry]
    names_index: Dict[str, List[SanctionEntry]]        # normalized name -> entries


def _normalize(text: str) -> str:
    """
    Aggressive normalization: lower, trim, remove extra spaces,
    transliterate to ASCII so Cyrillic/Latin become comparable.
    """
    if not text:
        return ""
    text = unidecode(text)
    text = text.strip().lower()
    # collapse spaces
    parts = text.split()
    return " ".join(parts)


def _load_fatf() -> Dict[str, FATFCategory]:
    path = SANCTIONS_DIR / "fatf-countries.json"
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    result: Dict[str, FATFCategory] = {}
    for cat_raw in data.get("categories", []):
        cat = FATFCategory(
            key=cat_raw["category_key"],
            name=cat_raw["category_name"],
            description=cat_raw.get("description", ""),
            countries=cat_raw.get("countries", []),
        )
        for country in cat.countries:
            result[_normalize(country)] = cat
    return result


def _load_un_sanctions() -> List[SanctionEntry]:
    """
    Very simple HTML parsing based on the UN sanctions HTML file.
    You may refine selectors when you see the exact structure.
    """
    path = SANCTIONS_DIR / "UN-sunctions-list.html"
    html = path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "lxml")

    entries: List[SanctionEntry] = []
    # Heuristic: assume sanctioned persons appear as <b>NAME</b> or in specific <td>.
    # Adjust selectors when you inspect the file in detail.
    for idx, bold in enumerate(soup.find_all("b")):
        name_text = bold.get_text(strip=True)
        if not name_text:
            continue
        entries.append(
            SanctionEntry(
                id=f"UN-{idx}",
                name=name_text,
                list_type="UN",
                raw={"source": "UN", "raw_text": name_text},
            )
        )
    return entries


def _load_eu_sanctions() -> List[SanctionEntry]:
    """
    Simple PDF scanning: treat all ALL-CAPS lines as potential names.
    This is heuristic – adjust thresholds to your PDF.
    """
    path = SANCTIONS_DIR / "EU-suctions-list.pdf"
    reader = PdfReader(str(path))

    entries: List[SanctionEntry] = []
    idx = 0
    for page in reader.pages:
        text = page.extract_text() or ""
        for line in text.splitlines():
            line = line.strip()
            if len(line) < 5:
                continue
            # crude heuristic for "name-like" lines
            if line.isupper():
                entries.append(
                    SanctionEntry(
                        id=f"EU-{idx}",
                        name=line,
                        list_type="EU",
                        raw={"source": "EU", "raw_text": line},
                    )
                )
                idx += 1
    return entries


def _build_names_index(sanctions: List[SanctionEntry]) -> Dict[str, List[SanctionEntry]]:
    index: Dict[str, List[SanctionEntry]] = {}
    for entry in sanctions:
        key = _normalize(entry.name)
        if not key:
            continue
        index.setdefault(key, []).append(entry)
    return index


@lru_cache(maxsize=1)
def get_sanctions() -> SanctionsData:
    """
    Load everything once per process and cache in memory.
    """
    fatf = _load_fatf()
    un_entries = _load_un_sanctions()
    eu_entries = _load_eu_sanctions()
    sanctions = un_entries + eu_entries  # local blacklist we’ll add later

    names_index = _build_names_index(sanctions)
    return SanctionsData(
        fatf_by_country=fatf,
        sanctions=sanctions,
        names_index=names_index,
    )


# Convenience helpers used elsewhere
def get_fatf_category(country_name: str) -> Optional[FATFCategory]:
    if not country_name:
        return None
    data = get_sanctions()
    return data.fatf_by_country.get(_normalize(country_name))


def is_name_sanctioned_exact(full_name: str) -> bool:
    if not full_name:
        return False
    data = get_sanctions()
    return _normalize(full_name) in data.names_index


def get_exact_sanction_matches(full_name: str) -> List[SanctionEntry]:
    if not full_name:
        return []
    data = get_sanctions()
    return data.names_index.get(_normalize(full_name), [])
