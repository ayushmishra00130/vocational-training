from datetime import datetime

from extensions import db


class Assessment(db.Model):
    __tablename__ = "assessments"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    age = db.Column(db.Integer, nullable=False)
    blood_pressure = db.Column(db.Integer, nullable=False)
    cholesterol = db.Column(db.Integer, nullable=False)
    risk_score = db.Column(db.Float, nullable=False)
    payload_json = db.Column(db.JSON, nullable=False)
