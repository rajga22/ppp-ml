
PRICE GAP LINEAR REGRESSION PROJECT

What this version does
This project keeps the synthetic CSV in the exact same 20-column format as the original Zara file.
It does not add any columns to the dataset itself.

Instead, the modeling code derives a target from existing columns only:

    price_gap_pct = (US_price_current_usd - IN_price_current_usd) / IN_price_current_usd

Why this target is better
Your proposal is about cross-country pricing disparities.
That means it is more aligned to predict the relative gap between the US price and India price than to predict one raw price by itself.

Files included
1. synthetic_zara_same_columns_600.csv
   A 600-row synthetic dataset with the same columns as the original file.

2. linear_regression_price_gap.py
   Python code for the regression model.

3. linear_regression_price_gap_metrics.csv
   Model evaluation results.

4. linear_regression_price_gap_coefficients.csv
   Coefficients from the fitted model.

5. PNG charts
   - actual_vs_predicted_price_gap.png
   - residual_distribution_price_gap.png
   - top_coefficients_price_gap.png
   - price_gap_pct_distribution.png

How the model works
1. Load the synthetic CSV
2. Derive price_gap_pct from US and India current prices
3. Remove Product_ID, name, and date from features
4. One-hot encode categorical columns
5. Impute missing values
6. Train a linear regression model
7. Evaluate with MAE, RMSE, and R²

Current model results
MAE: 0.1701
RMSE: 0.2645
R²: 0.5743

How to explain this simply
The model predicts how much higher or lower the US price is relative to the India price, as a percentage of the India price.
That makes it a direct measure of cross-country price disparity.

Suggested framing for class or thesis
We used linear regression to predict the percentage price gap between US and India Zara product prices using existing product, discount, market, and sourcing variables.
This better matches the research question than predicting raw price alone.

