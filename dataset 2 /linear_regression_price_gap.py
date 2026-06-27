
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# 1) Load dataset
df = pd.read_csv("synthetic_zara_same_columns_600.csv")

# 2) Derive target from existing columns only
df["price_gap_pct"] = (df["US_price_current_usd"] - df["IN_price_current_usd"]) / df["IN_price_current_usd"]
df.replace([np.inf, -np.inf], np.nan, inplace=True)
df = df.dropna(subset=["price_gap_pct"])

# 3) Build features and target
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

# 4) Train/test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# 5) Fit model
model.fit(X_train, y_train)

# 6) Predict
pred = model.predict(X_test)

# 7) Evaluate
mae = mean_absolute_error(y_test, pred)
rmse = mean_squared_error(y_test, pred) ** 0.5
r2 = r2_score(y_test, pred)

print("Target: price_gap_pct")
print("MAE:", round(mae, 4))
print("RMSE:", round(rmse, 4))
print("R^2:", round(r2, 4))

# 8) Coefficients
feature_names = model.named_steps["preprocessor"].get_feature_names_out()
coefs = model.named_steps["regressor"].coef_

coef_df = pd.DataFrame({
    "feature": feature_names,
    "coefficient": coefs
}).sort_values("coefficient", ascending=False)

print("\nTop coefficients:")
print(coef_df.head(10))
