
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

kids = pd.read_csv("../results/kids/Zara_Master_Dataset_Kids_March24_2026.csv")
kids["Segment"] = "Kids"

men = pd.read_csv("../results/men/Zara_Master_Dataset_Men_March22_2026.csv")
men["Segment"] = "Men"

women = pd.read_csv("../results/women/Zara_Master_Dataset_Women_March22_2026.csv")
women["Segment"] = "Women"

df = pd.concat([kids, men, women], ignore_index=True)
print("original length of df:", len(df))

df["price_gap_pct"] = (df["US_price_current_usd"] - df["IN_price_current_usd"]) / df["IN_price_current_usd"]
df = df.replace([np.inf, -np.inf], np.nan)
df = df.dropna(subset=["price_gap_pct"])

df.to_csv("combined_data.csv")

y = df["price_gap_pct"]
#X = df.drop(columns=["price_gap_pct", "Product_ID", "name", "date"])

# Drop the target, the IDs, the names, and ALL price info
price_columns = [col for col in df.columns if "price" in col.lower()]
X = df.drop(columns=[
    "price_gap_pct", 
    "Product_ID", 
    "name", 
    "date"
] + price_columns)

numeric_features = X.select_dtypes(include=[np.number, "bool"]).columns.tolist()
categorical_features = [c for c in X.columns if c not in numeric_features]

print("numerical features:", numeric_features)
print("categorical features:", categorical_features)

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


X.to_csv("X_preprocessed_data_train_test.csv")
y.to_csv("y_preprocessed_data_train_test.csv")

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

'''
print("X training:\n",X_train)
print("X test:\n", X_test)
print("y_train:\n", y_train)
print("y_test:\n", y_test)
'''

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


# Plots
'''
# Coefficients
feature_names = model.named_steps["preprocessor"].get_feature_names_out()
coefs = model.named_steps["regressor"].coef_
coef_df = pd.DataFrame({
"feature": feature_names,
"coefficient": coefs
})
coef_df["abs_coefficient"] = coef_df["coefficient"].abs()
coef_df = coef_df.sort_values("abs_coefficient", ascending=False)
coef_path = "combined_linear_regression_coefficients.csv"
coef_df.to_csv(coef_path, index=False)


# actual vs predicted
plt.figure(figsize=(7,5))
plt.scatter(y_test, pred, alpha=0.65)
lims = [min(y_test.min(), pred.min()), max(y_test.max(), pred.max())]
plt.plot(lims, lims)
plt.xlabel("Actual price_gap_pct")
plt.ylabel("Predicted price_gap_pct")
plt.title("Combined Dataset: Actual vs Predicted Price Gap %")
#plt.tight_layout()
plot1 = "combined_actual_vs_predicted.png"
plt.savefig(plot1, dpi=200)
plt.close()

# residuals
resid = y_test - pred
plt.figure(figsize=(7,5))
plt.hist(resid, bins=25)
plt.xlabel("Residual")
plt.ylabel("Count")
plt.title("Combined Dataset: Residual Distribution")
#plt.tight_layout()
plot2 = "combined_residual_distribution.png"
plt.savefig(plot2, dpi=200)
plt.close()

# top coefficients
top_coef = coef_df.head(20).sort_values("coefficient")
plt.figure(figsize=(10,15))
plt.barh(top_coef["feature"], top_coef["coefficient"])
plt.xlabel("Coefficient")
plt.title("Top Linear Regression Coefficients")
#plt.tight_layout()
plot3 = "combined_top_coefficients.png"
plt.savefig(plot3, dpi=200)
plt.close()

# segment comparison
plt.figure(figsize=(7,5))
for seg in df["Segment"].dropna().unique():
    plt.hist(df.loc[df["Segment"] == seg, "price_gap_pct"], bins=20, alpha=0.5, label=seg)
    plt.xlabel("price_gap_pct")
    plt.ylabel("Count")
    plt.title("Price Gap % Distribution by Segment")
    plt.legend()
    #plt.tight_layout()
    plot4 = "combined_segment_price_gap_distribution.png"
    plt.savefig(plot4, dpi=200)
    plt.close()
'''
