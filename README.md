# Modeling Cross-Country Price Disparities and Exchange Rate Dynamics: A Machine Learning Approach

**Author:** Ananya Rajgaria  
**Senior Honors Thesis**

## Thesis

[Read the full thesis here](https://docs.google.com/document/d/1ymwtbleioRYGD-MJTKkpP36eh14n0pUrk6-UGrYZ-gQ/edit?usp=sharing)

## Overview

This project investigates why the same product costs different amounts across countries, and whether machine learning can predict and explain those price gaps. Using real price data scraped from international fashion retailers (Zara and Mango) across the US and India, the project applies linear regression and other ML models to understand how exchange rates, materials, and product categories drive cross-country price disparities.

## Repository Structure

```
ppp-ml/
├── thesis/
│   ├── honors_thesis.pdf           ← Full written thesis (see link below)
│   └── presentation.pptx           ← Defense presentation slides
│
├── notebooks/                      ← Google Colab analysis notebooks
│   ├── zara_women_price_analysis.ipynb
│   ├── zara_men_price_analysis.ipynb
│   ├── zara_kids_price_analysis.ipynb
│   ├── mango_zara_price_regression.ipynb
│   ├── materials_country_linear_regression.ipynb
│   ├── materials_country_comparison.ipynb
│   ├── ml_pipeline_price_prediction.ipynb
│   ├── ols_regression_price_model.ipynb
│   ├── web_scraping_exploration.ipynb
│   └── selenium_scraping_setup.ipynb
│
├── scripts/
│   ├── scraping/                   ← Web scrapers for each retailer
│   │   ├── zara_scraper_us_india.py
│   │   ├── zara_scraper_us.py
│   │   ├── zara_scraper_india.py
│   │   ├── zara_url_finder.py
│   │   ├── zara_url_finder_women.py
│   │   ├── mango_scraper_us.py
│   │   ├── mango_scraper_india.py
│   │   ├── mango_url_finder.py
│   │   ├── gap_scraper.py
│   │   └── hm_scraper.py
│   └── analysis/
│       ├── linear_regression_price_gap.py
│       └── combine_csv.py
│
├── data/
│   ├── regression_dataset.xlsx         ← Main dataset used for modeling
│   ├── zara_mango_combined.csv         ← Combined Zara + Mango price data
│   ├── zara_mango_materials.csv        ← Material composition by product
│   ├── zara_combined_model_data.csv    ← Preprocessed data for ML models
│   ├── mango_us_prices.csv             ← Mango US scraped prices
│   ├── mango_india_prices.csv          ← Mango India scraped prices
│   ├── exchange_rate_forecast.csv      ← USD/INR exchange rate forecast
│   ├── exchange_rate_timeseries.csv    ← Exchange rate time series data
│   └── urls/                           ← Product URLs used for scraping
│       ├── women/
│       ├── men/
│       └── kids/
│
└── results/
    ├── zara_women_master_dataset.csv   ← Final aggregated women's data
    ├── zara_men_master_dataset.csv     ← Final aggregated men's data
    ├── zara_kids_master_dataset.csv    ← Final aggregated kids' data
    ├── zara_women_transformed.csv      ← Transformed women's data for modeling
    ├── zara_men_transformed.csv        ← Transformed men's data for modeling
    └── zara_kids_transformed.csv       ← Transformed kids' data for modeling
```

## Methods

- **Web scraping** — Python scripts using Playwright + Gemini API for material extraction
- **Linear regression** — modeling price gap as a function of exchange rate, category, materials
- **OLS regression** — statsmodels with clustered standard errors
- **ML pipeline** — scikit-learn with preprocessing, train/test split, and cross-validation
- **Time-series forecasting** — exchange rate dynamics over time

## How to Run Notebooks

All notebooks are designed for **Google Colab**:

1. Open [colab.research.google.com](https://colab.research.google.com)
2. File → Upload notebook → select any `.ipynb` from `notebooks/`
3. Upload the relevant data file from `data/` when prompted
4. Run all cells

## Tech Stack

- Python (pandas, numpy, scikit-learn, statsmodels, matplotlib, seaborn)
- Google Colab
- Playwright / Selenium (web scraping)
- Google Gemini API (material extraction)
