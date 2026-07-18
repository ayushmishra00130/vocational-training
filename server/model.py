import pandas as pd

FEATURE_COLUMNS = [
    "age",
    "sex",
    "cp",
    "trestbps",
    "chol",
    "fbs",
    "restecg",
    "thalach",
    "exang",
    "oldpeak",
    "slope",
    "ca",
    "thal",
]

CATEGORICAL_COLUMNS = ["sex", "cp", "fbs", "restecg", "exang", "slope", "thal"]
NUMERIC_COLUMNS = [col for col in FEATURE_COLUMNS if col not in CATEGORICAL_COLUMNS]

CATEGORY_MAPS = {
    "sex": {"male": 1, "female": 0, "m": 1, "f": 0, 1: 1, 0: 0},
    "cp": {
        "typical angina": 0,
        "atypical angina": 1,
        "non-anginal": 2,
        "asymptomatic": 3,
        "typical": 0,
        "atypical": 1,
        "non_anginal": 2,
        "none": 3,
        0: 0,
        1: 1,
        2: 2,
        3: 3,
    },
    "fbs": {"true": 1, "false": 0, "yes": 1, "no": 0, True: 1, False: 0, 1: 1, 0: 0},
    "restecg": {
        "normal": 0,
        "st-t abnormality": 1,
        "lv hypertrophy": 2,
        "abnormal": 2,
        0: 0,
        1: 1,
        2: 2,
    },
    "exang": {"true": 1, "false": 0, "yes": 1, "no": 0, True: 1, False: 0, 1: 1, 0: 0},
    "slope": {"upsloping": 0, "flat": 1, "downsloping": 2, 0: 0, 1: 1, 2: 2},
    "thal": {
        "normal": 2,
        "fixed defect": 1,
        "reversable defect": 3,
        "reversible defect": 3,
        1: 1,
        2: 2,
        3: 3,
    },
}

REQUIRED_FIELDS = [
    "age",
    "sex",
    "blood_pressure",
    "cholesterol",
    "chest_pain",
    "shortness_of_breath",
    "fatigue",
    "irregular_heartbeat",
    "smoking",
    "diabetes",
]

DRIVER_LABELS = {
    "age": "Age",
    "blood_pressure": "Blood Pressure",
    "cholesterol": "Cholesterol",
    "smoking": "Smoking",
    "diabetes": "Diabetes",
    "symptoms": "Current Symptoms",
}

DRIVER_SUMMARY_PHRASES = {
    "age": "age-related factors",
    "blood_pressure": "high blood pressure",
    "cholesterol": "high cholesterol",
    "smoking": "smoking history",
    "diabetes": "diabetes-related strain",
    "symptoms": "active symptom burden",
}

SMOKING_MAP = {
    "never": "never",
    "no": "never",
    "none": "never",
    "0": "never",
    "former": "former",
    "past": "former",
    "used": "former",
    "current": "current",
    "yes": "current",
    "active": "current",
    "1": "current",
    "true": "current",
}


class PayloadValidationError(ValueError):
    def __init__(self, message, is_biological_outlier=False):
        super().__init__(message)
        self.is_biological_outlier = is_biological_outlier


def _normalize_key(value):
    if isinstance(value, str):
        return value.strip().lower()
    return value


