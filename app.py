from __future__ import annotations

import io
from typing import Iterable, Optional, Sequence, Tuple

import pandas as pd
import streamlit as st

from scraper import (
    CATEGORIES,
    MAX_PAGES_LIMIT,
    clean_webscraper_dataframe,
    format_category_dataframe,
    scrape_categories,
)

DEFAULT_FORM_URL = "https://forms.gle/your-form-id"


def _format_price(value: Optional[float]) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "N/A"
    try:
        return f"{int(value):,}".replace(",", " ") + " CFA"
    except (TypeError, ValueError):
        return "N/A"


def _to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


@st.cache_data(show_spinner=False)
def _cached_scrape(
    category_keys: Tuple[str, ...],
    pages: Optional[int],
    clean: bool,
    delay_seconds: float,
    max_pages_limit: int,
) -> pd.DataFrame:
    return scrape_categories(
        category_keys=category_keys,
        pages=pages,
        clean=clean,
        delay_seconds=delay_seconds,
        max_pages_limit=max_pages_limit,
    )


def _category_label(key: str) -> str:
    return CATEGORIES[key].label


def main() -> None:
    st.set_page_config(page_title="CoinAfrique Scraper", layout="wide")
    st.title("CoinAfrique - Scraping animaux")
    st.caption(
        "Scraping multi-pages avec BeautifulSoup (nettoye) "
        "et pipeline Web Scraper (brut)."
    )

    with st.sidebar:
        st.header("Parametres")
        selected_categories = st.multiselect(
            "Categories",
            options=list(CATEGORIES.keys()),
            default=list(CATEGORIES.keys()),
            format_func=_category_label,
        )
        scrape_all_pages = st.checkbox(
            "Scraper toutes les pages (limite de securite)",
            value=False,
        )
        pages_input = st.number_input(
            "Nombre de pages",
            min_value=1,
            max_value=MAX_PAGES_LIMIT,
            value=2,
            step=1,
            disabled=scrape_all_pages,
        )
        delay_seconds = st.slider(
            "Delai entre requetes (secondes)",
            min_value=0.0,
            max_value=2.0,
            value=0.3,
            step=0.1,
        )
        form_url = st.text_input("Lien formulaire (Kobo/Google)", value=DEFAULT_FORM_URL)

    pages: Optional[int] = None if scrape_all_pages else int(pages_input)

    tabs = st.tabs(
        [
            "Scraping nettoye (BeautifulSoup)",
            "Donnees Web Scraper (brutes)",
            "Dashboard (donnees nettoyees)",
            "Evaluation",
        ]
    )

    with tabs[0]:
        st.subheader("Scraping et nettoyage via BeautifulSoup")
        st.write(
            "Extraction des champs: titre, prix, adresse, image_lien. "
            "Le champ titre correspond a Nom ou Details selon la categorie."
        )
        if not selected_categories:
            st.warning("Selectionnez au moins une categorie.")
        if st.button("Lancer le scraping nettoye"):
            if selected_categories:
                with st.spinner("Scraping en cours..."):
                    cleaned_df = _cached_scrape(
                        category_keys=tuple(selected_categories),
                        pages=pages,
                        clean=True,
                        delay_seconds=delay_seconds,
                        max_pages_limit=MAX_PAGES_LIMIT,
                    )
                st.session_state["bs4_clean_df"] = cleaned_df
        cleaned_df = st.session_state.get("bs4_clean_df")
        if isinstance(cleaned_df, pd.DataFrame) and not cleaned_df.empty:
            st.success(f"{len(cleaned_df)} annonces nettoyees.")
            for key in selected_categories:
                category_df = format_category_dataframe(cleaned_df, key)
                st.markdown(f"#### {CATEGORIES[key].label}")
                st.dataframe(category_df, use_container_width=True)
            st.download_button(
                "Telecharger CSV nettoye",
                data=_to_csv_bytes(cleaned_df),
                file_name="coinafrique_bs4_nettoye.csv",
                mime="text/csv",
            )
        elif isinstance(cleaned_df, pd.DataFrame):
            st.info("Aucune donnee trouvee pour cette selection.")

    with tabs[1]:
        st.subheader("Scraping brut via Web Scraper")
        st.write(
            "Extraction brute (sans nettoyage). "
            "Les prix restent tels que recuperes sur la page."
        )
        if not selected_categories:
            st.warning("Selectionnez au moins une categorie.")
        if st.button("Lancer Web Scraper (brut)"):
            if selected_categories:
                with st.spinner("Scraping brut en cours..."):
                    raw_df = _cached_scrape(
                        category_keys=tuple(selected_categories),
                        pages=pages,
                        clean=False,
                        delay_seconds=delay_seconds,
                        max_pages_limit=MAX_PAGES_LIMIT,
                    )
                st.session_state["webscraper_raw_df"] = raw_df
        raw_df = st.session_state.get("webscraper_raw_df")
        if isinstance(raw_df, pd.DataFrame) and not raw_df.empty:
            st.success(f"{len(raw_df)} annonces brutes.")
            st.dataframe(raw_df.head(50), use_container_width=True)
            st.download_button(
                "Telecharger CSV brut",
                data=_to_csv_bytes(raw_df),
                file_name="coinafrique_webscraper_brut.csv",
                mime="text/csv",
            )
        elif isinstance(raw_df, pd.DataFrame):
            st.info("Aucune donnee brute disponible.")

    with tabs[2]:
        st.subheader("Dashboard - donnees nettoyees issues du Web Scraper")
        raw_df = st.session_state.get("webscraper_raw_df")
        if not isinstance(raw_df, pd.DataFrame) or raw_df.empty:
            st.info(
                "Lancez d'abord le Web Scraper dans l'onglet precedent "
                "pour alimenter le dashboard."
            )
        else:
            cleaned_ws_df = clean_webscraper_dataframe(raw_df)
            total_ads = len(cleaned_ws_df)
            categories_count = cleaned_ws_df["categorie"].nunique()
            price_series = cleaned_ws_df["prix"].dropna()
            median_price = price_series.median() if not price_series.empty else None

            col1, col2, col3 = st.columns(3)
            col1.metric("Annonces", total_ads)
            col2.metric("Categories", categories_count)
            col3.metric("Prix median", _format_price(median_price))

            st.markdown("##### Nombre d'annonces par categorie")
            count_by_cat = cleaned_ws_df.groupby("categorie").size().sort_values()
            st.bar_chart(count_by_cat)

            st.markdown("##### Prix moyen par categorie (CFA)")
            avg_price_by_cat = (
                cleaned_ws_df.dropna(subset=["prix"])
                .groupby("categorie")["prix"]
                .mean()
                .sort_values()
            )
            if avg_price_by_cat.empty:
                st.info("Pas assez de prix numeriques pour le graphique.")
            else:
                st.bar_chart(avg_price_by_cat)

            st.markdown("##### Top annonces par prix")
            top_df = cleaned_ws_df.dropna(subset=["prix"]).sort_values(
                "prix", ascending=False
            )
            st.dataframe(top_df.head(50), use_container_width=True)

    with tabs[3]:
        st.subheader("Evaluation de l'application")
        st.write(
            "Merci de remplir le formulaire d'evaluation pour donner votre avis."
        )
        if form_url:
            st.markdown(f"[Ouvrir le formulaire]({form_url})")
        else:
            st.info("Ajoutez un lien Kobo ou Google Forms dans la barre laterale.")


if __name__ == "__main__":
    main()
