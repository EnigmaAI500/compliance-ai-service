from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from bs4 import BeautifulSoup  # type: ignore
from PyPDF2 import PdfReader  # type: ignore


@dataclass
class FATFCategory:
    key: str
    name: str
    description: str
    countries: List[str]


@dataclass
class SanctionEntry:
    source: str  # "UN" or "EU"
    name: str
    raw: str


@dataclass
class SanctionsDataset:
    as_of: Optional[str]
    fatf_categories: Dict[str, FATFCategory]
    fatf_country_index: Dict[str, str]  # normalized country -> category_key
    un_entries: List[SanctionEntry]
    eu_entries: List[SanctionEntry]
    names_index: Dict[str, List[SanctionEntry]]  # normalized name -> entries


_SANCTIONS_CACHE: Optional[SanctionsDataset] = None


def _base_dir() -> Path:
    """
    app/sanctions_loader.py -> app -> ai-service
    base_dir will be the ai-service directory where sunction-lists/ lives.
    """
    return Path(__file__).resolve().parent.parent


def _normalize(text: str) -> str:
    return " ".join(text.upper().split())


# ---------- FATF JSON ----------

def _load_fatf(base_dir: Path) -> tuple[Optional[str], Dict[str, FATFCategory], Dict[str, str]]:
    path = base_dir / "sunction-lists" / "fatf-countries.json"
    if not path.exists():
        raise FileNotFoundError(f"FATF JSON not found at {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    categories: Dict[str, FATFCategory] = {}
    country_index: Dict[str, str] = {}
    as_of = data.get("as_of")

    for cat in data.get("categories", []):
        category = FATFCategory(
            key=cat["category_key"],
            name=cat.get("category_name", cat["category_key"]),
            description=cat.get("description", ""),
            countries=cat.get("countries", []),
        )
        categories[category.key] = category
        for country in category.countries:
            country_index[_normalize(country)] = category.key

    return as_of, categories, country_index


# ---------- UN HTML ----------

def _load_un_html(base_dir: Path) -> List[SanctionEntry]:
    """
    Very simple parser for UN sanctions HTML.
    Assumes the 2nd <td> in a row is the name. You can refine later.
    """
    path = base_dir / "sunction-lists" / "UN-sunctions-list.html"
    if not path.exists():
        return []

    html = path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "lxml")

    entries: List[SanctionEntry] = []

    for row in soup.find_all("tr"):
        cols = row.find_all("td")
        if len(cols) < 2:
            continue

        name = cols[1].get_text(" ", strip=True)
        if not name:
            continue

        # Skip header rows
        if "name" in name.lower():
            continue

        raw_text = row.get_text(" ", strip=True)
        entries.append(SanctionEntry(source="UN", name=name, raw=raw_text))

    return entries


# ---------- EU PDF ----------

def _load_eu_pdf(base_dir: Path) -> List[SanctionEntry]:
    """
    Naive text extraction from EU PDF.
    Treats each non-empty line as a potential 'entry'.
    Improve heuristics later if needed.
    """
    path = base_dir / "sunction-lists" / "EU-suctions-list.pdf"
    if not path.exists():
        return []

    reader = PdfReader(str(path))
    text_parts: List[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        text_parts.append(page_text)

    full_text = "\n".join(text_parts)
    entries: List[SanctionEntry] = []

    for line in full_text.splitlines():
        line = line.strip()
        if not line:
            continue

        # Skip very short or obvious headings
        if len(line) < 5:
            continue
        if line.isupper() and "COUNCIL" in line:
            continue

        entries.append(SanctionEntry(source="EU", name=line, raw=line))

    return entries


# ---------- Public API with caching ----------

def load_sanctions() -> SanctionsDataset:
    """
    Load sanction data from disk (no caching).
    """
    base_dir = _base_dir()
    as_of, fatf_categories, fatf_country_index = _load_fatf(base_dir)
    un_entries = _load_un_html(base_dir)
    eu_entries = _load_eu_pdf(base_dir)

    names_index: Dict[str, List[SanctionEntry]] = {}
    for entry in un_entries + eu_entries:
        key = _normalize(entry.name)
        names_index.setdefault(key, []).append(entry)

    return SanctionsDataset(
        as_of=as_of,
        fatf_categories=fatf_categories,
        fatf_country_index=fatf_country_index,
        un_entries=un_entries,
        eu_entries=eu_entries,
        names_index=names_index,
    )


def get_sanctions() -> SanctionsDataset:
    """
    Get sanctions data with simple in-process cache.
    """
    global _SANCTIONS_CACHE
    if _SANCTIONS_CACHE is None:
        _SANCTIONS_CACHE = load_sanctions()
    return _SANCTIONS_CACHE


def refresh_sanctions() -> SanctionsDataset:
    """
    Force reload from disk into the cache.
    """
    global _SANCTIONS_CACHE
    _SANCTIONS_CACHE = load_sanctions()
    return _SANCTIONS_CACHE


# ---------- Convenience helpers for your endpoints ----------

def get_fatf_category_for_country(country: str) -> Optional[str]:
    """
    Returns FATF category key ("black_list", "grey_list", etc.) for a country name.
    Assumes you send full country names like in fatf-countries.json.
    """
    if not country:
        return None
    data = get_sanctions()
    return data.fatf_country_index.get(_normalize(country))


def compute_country_risk_score(country_of_birth: str, residency_country: str) -> int:
    """
    Map FATF category to a numeric risk score for ML.
    """
    cat_scores = {
        "black_list": 90,
        "grey_list": 60,
        None: 10,  # default if not present
    }

    cats = [
        get_fatf_category_for_country(country_of_birth),
        get_fatf_category_for_country(residency_country),
    ]

    return max(cat_scores.get(cat, 10) for cat in cats)


def is_name_sanctioned(full_name: str) -> bool:
    if not full_name:
        return False
    data = get_sanctions()
    return _normalize(full_name) in data.names_index


def get_sanction_matches(full_name: str) -> List[SanctionEntry]:
    if not full_name:
        return []
    data = get_sanctions()
    return data.names_index.get(_normalize(full_name), [])
