"""
Smart Goal-Based Investment Planner with Auto-Allocation
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
import json

from models import db, InvestmentGoal, GoalAllocation, GoalContribution, GoalRecommendation


class GoalInvestmentPlanner:
    """
    Smart Goal-Based Investment Planner with Auto-Allocation
    """
    
    def __init__(self, client=None):
        self.client = client
        
        # Asset allocation templates based on timeframe
        self.allocation_templates = {
            'short_term': {
                'equity': 20,
                'debt': 50,
                'gold': 10,
                'cash': 20
            },
            'medium_term': {
                'equity': 50,
                'debt': 30,
                'gold': 15,
                'cash': 5
            },
            'long_term': {
                'equity': 70,
                'debt': 15,
                'gold': 10,
                'cash': 5
            }
        }
    
    def create_goal(self, user_id: int, data: Dict) -> Dict:
        """
        Create a new investment goal
        
        Args:
            user_id: User ID
            data: Goal data
        
        Returns:
            Dict with created goal
        """
        # Calculate timeframe in months
        if data.get('target_date'):
            target_date = datetime.strptime(data['target_date'], '%Y-%m-%d')
            timeframe = max(1, (target_date - datetime.now()).days // 30)
        else:
            timeframe = data.get('timeframe', 12)
        
        goal = InvestmentGoal(
            user_id=user_id,
            name=data['name'],
            description=data.get('description', ''),
            category=data.get('category', 'medium_term'),
            target_amount=Decimal(str(data['target_amount'])),
            current_amount=Decimal(str(data.get('current_amount', 0))),
            priority=data.get('priority', 3),
            timeframe=timeframe,
            target_date=datetime.strptime(data['target_date'], '%Y-%m-%d') if data.get('target_date') else None,
            icon=data.get('icon', '🎯')
        )
        
        db.session.add(goal)
        db.session.flush()
        
        # Create auto-allocation
        allocation = self.generate_allocation(goal.category, goal.timeframe)
        for asset_type, percentage in allocation.items():
            goal_allocation = GoalAllocation(
                goal_id=goal.id,
                asset_type=asset_type,
                percentage=percentage
            )
            db.session.add(goal_allocation)
        
        db.session.commit()
        
        return {
            'success': True,
            'goal': goal.to_dict()
        }
    
    def generate_allocation(self, category: str, timeframe: int) -> Dict:
        """
        Generate optimized allocation for a goal
        
        Args:
            category: short_term, medium_term, long_term
            timeframe: Months until goal
        
        Returns:
            Dict with asset allocation
        """
        # Start with template
        template = self.allocation_templates.get(category, self.allocation_templates['medium_term'])
        
        # Adjust based on timeframe
        if category == 'short_term' and timeframe < 6:
            # More conservative for very short-term
            return {
                'equity': 10,
                'debt': 60,
                'gold': 10,
                'cash': 20
            }
        elif category == 'long_term' and timeframe > 120:
            # More aggressive for very long-term
            return {
                'equity': 80,
                'debt': 10,
                'gold': 5,
                'cash': 5
            }
        
        return template
    
    def allocate_funds(self, user_id: int) -> Dict:
        """
        Auto-allocate funds across all goals based on priority
        
        Args:
            user_id: User ID
        
        Returns:
            Dict with allocation results
        """
        goals = InvestmentGoal.query.filter_by(
            user_id=user_id,
            status='ACTIVE'
        ).order_by(InvestmentGoal.priority.asc()).all()
        
        if not goals:
            return {'success': False, 'error': 'No active goals found'}
        
      # Calculate total priority weight. Goals use a 1-5 scale where 1 is
        # the highest priority (see create_goal()'s default and
        # get_recommendations_ai()'s "Priority: {goal.priority}/5" label), so
        # we invert priority here to give lower-numbered (higher-priority)
        # goals a bigger weight. This keeps weight consistent with
        # adjusted_amount below, which already treats priority=1 as most
        # urgent.
        total_inverted_priority = sum(6 - g.priority for g in goals)
        if total_inverted_priority == 0:
            total_inverted_priority = 1
        
        # Calculate recommended allocation
        allocations = {}
        for goal in goals:
            inverted_priority = 6 - goal.priority  # 1 -> 5, 5 -> 1 on a 1-5 scale
            weight = inverted_priority / total_inverted_priority
            monthly_recommended = goal.calculate_monthly_required()
            
            # Adjust based on priority
            adjusted_amount = monthly_recommended * (1 + (5 - goal.priority) * 0.1)
            
            allocations[goal.id] = {
                'goal_name': goal.name,
                'goal_id': goal.id,
                'priority': goal.priority,
                'weight': round(weight * 100, 2),
                'recommended_monthly': round(adjusted_amount, 2),
                'current_monthly': goal.calculate_monthly_required()
            }
        
        return {
            'success': True,
            'total_goals': len(goals),
            'allocations': allocations,
            'total_recommended': sum(a['recommended_monthly'] for a in allocations.values())
        }
    
    def add_contribution(self, goal_id: int, amount: float, source: str = 'manual', note: str = "") -> Dict:
        """
        Add a contribution to a goal
        
        Args:
            goal_id: Goal ID
            amount: Contribution amount
            source: Source of contribution
            note: Optional note
        
        Returns:
            Dict with updated goal
        """
        goal = InvestmentGoal.query.get(goal_id)
        if not goal:
            return {'success': False, 'error': 'Goal not found'}
        
        contribution = GoalContribution(
            goal_id=goal_id,
            amount=Decimal(str(amount)),
            source=source,
            note=note
        )
        db.session.add(contribution)
        
        # Update goal current amount
        goal.current_amount = Decimal(str(goal.current_amount)) + Decimal(str(amount))
        goal.updated_at = datetime.utcnow()
        
        # Check if goal is completed
        if goal.current_amount >= goal.target_amount:
            goal.status = 'COMPLETED'
            goal.completed_at = datetime.utcnow()
        
        db.session.commit()
        
        # Generate recommendations if needed
        self.generate_recommendations(goal_id)
        
        return {
            'success': True,
            'goal': goal.to_dict()
        }
    
    def generate_recommendations(self, goal_id: int) -> List[Dict]:
        """
        Generate AI-powered recommendations for a goal
        
        Args:
            goal_id: Goal ID
        
        Returns:
            List of recommendations
        """
        goal = InvestmentGoal.query.get(goal_id)
        if not goal:
            return []
        
        recommendations = []
        
        # Check progress
        progress = float(goal.current_amount) / float(goal.target_amount) * 100 if float(goal.target_amount) > 0 else 0
        remaining_months = goal.timeframe
        monthly_required = goal.calculate_monthly_required()
        
        # Recommendation 1: Progress-based
        if progress < 30 and remaining_months > 0:
            rec = GoalRecommendation(
                goal_id=goal_id,
                type='contribution',
                message=f'Your goal "{goal.name}" is only {progress:.1f}% complete',
                suggestion=f'Increase monthly contribution by ₹{monthly_required * 0.3:.2f} to stay on track'
            )
            db.session.add(rec)
            recommendations.append(rec.to_dict())
        
        # Recommendation 2: Time-based
        if remaining_months < 6 and progress < 80:
            rec = GoalRecommendation(
                goal_id=goal_id,
                type='timeline',
                message=f'Only {remaining_months} months remaining for "{goal.name}"',
                suggestion='Consider increasing your contribution or extending the timeline'
            )
            db.session.add(rec)
            recommendations.append(rec.to_dict())
        
        # Recommendation 3: Allocation-based
        allocations = GoalAllocation.query.filter_by(goal_id=goal_id).all()
        if allocations:
            rec = GoalRecommendation(
                goal_id=goal_id,
                type='allocation',
                message=f'Review allocation for "{goal.name}"',
                suggestion=f'Consider adjusting allocation based on remaining {remaining_months} months'
            )
            db.session.add(rec)
            recommendations.append(rec.to_dict())
        
        db.session.commit()
        return recommendations
    
    def get_goal_analytics(self, user_id: int) -> Dict:
        """
        Get analytics for all goals
        
        Args:
            user_id: User ID
        
        Returns:
            Dict with analytics
        """
        goals = InvestmentGoal.query.filter_by(user_id=user_id).all()
        
        if not goals:
            return {'success': True, 'has_goals': False}
        
        total_target = sum(float(g.target_amount) for g in goals)
        total_current = sum(float(g.current_amount) for g in goals)
        total_progress = (total_current / total_target * 100) if total_target > 0 else 0
        
        completed = len([g for g in goals if g.status == 'COMPLETED'])
        active = len([g for g in goals if g.status == 'ACTIVE'])
        
        category_distribution = {}
        for g in goals:
            category_distribution[g.category] = category_distribution.get(g.category, 0) + float(g.target_amount)
        
        # Monthly requirements
        monthly_requirements = []
        for g in goals:
            if g.status == 'ACTIVE':
                monthly_requirements.append({
                    'name': g.name,
                    'monthly_required': g.calculate_monthly_required(),
                    'progress': float(g.current_amount) / float(g.target_amount) * 100 if float(g.target_amount) > 0 else 0
                })
        
        return {
            'success': True,
            'has_goals': True,
            'total_goals': len(goals),
            'completed_goals': completed,
            'active_goals': active,
            'total_target': total_target,
            'total_current': total_current,
            'total_progress': round(total_progress, 2),
            'category_distribution': category_distribution,
            'monthly_requirements': monthly_requirements,
            'on_track': total_progress >= 50
        }
    
    def get_recommendations_ai(self, user_id: int) -> Dict:
        """
        Get AI-powered recommendations for all goals
        
        Args:
            user_id: User ID
        
        Returns:
            Dict with recommendations
        """
        if not self.client:
            return {'success': False, 'error': 'AI client not configured'}
        
        goals = InvestmentGoal.query.filter_by(user_id=user_id, status='ACTIVE').all()
        if not goals:
            return {'success': False, 'error': 'No active goals'}
        
        # Prepare goal summary for AI
        goal_summary = ""
        for goal in goals:
            progress = float(goal.current_amount) / float(goal.target_amount) * 100 if float(goal.target_amount) > 0 else 0
            goal_summary += f"""
            Goal: {goal.name}
            Target: ₹{float(goal.target_amount):,.2f}
            Current: ₹{float(goal.current_amount):,.2f}
            Progress: {progress:.1f}%
            Timeframe: {goal.timeframe} months
            Priority: {goal.priority}/5
            Category: {goal.category}
            ---
            """
        
        prompt = f"""
        As a financial advisor, analyze these investment goals and provide recommendations:
        
        {goal_summary}
        
        Provide:
        1. Priority order for these goals
        2. Suggested monthly contribution for each
        3. Any allocation adjustments needed
        4. Overall strategy for achieving all goals
        
        Keep it concise and actionable.
        """
        
        try:
            response = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "You are a professional financial advisor specializing in goal-based investing."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            advice = response.choices[0].message.content
            
            # Save AI recommendations
            for goal in goals:
                rec = GoalRecommendation(
                    goal_id=goal.id,
                    type='ai_advice',
                    message=f'AI recommendation for {goal.name}',
                    suggestion=advice[:200]
                )
                db.session.add(rec)
            db.session.commit()
            
            return {
                'success': True,
                'advice': advice,
                'goals_analyzed': len(goals)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}