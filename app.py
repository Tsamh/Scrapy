from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import altair as alt
import pandas as pd
import streamlit as st

from scraper import (
    CATEGORIES,
    MAX_PAGES_LIMIT,
    clean_webscraper_dataframe,
    format_category_dataframe,
    scrape_categories,
)

# Valeurs par defaut pour les liens de formulaire
FORM_DEFAULTS = {
    "Kobo": "https://ee.kobotoolbox.org/x/qu2XMTMf",
    "Google Forms": "https://docs.google.com/forms/d/e/1FAIpQLScNZ_ftGzYCyrMieoRGxsj88IkbCmGg2Pv66Lrh13B02a3Hxw/viewform?usp=header",
}

# Images de fond pour les cartes de formulaire
FORM_CARD_IMAGES = {
    "Kobo": "https://images.unsplash.com/photo-1522202176988-66273c2fd55f?auto=format&fit=crop&w=900&q=60",
    "Google Forms": "https://images.unsplash.com/photo-1519389950473-47ba0277781c?auto=format&fit=crop&w=900&q=60",
}

# Images de fond pour les cartes de categories Web Scraper
CATEGORY_IMAGES = {
    "chiens": "https://images.unsplash.com/photo-1517849845537-4d257902454a?auto=format&fit=crop&w=900&q=60",
    "moutons": "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=900&q=60",
    "poules-lapins-et-pigeons": "https://images.unsplash.com/photo-1548550023-2bdb3c5beed7?auto=format&fit=crop&w=900&q=60",
    "autres-animaux": "https://images.unsplash.com/photo-1518791841217-8f162f1e1131?auto=format&fit=crop&w=900&q=60",
}

WEBSCRAPER_DATA_DIR = Path("data_webscraper")

# Palettes simples pour personnaliser le theme
THEMES = {
    "Ocean": {
        "primary": "#0ea5e9",
        "secondary": "#38bdf8",
        "accent": "#0f172a",
        "background": "#f0f9ff",
        "card": "#ffffff",
    },
    "Mango": {
        "primary": "#f97316",
        "secondary": "#fb923c",
        "accent": "#7c2d12",
        "background": "#fff7ed",
        "card": "#ffffff",
    },
    "Lavande": {
        "primary": "#8b5cf6",
        "secondary": "#a78bfa",
        "accent": "#312e81",
        "background": "#f5f3ff",
        "card": "#ffffff",
    },
}


def _format_price(value: Optional[float]) -> str:
    # Affiche un prix lisible ou "N/A" si absence de valeur
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "N/A"
    try:
        return f"{int(value):,}".replace(",", " ") + " CFA"
    except (TypeError, ValueError):
        return "N/A"


def _to_csv_bytes(df: pd.DataFrame) -> bytes:
    # Conversion du dataframe vers un CSV telechargeable
    return df.to_csv(index=False).encode("utf-8")


@st.cache_data(show_spinner=False)
def _cached_scrape(
    category_keys: Tuple[str, ...],
    pages: Optional[int],
    clean: bool,
    delay_seconds: float,
    max_pages_limit: int,
) -> pd.DataFrame:
    # Cache pour eviter de re-scraper inutilement
    return scrape_categories(
        category_keys=category_keys,
        pages=pages,
        clean=clean,
        delay_seconds=delay_seconds,
        max_pages_limit=max_pages_limit,
    )


def _category_label(key: str) -> str:
    # Libelle plus lisible dans la sidebar
    return CATEGORIES[key].label


def _altair_scheme(theme_key: str) -> str:
    # Palette Altair adaptee au theme selectionne
    return {
        "Ocean": "blues",
        "Mango": "oranges",
        "Lavande": "purples",
    }.get(theme_key, "tableau10")


def _webscraper_csv_path(category_key: str) -> Path:
    # Chemin attendu pour les CSV webscraper
    return WEBSCRAPER_DATA_DIR / f"{category_key}_coinafrique_webscraper_brut.csv"


