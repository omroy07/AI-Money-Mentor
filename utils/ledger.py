"""
Core Banking Simulator - Double-Entry Ledger System
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from sqlalchemy import and_
from flask import current_app

from models import db, Account, Transaction, LedgerEntry


class LedgerSystem:
    """
    Core Banking Ledger System with Double-Entry Accounting
    """
    
    @staticmethod
    def create_account(user_id: int, account_type: str, account_name: str, initial_balance: float = 0.0) -> Account:
        """
        Create a new bank account
        
        Args:
            user_id: User ID
            account_type: savings, current, investment, wallet
            account_name: Friendly name for the account
            initial_balance: Starting balance
            
        Returns:
            Account object
        """
        account = Account(
            user_id=user_id,
            account_type=account_type,
            account_name=account_name,
            balance=Decimal(str(initial_balance))
        )
        db.session.add(account)
        db.session.commit()
        
        # If initial balance > 0, create a deposit transaction
        if initial_balance > 0:
            LedgerSystem.deposit(account.id, initial_balance, "Initial deposit")
        
        return account
    
    @staticmethod
    def get_account(account_id: int) -> Optional[Account]:
        """Get account by ID"""
        return Account.query.get(account_id)
    
    @staticmethod
    def get_user_accounts(user_id: int) -> List[Account]:
        """Get all accounts for a user"""
        return Account.query.filter_by(user_id=user_id, is_active=True).all()
    
    @staticmethod
    def get_balance(account_id: int) -> float:
        """Get current balance of an account"""
        account = Account.query.get(account_id)
        if not account:
            raise ValueError(f"Account {account_id} not found")
        return float(account.balance)
    
    @staticmethod
    def transfer(from_account_id: int, to_account_id: int, amount: float, description: str = "") -> Dict:
        """
        Transfer money between accounts - Atomic transaction
        
        Args:
            from_account_id: Source account ID
            to_account_id: Destination account ID
            amount: Amount to transfer
            description: Description of the transaction
            
        Returns:
            Dict with transaction details
            
        Raises:
            ValueError: If insufficient balance or invalid accounts
        """
        if amount <= 0:
            raise ValueError("Amount must be greater than 0")
        
        if from_account_id == to_account_id:
            raise ValueError("Cannot transfer to the same account")
        
        # Get accounts
        from_account = Account.query.get(from_account_id)
        to_account = Account.query.get(to_account_id)
        
        if not from_account or not to_account:
            raise ValueError("One or both accounts not found")
        
        if not from_account.is_active or not to_account.is_active:
            raise ValueError("One or both accounts are inactive")
        
        # Check balance
        if float(from_account.balance) < amount:
            raise ValueError(f"Insufficient balance. Available: {from_account.balance}, Required: {amount}")
        
        # Generate reference ID
        reference_id = f"TXN-{uuid.uuid4().hex[:12].upper()}"
        
        try:
            # Create transaction
            transaction = Transaction(
                reference_id=reference_id,
                user_id=from_account.user_id,
                transaction_type='transfer',
                status='PENDING',
                total_amount=Decimal(str(amount)),
                description=description or f"Transfer from {from_account.account_name} to {to_account.account_name}"
            )
            db.session.add(transaction)
            db.session.flush()  # Get transaction ID
            
            # Create ledger entries (Double-entry)
            # 1. DEBIT from source account
            debit_entry = LedgerEntry(
                transaction_id=transaction.id,
                account_id=from_account_id,
                entry_type='DEBIT',
                amount=Decimal(str(amount)),
                description=f"Debit: {description or 'Transfer'}"
            )
            db.session.add(debit_entry)
            
            # 2. CREDIT to destination account
            credit_entry = LedgerEntry(
                transaction_id=transaction.id,
                account_id=to_account_id,
                entry_type='CREDIT',
                amount=Decimal(str(amount)),
                description=f"Credit: {description or 'Transfer'}"
            )
            db.session.add(credit_entry)
            
            # Update balances
            from_account.balance = Decimal(str(from_account.balance)) - Decimal(str(amount))
            to_account.balance = Decimal(str(to_account.balance)) + Decimal(str(amount))
            
            # Mark transaction as completed
            transaction.status = 'COMPLETED'
            transaction.completed_at = datetime.utcnow()
            
            db.session.commit()
            
            return {
                'success': True,
                'transaction_id': transaction.id,
                'reference_id': reference_id,
                'status': 'COMPLETED',
                'amount': amount,
                'from_account': from_account.account_name,
                'to_account': to_account.account_name,
                'from_balance': float(from_account.balance),
                'to_balance': float(to_account.balance),
                'description': description
            }
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def deposit(account_id: int, amount: float, description: str = "") -> Dict:
        """Deposit money into an account"""
        if amount <= 0:
            raise ValueError("Amount must be greater than 0")
        
        account = Account.query.get(account_id)
        if not account:
            raise ValueError(f"Account {account_id} not found")
        
        reference_id = f"DEP-{uuid.uuid4().hex[:12].upper()}"
        
        try:
            transaction = Transaction(
                reference_id=reference_id,
                user_id=account.user_id,
                transaction_type='deposit',
                status='PENDING',
                total_amount=Decimal(str(amount)),
                description=description or f"Deposit to {account.account_name}"
            )
            db.session.add(transaction)
            db.session.flush()
            
            # Credit entry
            credit_entry = LedgerEntry(
                transaction_id=transaction.id,
                account_id=account_id,
                entry_type='CREDIT',
                amount=Decimal(str(amount)),
                description=f"Credit: {description or 'Deposit'}"
            )
            db.session.add(credit_entry)
            
            # Update balance
            account.balance = Decimal(str(account.balance)) + Decimal(str(amount))
            
            transaction.status = 'COMPLETED'
            transaction.completed_at = datetime.utcnow()
            
            db.session.commit()
            
            return {
                'success': True,
                'transaction_id': transaction.id,
                'reference_id': reference_id,
                'status': 'COMPLETED',
                'amount': amount,
                'account': account.account_name,
                'new_balance': float(account.balance),
                'description': description
            }
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def withdraw(account_id: int, amount: float, description: str = "") -> Dict:
        """Withdraw money from an account"""
        if amount <= 0:
            raise ValueError("Amount must be greater than 0")
        
        account = Account.query.get(account_id)
        if not account:
            raise ValueError(f"Account {account_id} not found")
        
        if float(account.balance) < amount:
            raise ValueError(f"Insufficient balance. Available: {account.balance}, Required: {amount}")
        
        reference_id = f"WTH-{uuid.uuid4().hex[:12].upper()}"
        
        try:
            transaction = Transaction(
                reference_id=reference_id,
                user_id=account.user_id,
                transaction_type='withdraw',
                status='PENDING',
                total_amount=Decimal(str(amount)),
                description=description or f"Withdrawal from {account.account_name}"
            )
            db.session.add(transaction)
            db.session.flush()
            
            # Debit entry
            debit_entry = LedgerEntry(
                transaction_id=transaction.id,
                account_id=account_id,
                entry_type='DEBIT',
                amount=Decimal(str(amount)),
                description=f"Debit: {description or 'Withdrawal'}"
            )
            db.session.add(debit_entry)
            
            # Update balance
            account.balance = Decimal(str(account.balance)) - Decimal(str(amount))
            
            transaction.status = 'COMPLETED'
            transaction.completed_at = datetime.utcnow()
            
            db.session.commit()
            
            return {
                'success': True,
                'transaction_id': transaction.id,
                'reference_id': reference_id,
                'status': 'COMPLETED',
                'amount': amount,
                'account': account.account_name,
                'new_balance': float(account.balance),
                'description': description
            }
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def get_transaction_history(account_id: int, limit: int = 50) -> List[Dict]:
        """Get transaction history for an account"""
        account = Account.query.get(account_id)
        if not account:
            raise ValueError(f"Account {account_id} not found")
        
      # Fetch all entries oldest-first so we can replay them into a running
        # balance. balance_after must reflect the account's balance
        # immediately after that specific entry, not the account's current
        # (present-day) balance, so we can't just read account.balance here.
        entries = LedgerEntry.query.filter_by(account_id=account_id).order_by(
            LedgerEntry.timestamp.asc()
        ).all()
        
        running_balance = 0.0
        history_with_balance = []
        for entry in entries:
            delta = float(entry.amount) if entry.entry_type == 'CREDIT' else -float(entry.amount)
            running_balance += delta
            history_with_balance.append((entry, running_balance))
        
        # Display most-recent-first, then apply the limit
        history_with_balance.reverse()
        history_with_balance = history_with_balance[:limit]
        
        result = []
        for entry, balance_after in history_with_balance:
            transaction = Transaction.query.get(entry.transaction_id)
            if transaction:
                result.append({
                    'id': entry.id,
                    'transaction_id': transaction.id,
                    'reference_id': transaction.reference_id,
                    'type': entry.entry_type,
                    'amount': float(entry.amount),
                    'description': entry.description or transaction.description,
                    'timestamp': entry.timestamp.isoformat(),
                    'status': transaction.status,
                    'balance_after': round(balance_after, 2)
                })
        
        return result
    
    @staticmethod
    def get_transaction(transaction_id: int) -> Optional[Dict]:
        """Get transaction details by ID"""
        transaction = Transaction.query.get(transaction_id)
        if not transaction:
            return None
        return transaction.to_dict()
    
    @staticmethod
    def reconcile_account(account_id: int) -> Dict:
        """
        Verify that account balance matches ledger entries
        
        Returns:
            Dict with reconciliation results
        """
        account = Account.query.get(account_id)
        if not account:
            raise ValueError(f"Account {account_id} not found")
        
        # Calculate balance from ledger entries
        debit_total = db.session.query(db.func.sum(LedgerEntry.amount)).filter(
            and_(
                LedgerEntry.account_id == account_id,
                LedgerEntry.entry_type == 'DEBIT'
            )
        ).scalar() or 0
        
        credit_total = db.session.query(db.func.sum(LedgerEntry.amount)).filter(
            and_(
                LedgerEntry.account_id == account_id,
                LedgerEntry.entry_type == 'CREDIT'
            )
        ).scalar() or 0
        
        ledger_balance = float(credit_total) - float(debit_total)
        account_balance = float(account.balance)
        
        is_balanced = abs(ledger_balance - account_balance) < 0.001
        
        return {
            'account_id': account_id,
            'account_name': account.account_name,
            'account_balance': account_balance,
            'ledger_balance': ledger_balance,
            'total_debits': float(debit_total),
            'total_credits': float(credit_total),
            'is_balanced': is_balanced,
            'difference': abs(ledger_balance - account_balance)
        }
    
    @staticmethod
    def get_account_summary(user_id: int) -> Dict:
        """Get summary of all accounts for a user"""
        accounts = Account.query.filter_by(user_id=user_id, is_active=True).all()
        
        total_balance = sum(float(a.balance) for a in accounts)
        account_summaries = []
        
        for account in accounts:
            account_summaries.append({
                'id': account.id,
                'name': account.account_name,
                'type': account.account_type,
                'balance': float(account.balance),
                'currency': account.currency
            })
        
        return {
            'total_balance': total_balance,
            'account_count': len(accounts),
            'accounts': account_summaries
        }