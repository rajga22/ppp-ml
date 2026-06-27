# Modeling Cross-Country Price Disparities and Exchange Rate Dynamics: A Machine Learning Approach

**Author:** Ananya Rajgaria  
**Senior Honors Thesis**

## Overview

This project investigates why the same product costs different amounts in different countries — and whether machine learning can predict and explain those price gaps. Using real price data scraped from international fashion retailers (Zara and Mango) across the US and India, the project applies linear regression and other ML models to understand how exchange rates, materials, and product categories drive cross-country price disparities.

## Research Question

Can machine learning models effectively model and predict cross-country price differences, and what factors (exchange rates, materials, product category) matter most?

## Data Collection

- Web scraped product prices from **Zara** and **Mango** in the US and India
- Collected across multiple dates (March–April 2026) to capture time-series variation
- Retailers scraped: Zara, Mango, Gap, H&M, Etsy
- Data includes: product name, price (USD/INR), category, materials

## Methods

- **Web scraping** — custom Python scripts using Playwright/requests + Gemini API for material extraction
- **Linear regression** — modeling price gap as a function of exchange rate, category, materials
- **Time-series forecasting** — exchange rate dynamics over time
- **Comparative analysis** — US vs India pricing across product categories (women, men, kids)

## Repository Structure

```
ppp-ml/
├── notebooks/                          ← Colab analysis notebooks
│   ├── Mango zara compined regression colab/
│   ├── collab model/
│   └── ...
├── scripts/
│   ├── March6_Zara_code/               ← Main Zara scraping pipeline
│   ├── mango work final/               ← Mango scraping scripts
│   ├── Zara work*/                     ← Iterative Zara scraper versions
│   └── ...
├── data/                               ← Cleaned datasets (CSV/Excel)
├── results/                            ← Scraped comparison outputs by date
├── Honors_Thesis_Format.pdf            ← Full thesis paper
├── Ananya Honors Presentaion.pptx      ← Thesis presentation slides
└── README.md
```

## Key Files

| File | Description |
|------|-------------|
| `Honors_Thesis_Format.pdf` | Full written thesis |
| `March6_Zara_code/Zara_[Women].ipynb` | Main analysis notebook (women's pricing) |
| `Mango zara compined regression colab/mango_zara_price_regression_colab.ipynb` | Combined regression model |
| `March6_Zara_code/zara_IN_US.py` | Core Zara US vs India scraper |
| `Regression_Data.xlsx` | Main dataset used for modeling |

## How to Run

All notebooks are designed for **Google Colab**. To run:

1. Open [Google Colab](https://colab.research.google.com)
2. File → Upload notebook → select any `.ipynb` file
3. Upload the relevant data file when prompted
4. Run all cells

## Tech Stack

- Python (pandas, scikit-learn, matplotlib, seaborn)
- Google Colab
- Playwright / requests (web scraping)
- Google Gemini API (material extraction)
