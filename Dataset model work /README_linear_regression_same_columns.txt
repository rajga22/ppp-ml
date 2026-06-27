PROJECT SUMMARY

You asked for:
1. The exact same columns as your original CSV
2. More made-up data to expand the dataset
3. Only linear regression
4. No new columns added

What I did:
- Kept the exact same 20 columns from your uploaded Zara dataset
- Expanded the file to 600 total rows
- Preserved logical relationships between fields such as:
  - US_price_current_usd and US_price_original_usd
  - India INR price and India USD price using exchange_rate
  - discount fields and on-sale status
  - source file, product name, color, material, and country-of-origin patterns
- Did NOT add any new columns

Important limitation:
Because the original dataset is a snapshot and does not contain repeated time periods for the same item,
a true 'price change over time' model is not possible without inventing time-based target columns.
To respect your instruction, I used only the original columns and built a linear regression model to predict:

US_price_current_usd

Model performance on the synthetic dataset:
- MAE: 9.087
- RMSE: 13.860
- R2: 0.899

How to explain the model simply:
- Linear regression tries to predict a number
- Here, the number is the current US price
- The model uses the existing price, discount, India pricing, exchange rate, sale flags, materials, and category text patterns
- It learns a line of best fit across all those features

Main files:
- synthetic_zara_same_columns_600.csv
- linear_regression_zara_same_columns.py
- linear_regression_metrics.csv
- linear_regression_coefficients.csv

Graphs included:
- actual_vs_predicted_linear.png
- residual_distribution_linear.png
- top_linear_coefficients.png
- us_price_distribution_synthetic.png