def _category_from_filename(path: Path) -> Optional[str]:
    # Extrait la categorie a partir du nom de fichier
    suffix = "_coinafrique_webscraper_brut"
    if path.suffix != ".csv":
        return None
    stem = path.stem
    if stem.endswith(suffix):
        return stem[: -len(suffix)]
    return None


def _load_webscraper_csv(category_key: str) -> pd.DataFrame:
    # Charge un fichier CSV Web Scraper pour une categorie
    csv_path = _webscraper_csv_path(category_key)
    if not csv_path.exists():
        return pd.DataFrame()
    dataframe = pd.read_csv(csv_path)
    if "categorie" not in dataframe.columns:
        dataframe["categorie"] = category_key
    return dataframe


def _load_all_webscraper_data(category_keys: Tuple[str, ...]) -> pd.DataFrame:
    # Charge tous les CSV disponibles et les concatene
    frames = []
    for key in category_keys:
        category_df = _load_webscraper_csv(key)
        if not category_df.empty:
            frames.append(category_df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def _apply_theme(theme_key: str) -> None:
    # Injection CSS pour personnaliser les couleurs et animations
    palette = THEMES[theme_key]
    st.markdown(
        f"""
        <style>
        :root {{
            --primary: {palette["primary"]};
            --secondary: {palette["secondary"]};
            --accent: {palette["accent"]};
            --background: {palette["background"]};
            --card: {palette["card"]};
            --text: #0f172a;
            --text-muted: #475569;
        }}

        .stApp {{
            background: var(--background);
            color: var(--text);
        }}

        h1, h2, h3, h4, h5 {{
            color: var(--accent);
        }}

        /* Texte global lisible */
        p, span, label, li, div {{
            color: var(--text);
        }}

        .stMarkdown, .stText, .stCaption {{
            color: var(--text);
        }}

        /* Sidebar coloree selon le theme */
        [data-testid="stSidebar"] {{
            background: var(--primary);
        }}

        /* Texte blanc dans la sidebar pour contraste */
        [data-testid="stSidebar"] * {{
            color: #ffffff !important;
        }}

        /* Champs d'entree lisibles dans la sidebar */
        [data-testid="stSidebar"] input,
        [data-testid="stSidebar"] textarea,
        [data-testid="stSidebar"] select {{
            color: #0f172a !important;
            background: #ffffff !important;
            border-radius: 8px;
        }}

        /* Menu deroulant des categories (texte blanc) */
        [data-testid="stSidebar"] [data-baseweb="menu"] {{
            background: var(--primary) !important;
        }}

        [data-testid="stSidebar"] [data-baseweb="menu"] * {{
            color: #ffffff !important;
        }}

        [data-testid="stSidebar"] [role="option"][aria-selected="true"] {{
            background: var(--secondary) !important;
            color: #ffffff !important;
        }}

        /* Boutons plus attractifs avec une micro-animation */
        .stButton > button, .stDownloadButton > button {{
            background: var(--primary);
            color: #ffffff;
            border: none;
            border-radius: 8px;
            padding: 0.55rem 1rem;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}

        .stButton > button:hover, .stDownloadButton > button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 14px rgba(15, 23, 42, 0.18);
        }}

        /* Onglets */
        .stTabs [data-baseweb="tab"] {{
            font-weight: 600;
            color: var(--text-muted);
        }}

        .stTabs [data-baseweb="tab"][aria-selected="true"] {{
            color: #ffffff;
            background: var(--secondary);
            border-radius: 8px 8px 0 0;
            padding: 0.4rem 0.8rem;
        }}

        /* Cartes et tableaux */
        .stDataFrame, .stMetric {{
            background: var(--card);
            border-radius: 12px;
            box-shadow: 0 6px 16px rgba(15, 23, 42, 0.08);
        }}

        /* Couleur des categories dans les tags */
        div[data-baseweb="tag"] {{
            background: var(--secondary) !important;
            border: none !important;
        }}

        div[data-baseweb="tag"] span {{
            color: #ffffff !important;
        }}

        /* Barre d'actions des dataframes (icones visibles) */
        [data-testid="stDataFrame"] [data-testid="stToolbar"] {{
            background: var(--card);
            border-radius: 10px;
            padding: 4px;
        }}

        [data-testid="stDataFrame"] [data-testid="stToolbar"] button {{
            color: var(--accent) !important;
        }}

        [data-testid="stDataFrame"] [data-testid="stToolbar"] svg {{
            fill: var(--accent) !important;
        }}

        /* Fond clair pour les tableaux */
        [data-testid="stDataFrame"] div[role="grid"] {{
            background-color: #f1f5f9 !important;
            color: var(--text) !important;
        }}

        [data-testid="stDataFrame"] th, 
        [data-testid="stDataFrame"] td {{
            background-color: #f1f5f9 !important;
            color: var(--text) !important;
        }}

        /* Cartes des categories Web Scraper */
        section.main div[data-testid="stRadio"] > div {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin-top: 12px;
            margin-bottom: 16px;
        }}

        section.main div[data-testid="stRadio"] label {{
            height: 160px;
            border-radius: 16px;
            background-size: cover;
            background-position: center;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #ffffff !important;
            font-weight: 700;
            text-shadow: 0 2px 6px rgba(15, 23, 42, 0.6);
            position: relative;
            overflow: hidden;
            border: 2px solid transparent;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}

        section.main div[data-testid="stRadio"] label::before {{
            content: "";
            position: absolute;
            inset: 0;
            background: linear-gradient(135deg, rgba(15, 23, 42, 0.55), rgba(15, 23, 42, 0.2));
        }}

        section.main div[data-testid="stRadio"] label:hover {{
            transform: translateY(-4px);
            box-shadow: 0 12px 20px rgba(15, 23, 42, 0.18);
        }}

        section.main div[data-testid="stRadio"] label input {{
            display: none !important;
        }}

        section.main div[data-testid="stRadio"] label input:checked + div {{
            border: 2px solid var(--secondary);
            background: rgba(15, 23, 42, 0.35);
        }}

        section.main div[data-testid="stRadio"] label > div {{
            position: relative;
            z-index: 1;
            padding: 0 10px;
            text-align: center;
            font-size: 1.05rem;
        }}

        section.main div[data-testid="stRadio"] label:nth-of-type(1) {{
            background-image: url('{CATEGORY_IMAGES["chiens"]}');
        }}

        section.main div[data-testid="stRadio"] label:nth-of-type(2) {{
            background-image: url('{CATEGORY_IMAGES["moutons"]}');
        }}

        section.main div[data-testid="stRadio"] label:nth-of-type(3) {{
            background-image: url('{CATEGORY_IMAGES["poules-lapins-et-pigeons"]}');
        }}

        section.main div[data-testid="stRadio"] label:nth-of-type(4) {{
            background-image: url('{CATEGORY_IMAGES["autres-animaux"]}');
        }}

        /* Cartes de formulaire dans l'onglet evaluation */
        .form-card-container {{
            display: flex;
            justify-content: center;
            gap: 24px;
            flex-wrap: wrap;
            margin-top: 12px;
        }}

        .form-card {{
            width: 280px;
            height: 180px;
            border-radius: 16px;
            background-size: cover;
            background-position: center;
            position: relative;
            overflow: hidden;
            text-decoration: none;
            box-shadow: 0 10px 20px rgba(15, 23, 42, 0.18);
            transition: transform 0.25s ease, box-shadow 0.25s ease;
        }}

        .form-card::before {{
            content: "";
            position: absolute;
            inset: 0;
            background: linear-gradient(135deg, rgba(15, 23, 42, 0.55), rgba(15, 23, 42, 0.2));
        }}

        .form-card:hover {{
            transform: translateY(-6px) scale(1.02);
            box-shadow: 0 16px 28px rgba(15, 23, 42, 0.25);
        }}

        .form-card-overlay {{
            position: absolute;
            inset: 0;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 6px;
            color: #ffffff;
            text-align: center;
            z-index: 1;
        }}

        .form-card-title {{
            font-size: 1.1rem;
            font-weight: 700;
            color: #ffffff;
        }}

        .form-card-subtitle {{
            font-size: 0.9rem;
            color: #e2e8f0;
        }}

        /* Animation d'apparition douce */
        .stTabs [data-baseweb="tab-panel"] {{
            animation: fadeIn 0.4s ease-in-out;
        }}

        @keyframes fadeIn {{
            from {{
                opacity: 0;
                transform: translateY(6px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(page_title="CoinAfrique Scraper", layout="wide")
    # Titre principal
    st.title("CoinAfrique - Scraping animaux")
    st.caption(
        "Scraping multi-pages avec BeautifulSoup (nettoyée) "
        "et pipeline Web Scraper (brut)."
    )

    with st.sidebar:
        st.header("Parametres")
        # Choix du theme (texte blanc dans la sidebar)
        theme_key = st.radio(
            "Couleur du theme",
            options=list(THEMES.keys()),
            index=0,
            horizontal=True,
        )
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
        st.subheader("Formulaires d'evaluation")
        kobo_url = st.text_input(
            "Lien Kobo",
            value=FORM_DEFAULTS["Kobo"],
            key="kobo_url",
        )
        google_url = st.text_input(
            "Lien Google Forms",
            value=FORM_DEFAULTS["Google Forms"],
            key="google_url",
        )

    # Application du theme choisi
    _apply_theme(theme_key)

    pages: Optional[int] = None if scrape_all_pages else int(pages_input)

    tabs = st.tabs(
        [
            "Scraping nettoyé (BeautifulSoup)",
            "Données Web Scraper (brutes)",
            "Dashboard (données nettoyées)",
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
        if st.button("Lancer le scraping nettoyé"):
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
            st.success(f"{len(cleaned_df)} annonces nettoyées.")
            for key in selected_categories:
                category_df = format_category_dataframe(cleaned_df, key)
                st.markdown(f"#### {CATEGORIES[key].label}")
                st.dataframe(category_df, use_container_width=True)
            st.download_button(
                "Télécharger CSV nettoyé",
                data=_to_csv_bytes(cleaned_df),
                file_name="scrapy_donnees_nettoyees_coinafrique.csv",
                mime="text/csv",
            )
        elif isinstance(cleaned_df, pd.DataFrame):
            st.info("Aucune donnee trouvee pour cette selection.")

    with tabs[1]:
        st.subheader("Donnees Web Scraper (brutes)")
        st.write(
            "Selectionnez une categorie pour afficher les donnees brutes "
            "provenant des fichiers CSV."
        )
        category_order = tuple(CATEGORIES.keys())
        available_files = sorted(WEBSCRAPER_DATA_DIR.glob("*.csv"))
        if not available_files:
            st.warning(
                "Aucun fichier CSV trouve dans data_webscraper/. "
                "Ajoutez vos fichiers pour activer l'affichage."
            )
        # Selection par cartes (radio stylise)
        if "web_category" not in st.session_state:
            st.session_state["web_category"] = category_order[0]
        if st.session_state["web_category"] not in category_order:
            st.session_state["web_category"] = category_order[0]
        selected_web_category = st.radio(
            "Categorie Web Scraper",
            options=category_order,
            index=category_order.index(st.session_state["web_category"]),
            format_func=_category_label,
            key="web_category",
            label_visibility="collapsed",
        )
        st.caption(f"Categorie selectionnee : {CATEGORIES[selected_web_category].label}")

        selected_path = _webscraper_csv_path(selected_web_category)
        if not selected_path.exists():
            st.warning(
                "Aucune donnee trouvee. Ajoutez un fichier CSV dans "
                f"{selected_path}."
            )
        else:
            webscraper_df = pd.read_csv(selected_path)
            if "categorie" not in webscraper_df.columns:
                webscraper_df["categorie"] = selected_web_category
            if webscraper_df.empty:
                st.warning("Le fichier selectionne est vide.")
            else:
                st.success(f"{len(webscraper_df)} annonces brutes.")
                st.dataframe(webscraper_df, use_container_width=True)
                st.download_button(
                    "Telecharger CSV brut",
                    data=_to_csv_bytes(webscraper_df),
                    file_name=selected_path.name,
                    mime="text/csv",
                )

    with tabs[2]:
        st.subheader("Dashboard - donnees nettoyees issues du Web Scraper")
        raw_df = _load_all_webscraper_data(tuple(CATEGORIES.keys()))
        if raw_df.empty:
            st.info(
                "Ajoutez des fichiers CSV dans le dossier data_webscraper "
                "pour alimenter le dashboard."
            )
        else:
            # Nettoyage des donnees brutes pour le dashboard
            cleaned_ws_df = clean_webscraper_dataframe(raw_df)
            total_ads = len(cleaned_ws_df)
            categories_count = cleaned_ws_df["categorie"].nunique()
            price_series = cleaned_ws_df["prix"].dropna()
            median_price = price_series.median() if not price_series.empty else None
            scheme = _altair_scheme(theme_key)

            col1, col2, col3 = st.columns(3)
            col1.metric("Annonces", total_ads)
            col2.metric("Categories", categories_count)
            col3.metric("Prix median", _format_price(median_price))

            st.markdown("##### Nombre d'annonces par categorie (barres)")
            count_by_cat = (
                cleaned_ws_df.groupby("categorie")
                .size()
                .reset_index(name="count")
                .sort_values("count")
            )
            bar_chart = (
                alt.Chart(count_by_cat)
                .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
                .encode(
                    x=alt.X("categorie:N", title="Categorie", sort="-y"),
                    y=alt.Y("count:Q", title="Nombre d'annonces"),
                    color=alt.Color("categorie:N", scale=alt.Scale(scheme=scheme)),
                    tooltip=["categorie", "count"],
                )
            )
            st.altair_chart(bar_chart, use_container_width=True)

            st.markdown("##### Repartition des annonces (diagramme circulaire)")
            pie_chart = (
                alt.Chart(count_by_cat)
                .mark_arc(innerRadius=40)
                .encode(
                    theta=alt.Theta(field="count", type="quantitative"),
                    color=alt.Color(
                        field="categorie",
                        type="nominal",
                        scale=alt.Scale(scheme=scheme),
                    ),
                    tooltip=["categorie", "count"],
                )
            )
            st.altair_chart(pie_chart, use_container_width=True)

            st.markdown("##### Prix moyen par categorie (courbe)")
            avg_price_by_cat = (
                cleaned_ws_df.dropna(subset=["prix"])
                .groupby("categorie")["prix"]
                .mean()
                .reset_index()
            )
            if avg_price_by_cat.empty:
                st.info("Pas assez de prix numeriques pour le graphique.")
            else:
                line_chart = (
                    alt.Chart(avg_price_by_cat)
                    .mark_line(point=True)
                    .encode(
                        x=alt.X("categorie:N", title="Categorie"),
                        y=alt.Y("prix:Q", title="Prix moyen (CFA)"),
                        color=alt.value(THEMES[theme_key]["primary"]),
                        tooltip=["categorie", alt.Tooltip("prix:Q", format=",.0f")],
                    )
                )
                st.altair_chart(line_chart, use_container_width=True)

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
        # Cartes cliquables pour choisir le formulaire
        kobo_link = kobo_url or FORM_DEFAULTS["Kobo"]
        google_link = google_url or FORM_DEFAULTS["Google Forms"]
        kobo_image = FORM_CARD_IMAGES["Kobo"]
        google_image = FORM_CARD_IMAGES["Google Forms"]
        st.markdown(
            f"""
            <div class="form-card-container">
                <a class="form-card" href="{kobo_link}" target="_blank" style="background-image:url('{kobo_image}')">
                    <div class="form-card-overlay">
                        <div class="form-card-title">Kobo Form</div>
                        <div class="form-card-subtitle">Ouvrir le formulaire</div>
                    </div>
                </a>
                <a class="form-card" href="{google_link}" target="_blank" style="background-image:url('{google_image}')">
                    <div class="form-card-overlay">
                        <div class="form-card-title">Google Forms</div>
                        <div class="form-card-subtitle">Ouvrir le formulaire</div>
                    </div>
                </a>
            </div>
            """,
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    main()
