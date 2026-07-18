# CardioSense AI - Full Project Explanation

## 1) What this project is

CardioSense AI is a server-rendered Flask multi-page screening application for cardiovascular risk triage.

It provides:
- A 3-step assessment wizard
- Model-driven risk scoring with explainable drivers
- Heart-age estimation
- What-if simulation controls for modifiable factors
- Downloadable clinical summary PDF

Important: this is a screening support tool, not a clinical diagnosis system.

## 2) Current architecture

The system is organized into three runtime layers:

1. Flask web app and APIs
1. Flask web app and APIs
- File: server/app.py
- Serves pages: /, /assess, /results
- Exposes APIs: /api/v1/predict, /api/v1/latest-result, /api/v1/report

2. ML and risk logic
2. ML and risk logic
- File: server/model.py
- Handles payload validation, feature engineering, calibration, risk banding, explainability, and recommendations

3. Training pipeline
3. Training pipeline
- File: server/train_model.py
- Trains and exports server/model.pkl

UI assets are centralized in:
UI assets are centralized in:
- server/templates/
- server/static/

## 3) Data and target

Dataset:
- server/heart.csv

Notes:
- Label column in dataset is num
- Training converts num into a binary prediction target

## 4) Runtime prediction flow

1. User completes the wizard on /assess
2. Browser sends JSON to /api/v1/predict
3. Backend validates bounds and required fields
4. Feature engineering maps questionnaire data into model-compatible feature space
5. Model outputs base probability
6. Clinical calibration adjusts probability using symptom/lifestyle context
7. Final probability is converted into Low/Medium/High risk band
8. Explainability module generates top primary drivers and narrative summary
9. Recommendations are generated and returned

## 5) Results dashboard behavior

The /results page shows:
- Risk outlook gauge
- Heart age
- Primary driver chart with status indicators
- Simulation controls for blood pressure, cholesterol, smoking, and diabetes modifier
- Preventive recommendations based on original assessment input
- Download Medical Summary action

Simulation updates risk metrics and charts but does not overwrite baseline recommendations.

## 6) PDF report generation

Endpoint:
- POST /api/v1/report

The report includes:
- Assessment ID in format CS-YYYY-XXXX
- Risk level, risk score, and heart age
- Gauge visual and driver bar chart
- Clinical interpretation and recommendations
- Professional disclaimer

## 7) Setup and run

From project root:

```powershell
python -m pip install -r requirements.txt
python app.py
```

App URL:
- http://127.0.0.1:5000

## 8) Limitations and responsible use

- This tool is for computational screening and awareness support.
- It does not replace cardiology consultation, emergency care, or formal diagnosis.
- Use clinical judgment for any high-risk symptoms.

## 9) Summary

CardioSense AI combines calibrated ML risk prediction, explainability, simulation, and clinical-style reporting into a single professional Flask MPA workflow.
