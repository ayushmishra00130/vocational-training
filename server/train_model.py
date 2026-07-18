import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
import pickle
from model import FEATURE_COLUMNS, CATEGORICAL_COLUMNS, NUMERIC_COLUMNS, CATEGORY_MAPS

# Load dataset
df = pd.read_csv("heart.csv")

# Some versions of this dataset use `thalch` instead of `thalach`.
if "thalch" in df.columns and "thalach" not in df.columns:
	df = df.rename(columns={"thalch": "thalach"})

missing = [col for col in FEATURE_COLUMNS if col not in df.columns]
if missing:
	raise ValueError(f"Missing required feature columns: {missing}")

# Determine target column (`target` or `num`) and normalize as binary.
if "target" in df.columns:
	y = df["target"]
elif "num" in df.columns:
	y = (df["num"] > 0).astype(int)
else:
	raise ValueError("No target column found. Expected 'target' or 'num'.")

X = df[FEATURE_COLUMNS].copy()

# Convert categorical text values to numeric codes expected by the API payload.
for col in CATEGORICAL_COLUMNS:
	mapping = CATEGORY_MAPS[col]
	X[col] = X[col].apply(lambda val: mapping.get(val, mapping.get(str(val).strip().lower(), -1)))
	X[col] = pd.to_numeric(X[col], errors="coerce").fillna(-1).astype(int)

# Ensure numeric columns are numeric even when source CSV contains placeholders.
for col in NUMERIC_COLUMNS:
	X[col] = pd.to_numeric(X[col], errors="coerce")
	X[col] = X[col].fillna(X[col].median())

preprocessor = ColumnTransformer(
	transformers=[
		(
			"cat",
			OneHotEncoder(handle_unknown="ignore"),
			CATEGORICAL_COLUMNS,
		),
		("num", "passthrough", NUMERIC_COLUMNS),
	]
)

model = Pipeline(
	steps=[
		("preprocessor", preprocessor),
		("classifier", RandomForestClassifier(random_state=42)),
	]
)

# Split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train model
model.fit(X_train, y_train)

# Save model
pickle.dump(model, open("model.pkl", "wb"))

print("Model trained and saved!")