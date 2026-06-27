
COMBINED ZARA LINEAR REGRESSION PROJECT

What I did
I combined the three uploaded datasets:
- Zara_Master_Dataset_Kids_2026.csv
- Zara_Master_Dataset_Men_2026.csv
- Zara_Master_Dataset_Women_2026 (1).csv

I added one identifying column called Segment so the combined data preserves whether a row came from Kids, Men, or Women.

Target used
The target is derived from existing columns only:

    price_gap_pct = (US_price_current_usd - IN_price_current_usd) / IN_price_current_usd

This measures how much higher or lower the US price is relative to the India price in percentage terms.

Model used
- Linear Regression
- Missing numeric values filled with median
- Missing categorical values filled with most frequent value
- Categorical columns one-hot encoded
- Product_ID, name, and date removed from modeling features

Combined dataset info
Total combined rows before dropping missing target rows: 593
Rows used for modeling: 466

Results
MAE: 0.1502
RMSE: 0.2979
R²: 0.6400

How to explain it
The model predicts the percentage difference between the US and India prices after combining products from men, women, and kids.
This lets you study overall international pricing patterns while also keeping track of segment differences.
