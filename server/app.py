import os
import pickle
import secrets
import sqlite3
from datetime import datetime
from io import BytesIO
from pathlib import Path
from zoneinfo import ZoneInfo

from flask import Flask, jsonify, redirect, render_template, request, send_file, session, url_for
from flask_cors import CORS
from xhtml2pdf import pisa

from auth_models import Assessment
from extensions import db
from model import (
    PayloadValidationError,
    adjust_probability,
    build_model_features,
    calculate_heart_age,
    classify_risk,
    derive_primary_drivers,
    generate_recommendations,
    summarize_risk_drivers,
    validate_assessment_payload,
)

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "model.pkl"
DATABASE_PATH = BASE_DIR / "cardiosense.db"
IST = ZoneInfo("Asia/Kolkata")


def _sqlite_uri(path):
    return f"sqlite:///{path.as_posix()}"

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "cardiosense-dev-secret")
app.config["SQLALCHEMY_DATABASE_URI"] = _sqlite_uri(DATABASE_PATH)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["REMEMBER_COOKIE_HTTPONLY"] = True
CORS(app)
db.init_app(app)

with open(MODEL_PATH, "rb") as model_file:
    model = pickle.load(model_file)


def _run_prediction(raw_payload):
    payload = validate_assessment_payload(raw_payload)
    features, context = build_model_features(payload)

    if hasattr(model, "predict_proba"):
        base_probability = float(model.predict_proba(features)[0][1])
    else:
        base_probability = float(model.predict(features)[0])

    adjusted_probability = adjust_probability(base_probability, context)
    risk = classify_risk(adjusted_probability)

    heart_age, penalties = calculate_heart_age(
        actual_age=payload["age"],
        smoking=payload["smoking"],
        blood_pressure=payload["blood_pressure"],
        diabetes=payload["diabetes"],
    )

    primary_drivers = derive_primary_drivers(payload, context, limit=3)
    risk_summary = summarize_risk_drivers(adjusted_probability, primary_drivers)
    recommendations = generate_recommendations(risk, context)

    prediction = {
        "risk": risk,
        "risk_probability": round(adjusted_probability, 4),
        "base_probability": round(base_probability, 4),
        "heart_age": heart_age,
        "heart_age_penalties": penalties,
        "primary_drivers": primary_drivers,
        "risk_summary": risk_summary,
        "recommendations": recommendations,
        "assessed_at": datetime.utcnow().isoformat() + "Z",
    }

    return payload, prediction


def _error_response(exc):
    status_code = 422 if getattr(exc, "is_biological_outlier", False) else 400
    return (
        jsonify(
            {
                "error": str(exc),
                "error_type": "biological_outlier" if status_code == 422 else "validation",
            }
        ),
        status_code,
    )


def format_ist_timestamp(value, fmt="%B %d, %Y - %I:%M %p IST"):
    if value is None:
        return ""

    localized = value
    if localized.tzinfo is None:
        localized = localized.replace(tzinfo=ZoneInfo("UTC"))
    return localized.astimezone(IST).strftime(fmt)


def _persist_authenticated_assessment(payload, prediction):
    assessment = Assessment(
        age=payload["age"],
        blood_pressure=payload["blood_pressure"],
        cholesterol=payload["cholesterol"],
        risk_score=round(float(prediction["risk_probability"]) * 100.0, 1),
        payload_json=payload,
    )
    db.session.add(assessment)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        app.logger.exception("Failed to persist authenticated assessment")
        return None

    session["latest_assessment"] = {
        "payload": payload,
        "prediction": prediction,
    }

    return assessment


def _assessment_bundle_from_record(record):
    payload = record.payload_json or {}
    validated_payload, prediction = _run_prediction(payload)
    prediction["assessed_at"] = format_ist_timestamp(record.created_at)
    return {
        "payload": validated_payload,
        "prediction": prediction,
        "assessment_id": record.id,
    }


def _assessment_bundle_from_session():
    latest_assessment = session.get("latest_assessment") or {}
    return latest_assessment if latest_assessment.get("payload") and latest_assessment.get("prediction") else None


def _reset_legacy_database_if_needed():
    if not DATABASE_PATH.exists():
        return

    with sqlite3.connect(DATABASE_PATH) as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='assessments'")
        if not cursor.fetchone():
            return

        cursor.execute("PRAGMA table_info(assessments)")
        column_names = {row[1] for row in cursor.fetchall()}
        if "user_id" not in column_names:
            return

        cursor.execute("DROP TABLE IF EXISTS assessments")
        cursor.execute("DROP TABLE IF EXISTS users")
        connection.commit()


app.jinja_env.globals["format_ist_timestamp"] = format_ist_timestamp


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/assess")
def assess():
    return render_template("assess.html")


@app.route("/results")
def results():
    latest_assessment = _assessment_bundle_from_session()
    return render_template("results.html", latest_assessment=latest_assessment, selected_record=None)


@app.route("/api/v1/latest-result")
def latest_result():
    latest_assessment = _assessment_bundle_from_session()
    if not latest_assessment:
        return jsonify({"error": "No assessment found in current session."}), 404
    return jsonify(latest_assessment)


@app.route("/api/v1/predict", methods=["POST"])
@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json(silent=True) or {}

    try:
        payload, prediction = _run_prediction(data)
    except PayloadValidationError as exc:
        return _error_response(exc)

    mode = (request.args.get("mode") or "").strip().lower()
    if mode != "simulation":
        assessment = _persist_authenticated_assessment(payload, prediction)
        if assessment:
            prediction["assessment_id"] = assessment.id
            prediction["result_url"] = url_for("results")
            prediction["saved_to_history"] = True
        else:
            session["latest_assessment"] = {
                "payload": payload,
                "prediction": prediction,
            }
            prediction["saved_to_history"] = False

    return jsonify(prediction)


@app.route("/api/v1/report", methods=["POST"])
def download_report():
    data = request.get_json(silent=True) or {}
    payload = data.get("payload")

    if not payload:
        latest_assessment = session.get("latest_assessment") or {}
        payload = latest_assessment.get("payload")

    if not payload:
        return jsonify({"error": "No assessment payload provided for report generation."}), 400

    try:
        validated_payload, prediction = _run_prediction(payload)
    except PayloadValidationError as exc:
        return _error_response(exc)

    risk_percent = round(float(prediction["risk_probability"]) * 100.0, 1)
    gauge_fill_percent = max(2.0, min(100.0, risk_percent))
    assessment_id = f"CS-{datetime.utcnow():%Y}-{secrets.randbelow(10000):04d}"

    report_context = {
        "generated_on": datetime.utcnow().strftime("%d %b %Y %H:%M UTC"),
        "assessment_id": assessment_id,
        "payload": validated_payload,
        "prediction": prediction,
        "drivers": prediction["primary_drivers"],
        "recommendations": prediction["recommendations"],
        "risk_percent": risk_percent,
        "gauge_fill_percent": gauge_fill_percent,
        "gauge_rest_percent": round(100.0 - gauge_fill_percent, 1),
    }

    html = render_template("report_pdf.html", report=report_context)

    pdf_buffer = BytesIO()
    pdf_status = pisa.CreatePDF(html, dest=pdf_buffer, encoding="utf-8")
    if pdf_status.err:
        return jsonify({"error": "Failed to generate PDF report."}), 500

    pdf_buffer.seek(0)
    filename = f"CardioSense_Medical_Summary_{datetime.utcnow():%Y%m%d_%H%M%S}.pdf"

    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf",
    )


with app.app_context():
    _reset_legacy_database_if_needed()
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True)
