
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

kids = pd.read_csv("Zara_Master_Dataset_Kids_2026.csv")
kids["Segment"] = "Kids"

men = pd.read_csv("Zara_Master_Dataset_Men_2026.csv")
men["Segment"] = "Men"

women = pd.read_csv("Zara_Master_Dataset_Women_2026 (1).csv")
women["Segment"] = "Women"

df = pd.concat([kids, men, women], ignore_index=True)

df["price_gap_pct"] = (df["US_price_current_usd"] - df["IN_price_current_usd"]) / df["IN_price_current_usd"]
df = df.replace([np.inf, -np.inf], np.nan)
df = df.dropna(subset=["price_gap_pct"])

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
