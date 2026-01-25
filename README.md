# CoinAfrique Scraping App

Streamlit app to scrape CoinAfrique animal listings and explore results.

## Features

- Scrape and clean data from multiple pages with BeautifulSoup:
  - chiens (Nom, prix, adresse, image_lien)
  - moutons (Nom, prix, adresse, image_lien)
  - poules-lapins-et-pigeons (Details, prix, adresse, image_lien)
  - autres-animaux (Nom, prix, adresse, image_lien)
- Scrape raw (non-cleaned) data with a "Web Scraper" pipeline.
- Download raw data (CSV).
- Dashboard on cleaned data coming from Web Scraper.
- Link to an evaluation form (Kobo or Google Forms).

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

## How it works

- Select categories and number of pages in the sidebar.
- "Scraper toutes les pages" keeps fetching until no more results
  (with a safety limit).
- Tab 1: cleaned data via BeautifulSoup.
- Tab 2: raw data (no cleaning) via Web Scraper.
- Tab 3: dashboard using cleaned Web Scraper data.
- Tab 4: evaluation form link (set in the sidebar).

## Notes

- The CSV uses the column `titre` for the listing title. It corresponds
  to Nom or Details depending on the category.
- Price cleaning removes non-digits and keeps `None` for "Prix sur demande".