def _to_float(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _to_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        return normalized in {"1", "true", "yes", "y", "on", "current", "former"}
    return False


def _encode_with_map(value, mapping, default_value):
    direct = mapping.get(value)
    if direct is not None:
        return direct
    normalized = _normalize_key(value)
    mapped = mapping.get(normalized)
    if mapped is not None:
        return mapped
    return default_value


def _normalize_smoking(value):
    if value is None:
        return "never"
    key = _normalize_key(value)
    if key in SMOKING_MAP:
        return SMOKING_MAP[key]
    return "never"


def validate_assessment_payload(payload):
    data = payload or {}
    missing = [field for field in REQUIRED_FIELDS if field not in data]
    if missing:
        raise PayloadValidationError(f"Missing required fields: {missing}")

    age = _to_float(data.get("age"), -1)
    blood_pressure = _to_float(data.get("blood_pressure"), -1)
    cholesterol = _to_float(data.get("cholesterol"), -1)

    if age < 18 or age > 120:
        raise PayloadValidationError(
            "Biological Outlier: Age appears outside realistic human screening bounds (18-120).",
            is_biological_outlier=True,
        )

    if blood_pressure < 70 or blood_pressure > 260:
        raise PayloadValidationError(
            "Biological Outlier: Blood Pressure appears outside realistic clinical bounds (70-260 mmHg).",
            is_biological_outlier=True,
        )

    if cholesterol < 80 or cholesterol > 700:
        raise PayloadValidationError(
            "Biological Outlier: Cholesterol appears outside realistic lab bounds (80-700 mg/dL).",
            is_biological_outlier=True,
        )

    sex = _normalize_key(data.get("sex", "male"))
    if sex not in {"male", "female", "m", "f", 0, 1}:
        raise PayloadValidationError("Sex must be one of: male, female.")

    chest_pain = _normalize_key(data.get("chest_pain", "none"))
    if chest_pain not in {
        "none",
        "typical angina",
        "atypical angina",
        "non-anginal",
        "asymptomatic",
        "typical",
        "atypical",
        "non_anginal",
    }:
        raise PayloadValidationError(
            "Chest pain value is invalid. Use one of: none, typical angina, atypical angina, non-anginal."
        )

    smoking = _normalize_smoking(data.get("smoking"))

    return {
        "age": int(round(age)),
        "blood_pressure": int(round(blood_pressure)),
        "cholesterol": int(round(cholesterol)),
        "sex": "male" if sex in {"male", "m", 1} else "female",
        "chest_pain": "non-anginal" if chest_pain == "non_anginal" else str(chest_pain),
        "shortness_of_breath": _to_bool(data.get("shortness_of_breath", False)),
        "fatigue": _to_bool(data.get("fatigue", False)),
        "irregular_heartbeat": _to_bool(data.get("irregular_heartbeat", False)),
        "smoking": smoking,
        "diabetes": _to_bool(data.get("diabetes", False)),
    }


def build_model_features(payload):
    age = _to_float(payload.get("age"), 54)
    blood_pressure = _to_float(payload.get("blood_pressure"), 130)
    cholesterol = _to_float(payload.get("cholesterol"), 245)

    sex = _encode_with_map(payload.get("sex", "male"), CATEGORY_MAPS["sex"], 1)
    chest_pain = _encode_with_map(payload.get("chest_pain", "none"), CATEGORY_MAPS["cp"], 3)

    shortness_of_breath = _to_bool(payload.get("shortness_of_breath", False))
    fatigue = _to_bool(payload.get("fatigue", False))
    irregular_heartbeat = _to_bool(payload.get("irregular_heartbeat", False))

    smoking = _normalize_smoking(payload.get("smoking", "never"))
    smoking_current = smoking == "current"
    smoking_former = smoking == "former"
    diabetes = _to_bool(payload.get("diabetes", False))

    # Derive proxy clinical attributes required by the trained dataset model.
    thalach_estimate = max(85.0, min(202.0, 208.0 - (0.7 * age) - (8.0 if shortness_of_breath else 0.0)))
    oldpeak_estimate = min(
        6.0,
        0.6 + (0.7 if shortness_of_breath else 0.0) + (0.4 if fatigue else 0.0) + (0.4 if irregular_heartbeat else 0.0),
    )
    slope_value = 2 if (shortness_of_breath or fatigue) else 1
    restecg_value = 2 if irregular_heartbeat else 0
    exang_value = 1 if shortness_of_breath else 0
    fbs_value = 1 if diabetes else 0
    ca_value = min(3, int(smoking_current) + int(diabetes) + int(irregular_heartbeat))
    thal_value = 3 if (smoking_current and shortness_of_breath) else 2

    feature_row = {
        "age": age,
        "sex": sex,
        "cp": chest_pain,
        "trestbps": blood_pressure,
        "chol": cholesterol,
        "fbs": fbs_value,
        "restecg": restecg_value,
        "thalach": thalach_estimate,
        "exang": exang_value,
        "oldpeak": oldpeak_estimate,
        "slope": slope_value,
        "ca": ca_value,
        "thal": thal_value,
    }

    features = pd.DataFrame([feature_row], columns=FEATURE_COLUMNS)

    for col in CATEGORICAL_COLUMNS:
        features[col] = pd.to_numeric(features[col], errors="coerce").fillna(0).astype(int)
    for col in NUMERIC_COLUMNS:
        features[col] = pd.to_numeric(features[col], errors="coerce").fillna(0.0)

    context = {
        "shortness_of_breath": shortness_of_breath,
        "fatigue": fatigue,
        "irregular_heartbeat": irregular_heartbeat,
        "smoking_current": smoking_current,
        "smoking_former": smoking_former,
        "diabetes": diabetes,
        "blood_pressure": blood_pressure,
        "cholesterol": cholesterol,
        "smoking": smoking,
        "age": age,
    }

    return features, context


def adjust_probability(base_probability, context):
    adjusted = float(base_probability)
    adjusted += 0.07 if context["diabetes"] else 0.0
    adjusted += 0.06 if context["smoking_current"] else 0.0
    adjusted += 0.03 if context["smoking_former"] else 0.0
    adjusted += 0.05 if context["shortness_of_breath"] else 0.0
    adjusted += 0.04 if context["fatigue"] else 0.0
    adjusted += 0.05 if context["irregular_heartbeat"] else 0.0

    if context["blood_pressure"] >= 140:
        adjusted += 0.04
    if context["cholesterol"] >= 240:
        adjusted += 0.03

    return min(0.99, max(0.01, adjusted))


def classify_risk(probability):
    if probability < 0.35:
        return "Low"
    if probability < 0.70:
        return "Medium"
    return "High"


def calculate_heart_age(actual_age, smoking, blood_pressure, diabetes):
    penalties = {
        "Smoking": 5 if smoking in {"current", "former"} else 0,
        "High BP": 4 if blood_pressure >= 140 else 0,
        "Diabetes": 3 if diabetes else 0,
    }
    heart_age = int(round(actual_age + sum(penalties.values())))
    return heart_age, penalties


def derive_primary_drivers(payload, context, limit=3):
    age = float(payload.get("age", 0))
    blood_pressure = float(payload.get("blood_pressure", 0))
    cholesterol = float(payload.get("cholesterol", 0))
    smoking = _normalize_smoking(payload.get("smoking", "never"))

    symptom_score = 0.0
    symptom_score += 1.3 if context.get("shortness_of_breath") else 0.0
    symptom_score += 0.9 if context.get("fatigue") else 0.0
    symptom_score += 1.2 if context.get("irregular_heartbeat") else 0.0

    chest_pain = _normalize_key(payload.get("chest_pain", "none"))
    if chest_pain in {"typical angina", "typical"}:
        symptom_score += 1.3
    elif chest_pain in {"atypical angina", "atypical"}:
        symptom_score += 0.7

    scores = {
        "age": max(0.0, (age - 35.0) / 45.0) * 2.4,
        "blood_pressure": max(0.0, (blood_pressure - 120.0) / 45.0) * 2.7,
        "cholesterol": max(0.0, (cholesterol - 180.0) / 140.0) * 2.0,
        "smoking": 2.3 if smoking == "current" else (1.0 if smoking == "former" else 0.1),
        "diabetes": 2.0 if context.get("diabetes") else 0.0,
        "symptoms": symptom_score,
    }

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    top = [(feature, score) for feature, score in ranked if score > 0][:limit]
    if not top:
        top = [("age", 1.0)]

    total = sum(score for _, score in top) or 1.0

    drivers = []
    for feature, score in top:
        drivers.append(
            {
                "feature": feature,
                "label": DRIVER_LABELS[feature],
                "summary": DRIVER_SUMMARY_PHRASES[feature],
                "score": round(score, 4),
                "impact_percent": round((score / total) * 100.0, 1),
            }
        )

    return drivers


def summarize_risk_drivers(risk_probability, drivers):
    risk_pct = int(round(float(risk_probability) * 100))

    if len(drivers) >= 2:
        first = drivers[0]["summary"]
        second = drivers[1]["summary"]
        return f"Your {risk_pct}% risk score is primarily driven by {first} and {second}."

    if len(drivers) == 1:
        only = drivers[0]["summary"]
        return f"Your {risk_pct}% risk score is primarily driven by {only}."

    return f"Your {risk_pct}% risk score reflects your current cardio-metabolic profile."


def generate_recommendations(risk_level, context):
    recommendations = []

    if risk_level == "High":
        recommendations.append("Book a cardiology consultation as soon as possible for a full clinical evaluation.")
        recommendations.append(
            "Track blood pressure daily and seek urgent care for chest pain, severe breathlessness, or fainting."
        )
    elif risk_level == "Medium":
        recommendations.append("Schedule a preventive health check within the next 2-4 weeks.")
        recommendations.append("Monitor symptoms and blood pressure weekly and discuss trends with a doctor.")
    else:
        recommendations.append("Maintain regular annual checkups and continue heart-healthy habits.")

    if context["smoking_current"]:
        recommendations.append("Start a smoking cessation plan immediately and seek support if needed.")
    elif context["smoking_former"]:
        recommendations.append("Continue staying smoke-free and reinforce relapse-prevention habits.")

    if context["diabetes"]:
        recommendations.append("Keep blood glucose under control and follow your diabetes care plan closely.")
    if context["blood_pressure"] >= 140:
        recommendations.append("Reduce sodium intake, improve sleep quality, and follow blood pressure treatment guidance.")
    if context["cholesterol"] >= 240:
        recommendations.append("Adopt a low-saturated-fat diet and request a lipid profile review.")
    if context["shortness_of_breath"] or context["irregular_heartbeat"]:
        recommendations.append("Do not ignore persistent breathing changes or palpitations; seek medical assessment promptly.")

    recommendations.append("This tool is a screening assistant and does not replace professional diagnosis.")
    return recommendations