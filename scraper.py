from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence

import pandas as pd
import requests
from bs4 import BeautifulSoup


@dataclass(frozen=True)
class CategoryConfig:
    key: str
    label: str
    url: str
    field_name: str


CATEGORIES: Dict[str, CategoryConfig] = {
    "chiens": CategoryConfig(
        key="chiens",
        label="Chiens",
        url="https://sn.coinafrique.com/categorie/chiens",
        field_name="nom",
    ),
    "moutons": CategoryConfig(
        key="moutons",
        label="Moutons",
        url="https://sn.coinafrique.com/categorie/moutons",
        field_name="nom",
    ),
    "poules-lapins-et-pigeons": CategoryConfig(
        key="poules-lapins-et-pigeons",
        label="Poules, lapins et pigeons",
        url="https://sn.coinafrique.com/categorie/poules-lapins-et-pigeons",
        field_name="details",
    ),
    "autres-animaux": CategoryConfig(
        key="autres-animaux",
        label="Autres animaux",
        url="https://sn.coinafrique.com/categorie/autres-animaux",
        field_name="nom",
    ),
}

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}

DEFAULT_TIMEOUT_SECONDS = 20
DEFAULT_REQUEST_DELAY_SECONDS = 0.3
MAX_PAGES_LIMIT = 40


def build_page_url(base_url: str, page: int) -> str:
    if page <= 1:
        return base_url
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}page={page}"


def fetch_html(url: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> str:
    response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
    response.raise_for_status()
    return response.text


def normalize_text(value: Optional[str]) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def clean_price(price_text: Optional[str]) -> Optional[int]:
    if not price_text:
        return None
    lowered = price_text.lower()
    if "sur demande" in lowered:
        return None
    digits = re.sub(r"[^\d]", "", price_text)
    if not digits:
        return None
    return int(digits)


def fill_missing_prices(df: pd.DataFrame) -> pd.DataFrame:
    # Remplace les prix manquants par la moyenne des prix disponibles
    if "prix" not in df.columns or df.empty:
        return df
    cleaned = df.copy()
    prices = pd.to_numeric(cleaned["prix"], errors="coerce")
    mean_price = prices.dropna().mean()
    if pd.isna(mean_price):
        return cleaned
    cleaned["prix"] = prices.fillna(mean_price)
    return cleaned


def _extract_text(element, clean: bool) -> str:
    if not element:
        return ""
    text = element.get_text(" ", strip=True)
    return normalize_text(text) if clean else text


def parse_cards(html: str, clean: bool) -> List[Dict[str, Optional[str]]]:
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("div.card.ad__card")
    records: List[Dict[str, Optional[str]]] = []
    for card in cards:
        title_el = card.select_one(".ad__card-description a")
        price_el = card.select_one(".ad__card-price a")
        location_el = card.select_one(".ad__card-location span")
        image_el = card.select_one("img.ad__card-img")

        title = _extract_text(title_el, clean=clean)
        price_raw = _extract_text(price_el, clean=False)
        location = _extract_text(location_el, clean=clean)
        image = ""
        if image_el:
            image = image_el.get("src") or image_el.get("data-src") or ""

        records.append(
            {
                "titre": title,
                "prix": clean_price(price_raw) if clean else price_raw,
                "adresse": location,
                "image_lien": image,
            }
        )
    return records


def scrape_category(
    config: CategoryConfig,
    pages: Optional[int],
    clean: bool,
    delay_seconds: float = DEFAULT_REQUEST_DELAY_SECONDS,
    max_pages_limit: int = MAX_PAGES_LIMIT,
) -> List[Dict[str, Optional[str]]]:
    results: List[Dict[str, Optional[str]]] = []
    page = 1
    while True:
        if pages is not None and page > pages:
            break
        if pages is None and page > max_pages_limit:
            break
        url = build_page_url(config.url, page)
        html = fetch_html(url)
        page_records = parse_cards(html, clean=clean)
        if not page_records and page > 1:
            break
        for record in page_records:
            record["categorie"] = config.key
        results.extend(page_records)
        page += 1
        if delay_seconds:
            time.sleep(delay_seconds)
    return results


def scrape_categories(
    category_keys: Sequence[str],
    pages: Optional[int],
    clean: bool,
    delay_seconds: float = DEFAULT_REQUEST_DELAY_SECONDS,
    max_pages_limit: int = MAX_PAGES_LIMIT,
) -> pd.DataFrame:
    all_records: List[Dict[str, Optional[str]]] = []
    for key in category_keys:
        config = CATEGORIES[key]
        all_records.extend(
            scrape_category(
                config=config,
                pages=pages,
                clean=clean,
                delay_seconds=delay_seconds,
                max_pages_limit=max_pages_limit,
            )
        )
    dataframe = pd.DataFrame(all_records)
    if clean and not dataframe.empty:
        # Imputation des prix manquants apres nettoyage
        dataframe = fill_missing_prices(dataframe)
    return dataframe


def format_category_dataframe(df: pd.DataFrame, category_key: str) -> pd.DataFrame:
    config = CATEGORIES[category_key]
    subset = df[df["categorie"] == category_key].copy()
    if subset.empty:
        return subset
    subset = subset.rename(columns={"titre": config.field_name})
    ordered_cols = [config.field_name, "prix", "adresse", "image_lien"]
    return subset[ordered_cols]


def clean_webscraper_dataframe(raw_df: pd.DataFrame) -> pd.DataFrame:
    if raw_df.empty:
        return raw_df.copy()
    cleaned = raw_df.copy()
    cleaned["titre"] = cleaned["titre"].apply(normalize_text)
    cleaned["adresse"] = cleaned["adresse"].apply(normalize_text)
    cleaned["prix"] = cleaned["prix"].apply(clean_price)
    return fill_missing_prices(cleaned)
