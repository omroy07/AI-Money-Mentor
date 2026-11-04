"""
FIRE (Financial Independence, Retire Early) Planner Feature Blueprint.

Provides interactive retirement path calculation, Monte Carlo simulations,
and visualization data endpoints.
"""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from utils.fire_planner import FIREPlanner

fire_planner_bp = Blueprint("fire_planner", __name__)


@fire_planner_bp.route("/fire-planner")
@login_required
def fire_planner_page():
    """Render the main FIRE Planner interactive calculator view."""
    return render_template("fire_planner.html", active_page="fire_planner")


@fire_planner_bp.route("/api/fire/plan", methods=["POST"])
@login_required
def fire_plan():
    """Calculate detailed FIRE path projection and visualization milestones."""
    try:
        data = request.json or {}
        planner = FIREPlanner(
            current_age=data.get("current_age", 30),
            retirement_age=data.get("retirement_age", 45),
            annual_expenses=data.get("annual_expenses", 500000),
            current_corpus=data.get("current_corpus", 1000000),
            monthly_savings=data.get("monthly_savings", 30000),
            return_mean=data.get("return_mean", 0.10),
            return_std=data.get("return_std", 0.15),
            inflation_rate=data.get("inflation_rate", 0.06),
        )
        plan = planner.get_plan_summary()
        return jsonify({
            "success": True,
            "data": plan,
            "visualization": planner.get_visualization_data(),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@fire_planner_bp.route("/api/fire/quick", methods=["POST"])
@login_required
def fire_quick():
    """Run quick Monte Carlo simulation for probability of success."""
    try:
        data = request.json or {}
        planner = FIREPlanner(
            current_age=data.get("current_age", 30),
            retirement_age=data.get("retirement_age", 45),
            annual_expenses=data.get("annual_expenses", 500000),
            current_corpus=data.get("current_corpus", 1000000),
            monthly_savings=data.get("monthly_savings", 30000),
            return_mean=data.get("return_mean", 0.10),
            return_std=data.get("return_std", 0.15),
            inflation_rate=data.get("inflation_rate", 0.06),
        )
        mc_results = planner.run_monte_carlo(iterations=200)
        return jsonify({
            "success": True,
            "success_probability": mc_results["success"]["probability"],
            "median_corpus": mc_results["corpus"]["median"],
            "target_corpus": planner.target_corpus,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
