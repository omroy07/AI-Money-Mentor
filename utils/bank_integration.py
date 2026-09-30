"""
Bank Integration System
Secure OAuth2 connection, transaction sync, and categorization
"""

import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import random
import json

from models import db, BankConnection, BankTransaction, FraudAlert, User
from utils.anomaly_detector import AnomalyDetector
from utils.ai_categorizer import AICategorizer


class BankIntegration:
    """
    Bank Integration System with OAuth2 and Transaction Sync
    """
    
    def __init__(self):
        self.providers = {
            'upi': self._get_upi_provider(),
            'netbanking': self._get_netbanking_provider(),
            'card': self._get_card_provider()
        }
        self.anomaly_detector = AnomalyDetector()
        self.categorizer = AICategorizer()
    
    def _get_upi_provider(self):
        return {'name': 'UPI', 'oauth_url': 'https://api.upi.com/oauth', 'scopes': ['transactions', 'balance']}
    
    def _get_netbanking_provider(self):
        return {'name': 'Netbanking', 'oauth_url': 'https://api.netbanking.com/oauth', 'scopes': ['accounts', 'transactions', 'balance']}
    
    def _get_card_provider(self):
        return {'name': 'Card', 'oauth_url': 'https://api.card.com/oauth', 'scopes': ['transactions', 'balance']}
    
    def connect_bank(self, user_id: int, provider: str, credentials: Dict) -> Dict:
        """Connect bank account using OAuth2 flow"""
        if provider not in self.providers:
            return {'success': False, 'error': 'Unsupported provider'}
        
        try:
            access_token = self._generate_token(credentials)
            refresh_token = self._generate_token(credentials, is_refresh=True)
            
            connection = BankConnection(
                user_id=user_id,
                provider=provider,
                account_name=credentials.get('account_name', f'{provider.capitalize()} Account'),
                account_number=credentials.get('account_number', 'XXXX' + str(random.randint(1000, 9999))),
                access_token=access_token,
                refresh_token=refresh_token,
                is_active=True,
                last_sync=datetime.utcnow()
            )
            
            db.session.add(connection)
            db.session.commit()
            
            return {
                'success': True,
                'connection_id': connection.id,
                'message': f'Successfully connected {provider} account',
                'account_name': connection.account_name
            }
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': str(e)}
    
    def _generate_token(self, credentials: Dict, is_refresh: bool = False) -> str:
        """Generate mock OAuth token"""
        salt = str(uuid.uuid4())
        data = f"{credentials.get('account_name', '')}{salt}{datetime.utcnow().isoformat()}"
        token = hashlib.sha256(data.encode()).hexdigest()
        return f"oauth_{'refresh' if is_refresh else 'access'}_{token[:32]}"
    
    def sync_transactions(self, user_id: int, connection_id: int = None) -> Dict:
        """Sync transactions for a user's bank connection"""
        connections = self._get_connections(user_id, connection_id)
        
        if not connections:
            return {'success': False, 'error': 'No active connections found'}
        
        results = []
        total_synced = 0
        total_anomalies = 0
        
        for connection in connections:
            transactions = self._fetch_transactions(connection)
            
            synced_count = 0
            anomaly_count = 0
            
            for tx in transactions:
                existing = BankTransaction.query.filter_by(transaction_id=tx['transaction_id']).first()
                if existing:
                    continue
                
                category = self._categorize_transaction(tx)
                merchant = self._extract_merchant(tx)
                
                bank_tx = BankTransaction(
                    user_id=user_id,
                    connection_id=connection.id,
                    transaction_id=tx['transaction_id'],
                    amount=tx['amount'],
                    currency=tx.get('currency', 'INR'),
                    description=tx.get('description', ''),
                    category=category,
                    merchant=merchant,
                    transaction_date=tx['transaction_date'],
                    posted_date=tx.get('posted_date')
                )
                
                db.session.add(bank_tx)
                synced_count += 1
                
                # Check for anomalies
                anomaly_check = self.anomaly_detector.detect_anomalies([tx], [])
                if anomaly_check:
                    for anomaly in anomaly_check:
                        bank_tx.is_anomaly = True
                        bank_tx.is_flagged = True
                        bank_tx.anomaly_reason = anomaly.get('reason', '')
                        anomaly_count += 1
                        
                        alert = FraudAlert(
                            user_id=user_id,
                            transaction_id=bank_tx.id,
                            alert_type=anomaly.get('type', 'unknown'),
                            severity=anomaly.get('severity', 'medium'),
                            message=anomaly.get('reason', 'Suspicious transaction detected'),
                            is_read=False,
                            is_resolved=False
                        )
                        db.session.add(alert)
            
            connection.last_sync = datetime.utcnow()
            db.session.commit()
            
            results.append({
                'connection_id': connection.id,
                'account_name': connection.account_name,
                'synced': synced_count,
                'anomalies': anomaly_count
            })
            
            total_synced += synced_count
            total_anomalies += anomaly_count
        
        return {
            'success': True,
            'total_synced': total_synced,
            'total_anomalies': total_anomalies,
            'details': results
        }
    
    def _get_connections(self, user_id: int, connection_id: int = None) -> List:
        query = BankConnection.query.filter_by(user_id=user_id, is_active=True)
        if connection_id:
            query = query.filter_by(id=connection_id)
        return query.all()
    
    def _fetch_transactions(self, connection: BankConnection) -> List[Dict]:
        """Fetch transactions from bank (simulated)"""
        transactions = []
        today = datetime.utcnow()
        
        for i in range(random.randint(3, 10)):
            amount = random.randint(100, 50000)
            categories = ['Food', 'Transport', 'Entertainment', 'Shopping', 'Utilities', 'Healthcare', 'Rent', 'Other']
            merchants = ['Amazon', 'Flipkart', 'Swiggy', 'Uber', 'Zomato', 'BigBasket', 'Netflix', 'Reliance']
            
            tx = {
                'transaction_id': f"TX_{uuid.uuid4().hex[:12].upper()}",
                'amount': amount,
                'currency': 'INR',
                'description': f"Transaction from {connection.provider}",
                'category': random.choice(categories),
                'merchant': random.choice(merchants),
                'transaction_date': today - timedelta(days=random.randint(0, 30)),
                'posted_date': today - timedelta(days=random.randint(0, 30))
            }
            transactions.append(tx)
        
        return transactions
    
    def _categorize_transaction(self, transaction: Dict) -> str:
        """Categorize a synced transaction using the shared expense rules."""
        description = transaction.get('description')
        merchant = transaction.get('merchant')
        combined_description = " ".join(
            value for value in (description, merchant) if isinstance(value, str)
        )
        return self.categorizer.categorize(combined_description)["category"]
    
    def _extract_merchant(self, transaction: Dict) -> str:
        """Extract merchant from transaction"""
        if transaction.get('merchant'):
            return transaction['merchant']
        
        description = transaction.get('description', '')
        
        if 'at ' in description.lower():
            parts = description.lower().split('at ')
            if len(parts) > 1:
                return parts[1].split()[0].title()
        
        if 'from ' in description.lower():
            parts = description.lower().split('from ')
            if len(parts) > 1:
                return parts[1].split()[0].title()
        
        return 'Unknown'
    
    def get_anomalies(self, user_id: int, limit: int = 50) -> List[Dict]:
        """Get anomalies for a user"""
        alerts = FraudAlert.query.filter_by(user_id=user_id).order_by(
            FraudAlert.created_at.desc()
        ).limit(limit).all()
        
        return [alert.to_dict() for alert in alerts]
    
    def resolve_alert(self, alert_id: int, user_id: int) -> Dict:
        """Resolve a fraud alert"""
        alert = FraudAlert.query.filter_by(id=alert_id, user_id=user_id).first()
        if not alert:
            return {'success': False, 'error': 'Alert not found'}
        
        alert.is_resolved = True
        alert.resolved_at = datetime.utcnow()
        db.session.commit()
        
        return {'success': True, 'message': 'Alert resolved'}
    
    def get_sync_status(self, user_id: int) -> Dict:
        """Get sync status for all connections"""
        connections = BankConnection.query.filter_by(user_id=user_id, is_active=True).all()
        
        status = []
        for conn in connections:
            transaction_count = BankTransaction.query.filter_by(connection_id=conn.id).count()
            anomaly_count = BankTransaction.query.filter_by(connection_id=conn.id, is_anomaly=True).count()
            
            status.append({
                'connection_id': conn.id,
                'account_name': conn.account_name,
                'provider': conn.provider,
                'last_sync': conn.last_sync.isoformat() if conn.last_sync else None,
                'transaction_count': transaction_count,
                'anomaly_count': anomaly_count
            })
        
        return {
            'success': True,
            'connections': status
        }