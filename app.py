from flask import Flask, render_template, request, jsonify
import pickle
import numpy as np
import json
from pathlib import Path

app = Flask(__name__)

# ─── Load model artifact ───────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "artifacts" / "heart_disease_model.pkl"

with open(MODEL_PATH, "rb") as f:
    artifact = pickle.load(f)

model        = artifact["model"]
scaler       = artifact["scaler"]
feature_names = artifact["feature_names"]
model_name   = artifact.get("model_name", "Gradient Boosting")

# ─── Feature metadata ──────────────────────────────────────────────────────────
FEATURE_LABELS = {
    "age":      "Age (years)",
    "sex":      "Sex",
    "cp":       "Chest Pain Type",
    "trestbps": "Resting Blood Pressure (mm Hg)",
    "chol":     "Serum Cholesterol (mg/dl)",
    "fbs":      "Fasting Blood Sugar > 120 mg/dl",
    "restecg":  "Resting ECG Result",
    "thalach":  "Maximum Heart Rate",
    "exang":    "Exercise-Induced Angina",
    "oldpeak":  "ST Depression (oldpeak)",
    "slope":    "ST Segment Slope",
    "ca":       "Major Vessels (0-3)",
    "thal":     "Thalassemia",
}

SELECT_OPTIONS = {
    "sex":     [(1, "Male"), (0, "Female")],
    "cp":      [(0, "Typical Angina"), (1, "Atypical Angina"),
                (2, "Non-Anginal Pain"), (3, "Asymptomatic")],
    "fbs":     [(1, "Yes (> 120 mg/dl)"), (0, "No")],
    "restecg": [(0, "Normal"), (1, "ST-T Wave Abnormality"),
                (2, "Left Ventricular Hypertrophy")],
    "exang":   [(1, "Yes"), (0, "No")],
    "slope":   [(0, "Upsloping"), (1, "Flat"), (2, "Downsloping")],
    "ca":      [(0, "0"), (1, "1"), (2, "2"), (3, "3")],
    "thal":    [(1, "Normal"), (2, "Fixed Defect"), (3, "Reversible Defect")],
}

# Dataset means (Cleveland Heart Disease – standard reference values)
FEATURE_MEANS = {
    "age": 54.4, "sex": 0.68, "cp": 0.97, "trestbps": 131.6,
    "chol": 246.3, "fbs": 0.15, "restecg": 0.53, "thalach": 149.6,
    "exang": 0.33, "oldpeak": 1.04, "slope": 1.40, "ca": 0.73, "thal": 2.31,
}

# Thresholds that indicate elevated risk (used for risk_reasons)
RISK_THRESHOLDS = {
    "age":      (">=", 60,  "Age ≥ 60 increases cardiac risk"),
    "trestbps": (">=", 140, "Resting BP ≥ 140 mm Hg (hypertensive range)"),
    "chol":     (">=", 240, "Cholesterol ≥ 240 mg/dl (high range)"),
    "thalach":  ("<=", 120, "Max heart rate ≤ 120 bpm (low for age)"),
    "oldpeak":  (">=", 2.0, "ST depression ≥ 2.0 (significant ischaemia sign)"),
    "ca":       (">=", 1,   "≥ 1 major vessel blocked"),
    "exang":    ("==", 1,   "Exercise-induced angina present"),
    "fbs":      ("==", 1,   "Fasting blood sugar > 120 mg/dl (diabetic range)"),
    "cp":       ("==", 3,   "Asymptomatic chest pain (silent ischaemia risk)"),
    "thal":     ("==", 3,   "Reversible thalassemia defect detected"),
}

# ─── Helpers ───────────────────────────────────────────────────────────────────

def prepare_input(form):
    values = []
    for feat in feature_names:
        val = form.get(feat)
        if val is None or val == "":
            raise ValueError(f"Missing value for '{feat}'")
        values.append(float(val))
    arr = np.array(values).reshape(1, -1)
    return scaler.transform(arr), values   # scaled for model; raw for analysis


def get_risk_reasons(raw_values):
    reasons = []
    for i, feat in enumerate(feature_names):
        if feat not in RISK_THRESHOLDS:
            continue
        op, threshold, msg = RISK_THRESHOLDS[feat]
        v = raw_values[i]
        if   op == ">=" and v >= threshold:  reasons.append(msg)
        elif op == "<=" and v <= threshold:  reasons.append(msg)
        elif op == "==" and v == threshold:  reasons.append(msg)
    return reasons


def build_chart_data(raw_values):
    """Only show the most interpretable continuous features in the bar chart."""
    chart_features = ["age", "trestbps", "chol", "thalach", "oldpeak", "ca"]
    labels, user_vals, mean_vals = [], [], []
    for feat in chart_features:
        if feat in feature_names:
            idx = feature_names.index(feat)
            labels.append(FEATURE_LABELS.get(feat, feat))
            user_vals.append(raw_values[idx])
            mean_vals.append(FEATURE_MEANS.get(feat, 0))
    return {"labels": labels, "user_values": user_vals, "mean_values": mean_vals}


def get_risk_level(prob):
    if prob < 0.30: return "Low"
    if prob < 0.60: return "Medium"
    return "High"


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template(
        "index.html",
        feature_names=feature_names,
        feature_labels=FEATURE_LABELS,
        select_options=SELECT_OPTIONS,
        model_name=model_name,
    )


@app.route("/predict", methods=["POST"])
def predict():
    try:
        scaled, raw = prepare_input(request.form)

        pred = int(model.predict(scaled)[0])
        prob = float(model.predict_proba(scaled)[0][1]) if hasattr(model, "predict_proba") else float(pred)

        risk_level    = get_risk_level(prob)
        risk_reasons  = get_risk_reasons(raw)
        chart_data    = build_chart_data(raw)

        return jsonify({
            "prediction":       "Heart Disease Detected" if pred == 1 else "No Heart Disease",
            "probability_percent": round(prob * 100, 2),
            "risk_level":       risk_level,
            "risk_reasons":     risk_reasons,
            "chart_data":       chart_data,
            "model_name":       model_name,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True)
