from app import db
from datetime import datetime


class LifeCheckIn(db.Model):
    __tablename__ = "life_checkins"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    checkin_type = db.Column(db.String(30), nullable=False)
    details = db.Column(db.Text, nullable=True)
    amount = db.Column(db.Numeric(10, 2), nullable=True)
    plan_adjusted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("life_checkins", lazy=True))

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.checkin_type,
            "details": self.details,
            "amount": float(self.amount) if self.amount else None,
            "plan_adjusted": self.plan_adjusted,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }