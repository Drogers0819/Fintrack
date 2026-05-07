from app import db


class Goal(db.Model):
    __tablename__ = "goals"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(20), nullable=False)
    target_amount = db.Column(db.Numeric(10, 2), nullable=True)
    current_amount = db.Column(db.Numeric(10, 2), default=0)
    monthly_allocation = db.Column(db.Numeric(10, 2), nullable=True)
    deadline = db.Column(db.Date, nullable=True)
    priority_rank = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), default="active")
    is_essential = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def _calculate_progress(self):
        if not self.target_amount or float(self.target_amount) == 0:
            return None
        progress = (float(self.current_amount) / float(self.target_amount)) * 100
        return min(round(progress, 1), 100)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "type": self.type,
            "target_amount": float(self.target_amount) if self.target_amount else None,
            "current_amount": float(self.current_amount) if self.current_amount else 0,
            "monthly_allocation": float(self.monthly_allocation) if self.monthly_allocation else None,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "priority_rank": self.priority_rank,
            "status": self.status,
            "is_essential": bool(self.is_essential),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "progress_percent": self._calculate_progress()
        }

    def __repr__(self):
        return f"<Goal {self.id}: {self.name} ({self.status})>"