import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import zipfile
import textwrap

base = Path("/mnt/data")

# File paths
files = {
"Kids": base / "Zara_Master_Dataset_Kids_2026.csv",
"Men": base / "Zara_Master_Dataset_Men_2026.csv",
"Women": base / "Zara_Master_Dataset_Women_2026 (1).csv",
}

dfs = []
for label, path in files.items():
df = pd.read_csv(path)
df["Segment"] = label
dfs.append(df)

combined = pd.concat(dfs, ignore_index=True)

# Save combined raw dataset
combined_raw_path = base / "zara_combined_men_women_kids.csv"
combined.to_csv(combined_raw_path, index=False)

# Derive target from existing columns only
model_df = combined.copy()
model_df["price_gap_pct"] = (model_df["US_price_current_usd"] - model_df["IN_price_current_usd"]) / model_df["IN_price_current_usd"]
model_df = model_df.replace([np.inf, -np.inf], np.nan)
model_df = model_df.dropna(subset=["price_gap_pct"])

# Features/target
target = "price_gap_pct"
drop_cols = [target, "Product_ID", "name", "date"] # remove ID/free-text/date leakage
X = model_df.drop(columns=[c for c in drop_cols if c in model_df.columns])
y = model_df[target]

numeric_features = X.select_dtypes(include=[np.number, "bool"]).columns.tolist()
categorical_features = [c for c in X.columns if c not in numeric_features]

numeric_transformer = Pipeline(steps=[
("imputer", SimpleImputer(strategy="median"))
])

categorical_transformer = Pipeline(steps=[
("imputer", SimpleImputer(strategy="most_frequent")),
("onehot", OneHotEncoder(handle_unknown="ignore"))
])

preprocessor = ColumnTransformer(
transformers=[
("num", numeric_transformer, numeric_features),
("cat", categorical_transformer, categorical_features)
]
)

model = Pipeline(steps=[
("preprocessor", preprocessor),
("regressor", LinearRegression())
])

X_train, X_test, y_train, y_test = train_test_split(
X, y, test_size=0.2, random_state=42
)

model.fit(X_train, y_train)
pred = model.predict(X_test)

mae = mean_absolute_error(y_test, pred)
rmse = mean_squared_error(y_test, pred) ** 0.5
r2 = r2_score(y_test, pred)

metrics = pd.DataFrame([{
"dataset": "combined_men_women_kids",
"target": "price_gap_pct",
"rows_used": len(model_df),
"MAE": mae,
"RMSE": rmse,
"R2": r2
}])
metrics_path = base / "combined_linear_regression_metrics.csv"
metrics.to_csv(metrics_path, index=False)

# Coefficients
feature_names = model.named_steps["preprocessor"].get_feature_names_out()
coefs = model.named_steps["regressor"].coef_
coef_df = pd.DataFrame({
"feature": feature_names,
"coefficient": coefs
})
coef_df["abs_coefficient"] = coef_df["coefficient"].abs()
coef_df = coef_df.sort_values("abs_coefficient", ascending=False)
coef_path = base / "combined_linear_regression_coefficients.csv"
coef_df.to_csv(coef_path, index=False)

# Plots
# actual vs predicted
plt.figure(figsize=(7,5))
plt.scatter(y_test, pred, alpha=0.65)
lims = [min(y_test.min(), pred.min()), max(y_test.max(), pred.max())]
plt.plot(lims, lims)
plt.xlabel("Actual price_gap_pct")
plt.ylabel("Predicted price_gap_pct")
plt.title("Combined Dataset: Actual vs Predicted Price Gap %")
plt.tight_layout()
plot1 = base / "combined_actual_vs_predicted.png"
plt.savefig(plot1, dpi=200)
plt.close()

# residuals
resid = y_test - pred
plt.figure(figsize=(7,5))
plt.hist(resid, bins=25)
plt.xlabel("Residual")
plt.ylabel("Count")
plt.title("Combined Dataset: Residual Distribution")
plt.tight_layout()
plot2 = base / "combined_residual_distribution.png"
plt.savefig(plot2, dpi=200)
plt.close()

# top coefficients
top_coef = coef_df.head(20).sort_values("coefficient")
plt.figure(figsize=(9,7))
plt.barh(top_coef["feature"], top_coef["coefficient"])
plt.xlabel("Coefficient")
plt.title("Top Linear Regression Coefficients")
plt.tight_layout()
plot3 = base / "combined_top_coefficients.png"
plt.savefig(plot3, dpi=200)
plt.close()

# segment comparison
plt.figure(figsize=(7,5))
for seg in model_df["Segment"].dropna().unique():
plt.hist(model_df.loc[model_df["Segment"] == seg, "price_gap_pct"], bins=20, alpha=0.5, label=seg)
plt.xlabel("price_gap_pct")
plt.ylabel("Count")
plt.title("Price Gap % Distribution by Segment")
plt.legend()
plt.tight_layout()
plot4 = base / "combined_segment_price_gap_distribution.png"
plt.savefig(plot4, dpi=200)
plt.close()

# segment summary
segment_summary = model_df.groupby("Segment").agg(
rows=("Segment", "size"),
mean_us_price=("US_price_current_usd", "mean"),
mean_in_price_usd=("IN_price_current_usd", "mean"),
mean_price_gap_pct=("price_gap_pct", "mean"),
).reset_index()
segment_summary_path = base / "combined_segment_summary.csv"
segment_summary.to_csv(segment_summary_path, index=False)

# Python script
script = f"""
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Load and combine datasets
kids = pd.read_csv("Zara_Master_Dataset_Kids_2026.csv")
kids["Segment"] = "Kids"

men = pd.read_csv("Zara_Master_Dataset_Men_2026.csv")
men["Segment"] = "Men"

women = pd.read_csv("Zara_Master_Dataset_Women_2026 (1).csv")
women["Segment"] = "Women"

df = pd.concat([kids, men, women], ignore_index=True)

# Derive target from existing columns only
df["price_gap_pct"] = (df["US_price_current_usd"] - df["IN_price_current_usd"]) / df["IN_price_current_usd"]
df = df.replace([np.inf, -np.inf], np.nan)
df = df.dropna(subset=["price_gap_pct"])

# Build X and y
y = df["price_gap_pct"]
X = df.drop(columns=["price_gap_pct", "Product_ID", "name", "date"])

numeric_features = X.select_dtypes(include=[np.number, "bool"]).columns.tolist()
categorical_features = [c for c in X.columns if c not in numeric_features]

numeric_transformer = Pipeline(steps=[
("imputer", SimpleImputer(strategy="median"))
])

categorical_transformer = Pipeline(steps=[
("imputer", SimpleImputer(strategy="most_frequent")),
("onehot", OneHotEncoder(handle_unknown="ignore"))
])

preprocessor = ColumnTransformer(
transformers=[
("num", numeric_transformer, numeric_features),
("cat", categorical_transformer, categorical_features)
]
)

model = Pipeline(steps=[
("preprocessor", preprocessor),
("regressor", LinearRegression())
])

X_train, X_test, y_train, y_test = train_test_split(
X, y, test_size=0.2, random_state=42
)

model.fit(X_train, y_train)
pred = model.predict(X_test)

mae = mean_absolute_error(y_test, pred)
rmse = mean_squared_error(y_test, pred) ** 0.5
r2 = r2_score(y_test, pred)

print("Rows used:", len(df))
print("Target: price_gap_pct")
print("MAE:", round(mae, 4))
print("RMSE:", round(rmse, 4))
print("R^2:", round(r2, 4))
"""
script_path = base / "combined_linear_regression_price_gap.py"
script_path.write_text(textwrap.dedent(script))

# README
readme = f"""
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

Why this target works
Your proposal is about cross-country pricing disparities.
This target directly matches that idea better than predicting one raw price column by itself.

Model used
- Linear Regression
- Missing numeric values: filled with median
- Missing categorical values: filled with most frequent value
- Categorical columns: one-hot encoded
- Product_ID, name, and date removed from modeling features

Combined dataset info
Total combined rows before dropping missing target rows: {len(combined)}
Rows used for modeling: {len(model_df)}

Results
MAE: {mae:.4f}
RMSE: {rmse:.4f}
R²: {r2:.4f}

Files
- zara_combined_men_women_kids.csv
- combined_linear_regression_price_gap.py
- combined_linear_regression_metrics.csv
- combined_linear_regression_coefficients.csv
- combined_segment_summary.csv
- combined_actual_vs_predicted.png
- combined_residual_distribution.png
- combined_top_coefficients.png
- combined_segment_price_gap_distribution.png

How to explain it simply
The model predicts the percentage difference between the US and India prices after combining products from men, women, and kids.
That lets you study overall international pricing patterns while also keeping track of segment differences.

"""
readme_path = base / "README_combined_zara_linear_regression.txt"
readme_path.write_text(textwrap.dedent(readme))

# Zip everything
zip_path = base / "combined_zara_linear_regression_project.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
for p in [
combined_raw_path, script_path, metrics_path, coef_path, segment_summary_path,
plot1, plot2, plot3, plot4, readme_path
]:
z.write(p, arcname=p.name)

print("Created files:")
for p in [combined_raw_path, script_path, metrics_path, coef_path, segment_summary_path, plot1, plot2, plot3, plot4, readme_path, zip_path]:
print(p.name)

print("\nSegment summary:")
print(segment_summary)

print("\nMetrics:")
print(metrics)
