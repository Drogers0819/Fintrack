from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.goal import Goal
from datetime import date

goal_bp = Blueprint("goals", __name__, url_prefix="/api/goals")


@goal_bp.route("", methods=["POST"])
@login_required
def create_goal():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    name = data.get("name", "").strip()
    goal_type = data.get("type", "").strip().lower()

    if not name:
        return jsonify({"error": "Name is required"}), 400

    if goal_type not in ("savings_target", "spending_allocation", "accumulation"):
        return jsonify({"error": "Type must be 'savings_target', 'spending_allocation', or 'accumulation'"}), 400

    target_amount = None
    if data.get("target_amount") is not None:
        try:
            target_amount = round(float(data["target_amount"]), 2)
            if target_amount <= 0:
                return jsonify({"error": "Target amount must be greater than zero"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "Target amount must be a valid number"}), 400

    monthly_allocation = None
    if data.get("monthly_allocation") is not None:
        try:
            monthly_allocation = round(float(data["monthly_allocation"]), 2)
            if monthly_allocation < 0:
                return jsonify({"error": "Monthly allocation cannot be negative"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "Monthly allocation must be a valid number"}), 400

    current_amount = 0
    if data.get("current_amount") is not None:
        try:
            current_amount = round(float(data["current_amount"]), 2)
            if current_amount < 0:
                return jsonify({"error": "Current amount cannot be negative"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "Current amount must be a valid number"}), 400

    deadline = None
    if data.get("deadline"):
        try:
            deadline = date.fromisoformat(data["deadline"])
        except (ValueError, TypeError):
            return jsonify({"error": "Deadline must be in YYYY-MM-DD format"}), 400

    priority_rank = data.get("priority_rank", 1)
    if not isinstance(priority_rank, int) or priority_rank < 1:
        return jsonify({"error": "Priority rank must be a positive integer"}), 400

    goal = Goal(
        user_id=current_user.id,
        name=name,
        type=goal_type,
        target_amount=target_amount,
        current_amount=current_amount,
        monthly_allocation=monthly_allocation,
        deadline=deadline,
        priority_rank=priority_rank
    )

    db.session.add(goal)
    db.session.commit()

    return jsonify({
        "message": "Goal created successfully",
        "goal": goal.to_dict()
    }), 201


@goal_bp.route("", methods=["GET"])
@login_required
def list_goals():
    status_filter = request.args.get("status", "active")

    query = Goal.query.filter_by(user_id=current_user.id)

    if status_filter != "all":
        query = query.filter_by(status=status_filter)

    goals = query.order_by(Goal.priority_rank.asc()).all()

    return jsonify({
        "goals": [g.to_dict() for g in goals],
        "count": len(goals)
    }), 200


@goal_bp.route("/<int:goal_id>", methods=["GET"])
@login_required
def get_goal(goal_id):
    goal = Goal.query.filter_by(
        id=goal_id,
        user_id=current_user.id
    ).first()

    if not goal:
        return jsonify({"error": "Goal not found"}), 404

    return jsonify({"goal": goal.to_dict()}), 200


@goal_bp.route("/<int:goal_id>", methods=["PUT"])
@login_required
def update_goal(goal_id):
    goal = Goal.query.filter_by(
        id=goal_id,
        user_id=current_user.id
    ).first()

    if not goal:
        return jsonify({"error": "Goal not found"}), 404

    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    if "name" in data:
        name = data["name"].strip()
        if not name:
            return jsonify({"error": "Name cannot be empty"}), 400
        goal.name = name

    if "type" in data:
        goal_type = data["type"].strip().lower()
        if goal_type not in ("savings_target", "spending_allocation", "accumulation"):
            return jsonify({"error": "Type must be 'savings_target', 'spending_allocation', or 'accumulation'"}), 400
        goal.type = goal_type

    if "target_amount" in data:
        if data["target_amount"] is None:
            goal.target_amount = None
        else:
            try:
                target = round(float(data["target_amount"]), 2)
                if target <= 0:
                    return jsonify({"error": "Target amount must be greater than zero"}), 400
                goal.target_amount = target
            except (ValueError, TypeError):
                return jsonify({"error": "Target amount must be a valid number"}), 400

    if "current_amount" in data:
        try:
            current = round(float(data["current_amount"]), 2)
            if current < 0:
                return jsonify({"error": "Current amount cannot be negative"}), 400
            goal.current_amount = current
        except (ValueError, TypeError):
            return jsonify({"error": "Current amount must be a valid number"}), 400

    if "monthly_allocation" in data:
        if data["monthly_allocation"] is None:
            goal.monthly_allocation = None
        else:
            try:
                allocation = round(float(data["monthly_allocation"]), 2)
                if allocation < 0:
                    return jsonify({"error": "Monthly allocation cannot be negative"}), 400
                goal.monthly_allocation = allocation
            except (ValueError, TypeError):
                return jsonify({"error": "Monthly allocation must be a valid number"}), 400

    if "deadline" in data:
        if data["deadline"] is None:
            goal.deadline = None
        else:
            try:
                goal.deadline = date.fromisoformat(data["deadline"])
            except (ValueError, TypeError):
                return jsonify({"error": "Deadline must be in YYYY-MM-DD format"}), 400

    if "priority_rank" in data:
        if not isinstance(data["priority_rank"], int) or data["priority_rank"] < 1:
            return jsonify({"error": "Priority rank must be a positive integer"}), 400
        goal.priority_rank = data["priority_rank"]

    if "status" in data:
        if data["status"] not in ("active", "completed", "paused"):
            return jsonify({"error": "Status must be 'active', 'completed', or 'paused'"}), 400
        goal.status = data["status"]

    db.session.commit()

    return jsonify({
        "message": "Goal updated successfully",
        "goal": goal.to_dict()
    }), 200


@goal_bp.route("/<int:goal_id>", methods=["DELETE"])
@login_required
def delete_goal(goal_id):
    goal = Goal.query.filter_by(
        id=goal_id,
        user_id=current_user.id
    ).first()

    if not goal:
        return jsonify({"error": "Goal not found"}), 404

    db.session.delete(goal)
    db.session.commit()

    return jsonify({"message": "Goal deleted successfully"}), 200