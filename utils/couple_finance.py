"""
Couple's Finance Planner - Joint Financial Management System
"""

import uuid
import json
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from sqlalchemy import and_, func

from models import db, Couple, SharedGoal, GoalContribution, SplitExpense, CoupleBudget, CoupleTaxPlan, CoupleAlert, User, Expense, Asset, Liability


class CoupleFinanceManager:
    """
    Core Couple Finance Management System
    """
    
    def __init__(self, client=None):
        self.client = client
    
    # ============================================
    # COUPLE MANAGEMENT
    # ============================================
    
    def create_invitation(self, user1_id: int, email: str) -> Dict:
        """
        Create a couple invitation for partner
        
        Args:
            user1_id: Current user ID
            email: Partner's email address
        
        Returns:
            Dict with invitation details
        """
        # Check if user already has an active couple
        existing = Couple.query.filter(
            and_(
                db.or_(Couple.user1_id == user1_id, Couple.user2_id == user1_id),
                Couple.status.in_(['PENDING', 'ACTIVE'])
            )
        ).first()
        
        if existing:
            return {'success': False, 'error': 'You already have an active or pending couple connection'}
        
        # Check if partner exists
        partner = User.query.filter_by(email=email).first()
        if not partner:
            return {'success': False, 'error': 'User with this email not found'}
        
        if partner.id == user1_id:
            return {'success': False, 'error': 'You cannot invite yourself'}
        
        # Generate invitation token
        token = uuid.uuid4().hex + uuid.uuid4().hex[:8]
        expires = datetime.utcnow() + timedelta(days=7)
        
        couple = Couple(
            user1_id=user1_id,
            user2_id=partner.id,
            status='PENDING',
            invitation_token=token,
            invitation_expires=expires
        )
        
        db.session.add(couple)
        db.session.commit()
        
        # Create alert for partner
        inviter = User.query.get(user1_id)
        inviter_name = inviter.username if inviter else "a user"
        alert = CoupleAlert(
            couple_id=couple.id,
            user_id=partner.id,
            type='INVITATION',
            message=f'You have been invited to join a couple by {inviter_name}'
        )
        db.session.add(alert)
        db.session.commit()
        
        return {
            'success': True,
            'couple_id': couple.id,
            'invitation_token': token,
            'expires_at': expires.isoformat(),
            'partner_email': email
        }
    
    def accept_invitation(self, user2_id: int, token: str) -> Dict:
        """
        Accept a couple invitation
        
        Args:
            user2_id: Partner user ID
            token: Invitation token
        
        Returns:
            Dict with status
        """
        couple = Couple.query.filter_by(
            invitation_token=token,
            status='PENDING'
        ).first()
        
        if not couple:
            return {'success': False, 'error': 'Invalid or expired invitation'}
        
        if couple.invitation_expires < datetime.utcnow():
            couple.status = 'EXPIRED'
            db.session.commit()
            return {'success': False, 'error': 'Invitation has expired'}
        
        couple.user2_id = user2_id
        couple.status = 'ACTIVE'
        couple.linked_at = datetime.utcnow()
        couple.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return {
            'success': True,
            'couple_id': couple.id,
            'message': 'Couple linked successfully!'
        }
    
    def get_couple_status(self, user_id: int) -> Dict:
        """
        Get current couple status for a user
        
        Args:
            user_id: User ID
        
        Returns:
            Dict with couple status and details
        """
        couple = Couple.query.filter(
            and_(
                db.or_(Couple.user1_id == user_id, Couple.user2_id == user_id),
                Couple.status.in_(['PENDING', 'ACTIVE'])
            )
        ).first()
        
        if not couple:
            return {
                'success': True,
                'has_couple': False,
                'status': 'SINGLE'
            }
        
        partner_id = couple.user2_id if couple.user1_id == user_id else couple.user1_id
        partner = User.query.get(partner_id) if partner_id else None
        
        return {
            'success': True,
            'has_couple': True,
            'couple_id': couple.id,
            'status': couple.status,
            'partner_id': partner_id,
            'partner_username': partner.username if partner else None,
            'partner_email': partner.email if partner else None,
            'linked_at': couple.linked_at.isoformat() if couple.linked_at else None
        }
    
    def unlink_couple(self, user_id: int) -> Dict:
        """
        Unlink a couple relationship
        
        Args:
            user_id: User ID
        
        Returns:
            Dict with status
        """
        couple = Couple.query.filter(
            and_(
                db.or_(Couple.user1_id == user_id, Couple.user2_id == user_id),
                Couple.status == 'ACTIVE'
            )
        ).first()
        
        if not couple:
            return {'success': False, 'error': 'No active couple found'}
        
        couple.status = 'UNLINKED'
        couple.updated_at = datetime.utcnow()
        db.session.commit()
        
        return {'success': True, 'message': 'Couple unlinked successfully'}
    
    # ============================================
    # SHARED GOALS
    # ============================================
    
    def create_shared_goal(self, couple_id: int, data: Dict) -> Dict:
        """
        Create a shared goal for a couple
        
        Args:
            couple_id: Couple ID
            data: Goal data
        
        Returns:
            Dict with created goal
        """
        goal = SharedGoal(
            couple_id=couple_id,
            name=data.get('name'),
            description=data.get('description', ''),
            target_amount=Decimal(str(data.get('target_amount', 0))),
            current_amount=Decimal(str(data.get('current_amount', 0))),
            deadline=datetime.strptime(data.get('deadline'), '%Y-%m-%d').date() if data.get('deadline') else None,
            priority=data.get('priority', 'MEDIUM'),
            icon=data.get('icon', '🎯')
        )
        
        db.session.add(goal)
        db.session.commit()
        
        return {
            'success': True,
            'goal': goal.to_dict()
        }
    
    def add_goal_contribution(self, user_id: int, goal_id: int, amount: float, note: str = "") -> Dict:
        """
        Add a contribution to a shared goal
        
        Args:
            user_id: User ID
            goal_id: Goal ID
            amount: Contribution amount
            note: Optional note
        
        Returns:
            Dict with updated goal
        """
        goal = SharedGoal.query.get(goal_id)
        if not goal:
            return {'success': False, 'error': 'Goal not found'}
        
        # Check if user is part of the couple
        couple = Couple.query.get(goal.couple_id)
        if not couple or (couple.user1_id != user_id and couple.user2_id != user_id):
            return {'success': False, 'error': 'You are not part of this couple'}
        
        contribution = GoalContribution(
            goal_id=goal_id,
            user_id=user_id,
            amount=Decimal(str(amount)),
            note=note
        )
        
        db.session.add(contribution)
        
        # Update goal current amount
        goal.current_amount = Decimal(str(goal.current_amount)) + Decimal(str(amount))
        
        # Check if goal is completed
        if goal.current_amount >= goal.target_amount:
            goal.status = 'COMPLETED'
            goal.completed_at = datetime.utcnow()
        
        db.session.commit()
        
        return {
            'success': True,
            'goal': goal.to_dict()
        }
    
    def get_shared_goals(self, couple_id: int) -> List[Dict]:
        """
        Get all shared goals for a couple
        
        Args:
            couple_id: Couple ID
        
        Returns:
            List of goals
        """
        goals = SharedGoal.query.filter_by(
            couple_id=couple_id
        ).order_by(SharedGoal.priority.desc(), SharedGoal.created_at.desc()).all()
        
        return [g.to_dict() for g in goals]
    
    # ============================================
    # SPLIT EXPENSES
    # ============================================
    
    def create_split_expense(self, couple_id: int, data: Dict) -> Dict:
        """
        Create a split expense
        
        Args:
            couple_id: Couple ID
            data: Expense data
        
        Returns:
            Dict with created expense
        """
        total = Decimal(str(data.get('total_amount', 0)))
        split_type = data.get('split_type', 'EQUAL')
        
        # Calculate shares based on split type
        user1_share = Decimal('0')
        user2_share = Decimal('0')
        
        if split_type == 'EQUAL':
            user1_share = total / 2
            user2_share = total / 2
        elif split_type == 'PERCENTAGE':
            user1_share = total * Decimal(str(data.get('user1_percent', 50))) / 100
            user2_share = total - user1_share
        elif split_type == 'CUSTOM':
            user1_share = Decimal(str(data.get('user1_share', 0)))
            user2_share = total - user1_share
        
        expense = SplitExpense(
            couple_id=couple_id,
            total_amount=total,
            description=data.get('description'),
            category=data.get('category', 'Other'),
            payer_id=data.get('payer_id'),
            split_type=split_type,
            user1_share=user1_share,
            user2_share=user2_share,
            expense_date=datetime.strptime(data.get('expense_date'), '%Y-%m-%d').date() if data.get('expense_date') else date.today()
        )
        
        db.session.add(expense)
        db.session.commit()
        
        return {
            'success': True,
            'expense': expense.to_dict()
        }
    
    def settle_expense(self, expense_id: int) -> Dict:
        """
        Mark a split expense as settled
        
        Args:
            expense_id: Expense ID
        
        Returns:
            Dict with status
        """
        expense = SplitExpense.query.get(expense_id)
        if not expense:
            return {'success': False, 'error': 'Expense not found'}
        
        expense.settled = True
        expense.settled_at = datetime.utcnow()
        db.session.commit()
        
        return {
            'success': True,
            'message': 'Expense settled successfully'
        }
    
    def get_split_expenses(self, couple_id: int, settled: bool = None) -> List[Dict]:
        """
        Get split expenses for a couple
        
        Args:
            couple_id: Couple ID
            settled: Filter by settled status
        
        Returns:
            List of expenses
        """
        query = SplitExpense.query.filter_by(couple_id=couple_id)
        if settled is not None:
            query = query.filter_by(settled=settled)
        
        expenses = query.order_by(SplitExpense.expense_date.desc()).all()
        return [e.to_dict() for e in expenses]
    
    def get_expense_summary(self, couple_id: int) -> Dict:
        """
        Get expense summary for a couple
        
        Args:
            couple_id: Couple ID
        
        Returns:
            Dict with summary
        """
        couple = Couple.query.get(couple_id)
        if not couple:
            return {'success': False, 'error': 'Couple not found'}
        
        # Get all expenses
        expenses = SplitExpense.query.filter_by(couple_id=couple_id).all()
        
        total_expenses = sum(float(e.total_amount) for e in expenses)
        total_settled = sum(float(e.total_amount) for e in expenses if e.settled)
        total_pending = total_expenses - total_settled
        
        # Calculate who owes whom
        user1_paid = sum(float(e.total_amount) for e in expenses if e.payer_id == couple.user1_id)
        user2_paid = sum(float(e.total_amount) for e in expenses if e.payer_id == couple.user2_id)
        
        user1_share = sum(float(e.user1_share) for e in expenses if e.user1_share)
        user2_share = sum(float(e.user2_share) for e in expenses if e.user2_share)
        
        user1_balance = user1_paid - user1_share
        user2_balance = user2_paid - user2_share
        
        return {
            'success': True,
            'total_expenses': total_expenses,
            'total_settled': total_settled,
            'total_pending': total_pending,
            'user1_paid': user1_paid,
            'user2_paid': user2_paid,
            'user1_share': user1_share,
            'user2_share': user2_share,
            'user1_balance': user1_balance,
            'user2_balance': user2_balance,
            'settlement_status': 'BALANCED' if abs(user1_balance - user2_balance) < 1 else 'UNBALANCED'
        }
    
    # ============================================
    # COUPLE BUDGET
    # ============================================
    
    def create_couple_budget(self, couple_id: int, data: Dict) -> Dict:
        """
        Create a couple budget
        
        Args:
            couple_id: Couple ID
            data: Budget data
        
        Returns:
            Dict with created budget
        """
        budget = CoupleBudget(
            couple_id=couple_id,
            category=data.get('category'),
            combined_limit=Decimal(str(data.get('combined_limit', 0))),
            month=data.get('month', datetime.now().strftime('%Y-%m'))
        )
        
        db.session.add(budget)
        db.session.commit()
        
        return {
            'success': True,
            'budget': budget.to_dict()
        }
    
    def get_couple_budgets(self, couple_id: int, month: str = None) -> List[Dict]:
        """
        Get couple budgets
        
        Args:
            couple_id: Couple ID
            month: Month (YYYY-MM)
        
        Returns:
            List of budgets
        """
        month = month or datetime.now().strftime('%Y-%m')
        budgets = CoupleBudget.query.filter_by(
            couple_id=couple_id,
            month=month
        ).all()
        
        return [b.to_dict() for b in budgets]
    
    def get_budget_status(self, couple_id: int, month: str = None) -> Dict:
        """
        Get budget status with actual spending
        
        Args:
            couple_id: Couple ID
            month: Month (YYYY-MM)
        
        Returns:
            Dict with budget status
        """
        month = month or datetime.now().strftime('%Y-%m')
        budgets = self.get_couple_budgets(couple_id, month)
        
        # Get actual spending from expenses
        expenses = SplitExpense.query.filter(
            and_(
                SplitExpense.couple_id == couple_id,
                db.extract('year', SplitExpense.expense_date) == int(month[:4]),
                db.extract('month', SplitExpense.expense_date) == int(month[5:7])
            )
        ).all()
        
        # Group by category
        spending_by_category = {}
        for expense in expenses:
            category = expense.category
            spending_by_category[category] = spending_by_category.get(category, 0) + float(expense.total_amount)
        
        status = []
        for budget in budgets:
            spent = spending_by_category.get(budget.category, 0)
            status.append({
                'category': budget.category,
                'limit': float(budget.combined_limit),
                'spent': spent,
                'remaining': float(budget.combined_limit) - spent,
                'percentage': round(spent / float(budget.combined_limit) * 100, 2) if float(budget.combined_limit) > 0 else 0
            })
        
        return {
            'success': True,
            'month': month,
            'budgets': status,
            'total_limit': sum(b['limit'] for b in status),
            'total_spent': sum(b['spent'] for b in status)
        }
    
    # ============================================
    # TAX OPTIMIZATION
    # ============================================
    
    def get_tax_optimization(self, couple_id: int, user1_income: float, user2_income: float) -> Dict:
        """
        Get tax optimization suggestions for a couple
        
        Args:
            couple_id: Couple ID
            user1_income: Income of user 1
            user2_income: Income of user 2
        
        Returns:
            Dict with tax suggestions
        """
        # Check if existing plan exists
        plan = CoupleTaxPlan.query.filter_by(couple_id=couple_id).order_by(CoupleTaxPlan.created_at.desc()).first()
        
        if plan and plan.user1_income == user1_income and plan.user2_income == user2_income:
            return {
                'success': True,
                'plan': plan.to_dict()
            }
        
        # Calculate combined tax for different scenarios
        from utils.tax import calculate_tax
        
        # Individual tax calculations
        tax1_old = calculate_tax(user1_income, regime='old')
        tax1_new = calculate_tax(user1_income, regime='new')
        tax2_old = calculate_tax(user2_income, regime='old')
        tax2_new = calculate_tax(user2_income, regime='new')
        
        total_old = tax1_old.get('total_tax', 0) + tax2_old.get('total_tax', 0)
        total_new = tax1_new.get('total_tax', 0) + tax2_new.get('total_tax', 0)
        
        best_regime = 'NEW' if total_new <= total_old else 'OLD'
        savings = abs(total_new - total_old)
        
        # Generate suggestions using AI if available
        suggestions = self._generate_tax_suggestions(user1_income, user2_income, best_regime)
        
        plan = CoupleTaxPlan(
            couple_id=couple_id,
            user1_income=Decimal(str(user1_income)),
            user2_income=Decimal(str(user2_income)),
            regime=best_regime,
            total_tax=Decimal(str(min(total_new, total_old))),
            total_savings=Decimal(str(savings)),
            suggestions=suggestions
        )
        
        db.session.add(plan)
        db.session.commit()
        
        return {
            'success': True,
            'plan': plan.to_dict()
        }
    
    def _generate_tax_suggestions(self, income1: float, income2: float, regime: str) -> str:
        """Generate tax suggestions using AI"""
        if not self.client:
            return self._get_default_suggestions(income1, income2, regime)
        
        prompt = f"""
        As a tax expert, provide tax-saving suggestions for a couple:
        
        Partner 1 Income: ₹{income1:,.2f}
        Partner 2 Income: ₹{income2:,.2f}
        Recommended Regime: {regime}
        
        Provide:
        1. Section 80C investment recommendations (limit ₹1.5L each)
        2. Health insurance (80D) suggestions
        3. Home loan interest (24b) benefits if applicable
        4. HRA optimization tips
        5. Overall tax-saving strategy for the couple
        
        Keep it brief, actionable, and specific to Indian tax laws.
        """
        
        try:
            response = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "You are an expert Indian tax consultant for couples."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            return response.choices[0].message.content
        except:
            return self._get_default_suggestions(income1, income2, regime)
    
    def _get_default_suggestions(self, income1: float, income2: float, regime: str) -> str:
        """Get default tax suggestions"""
        return f"""
        📊 **Tax Optimization Summary for Couple**
        
        💰 **Combined Income:** ₹{income1 + income2:,.2f}
        📋 **Recommended Regime:** {regime}
        
        💡 **Key Recommendations:**
        
        1. **Section 80C (₹1.5L each):**
           - Invest in PPF/ELSS/NPS
           - Consider tax-saving FDs
        
        2. **Health Insurance (80D):**
           - Family floater policy (₹25K limit)
           - Parents health insurance (₹50K for senior citizens)
        
        3. **Home Loan Benefits:**
           - Section 24b: ₹2L interest deduction
           - Section 80C: Principal repayment
        
        4. **HRA Optimization:**
           - Claim HRA if renting
           - Consider joint ownership for tax benefits
        
        5. **Overall Strategy:**
           - Split investments between partners
           - Maximize deductions in higher income partner
           - Review quarterly for optimal tax planning
        """
    
    # ============================================
    # DASHBOARD & SUMMARY
    # ============================================
    
    def get_couple_dashboard(self, user_id: int) -> Dict:
        """
        Get comprehensive couple dashboard
        
        Args:
            user_id: User ID
        
        Returns:
            Dict with dashboard data
        """
        # Get couple status
        status = self.get_couple_status(user_id)
        if not status.get('has_couple'):
            return {
                'success': True,
                'has_couple': False,
                'message': 'You are not currently in a couple'
            }
        
        couple_id = status['couple_id']
        couple = Couple.query.get(couple_id)
        partner_id = couple.user2_id if couple.user1_id == user_id else couple.user1_id
        
        # Get partner info
        partner = User.query.get(partner_id)
        
        # Get shared goals
        goals = self.get_shared_goals(couple_id)
        
        # Get expense summary
        expense_summary = self.get_expense_summary(couple_id)
        
        # Get budget status
        budget_status = self.get_budget_status(couple_id)
        
        # Get combined net worth
        combined_net_worth = self._get_combined_net_worth(couple_id, user_id, partner_id)
        
        # Get tax optimization
        tax_plan = CoupleTaxPlan.query.filter_by(couple_id=couple_id).order_by(CoupleTaxPlan.created_at.desc()).first()
        
        # Get alerts
        alerts = CoupleAlert.query.filter_by(
            couple_id=couple_id,
            user_id=user_id,
            is_read=False
        ).order_by(CoupleAlert.created_at.desc()).limit(5).all()
        
        return {
            'success': True,
            'has_couple': True,
            'couple_id': couple_id,
            'partner': {
                'id': partner.id,
                'username': partner.username,
                'email': partner.email
            },
            'goals': goals,
            'expense_summary': expense_summary,
            'budget_status': budget_status,
            'combined_net_worth': combined_net_worth,
            'tax_plan': tax_plan.to_dict() if tax_plan else None,
            'alerts': [a.to_dict() for a in alerts],
            'alert_count': len(alerts)
        }
    
    def _get_combined_net_worth(self, couple_id: int, user1_id: int, user2_id: int) -> Dict:
        """Get combined net worth of a couple"""
        # Get assets and liabilities for both users
        user1_assets = Asset.query.filter_by(user_id=user1_id).all()
        user1_liabilities = Liability.query.filter_by(user_id=user1_id).all()
        user2_assets = Asset.query.filter_by(user_id=user2_id).all()
        user2_liabilities = Liability.query.filter_by(user_id=user2_id).all()
        
        user1_net = sum(a.amount for a in user1_assets) - sum(l.amount for l in user1_liabilities)
        user2_net = sum(a.amount for a in user2_assets) - sum(l.amount for l in user2_liabilities)
        
        return {
            'user1_net_worth': float(user1_net),
            'user2_net_worth': float(user2_net),
            'combined_net_worth': float(user1_net + user2_net)
        }