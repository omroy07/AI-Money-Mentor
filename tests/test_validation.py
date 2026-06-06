import sys
import unittest
from unittest.mock import MagicMock, patch

# Mock out external libraries that are not installed before importing app
sys.modules['yfinance'] = MagicMock()
sys.modules['groq'] = MagicMock()
sys.modules['pdfplumber'] = MagicMock()
sys.modules['apscheduler'] = MagicMock()
sys.modules['apscheduler.schedulers'] = MagicMock()
sys.modules['apscheduler.schedulers.background'] = MagicMock()

# Mock flask_sqlalchemy
mock_sqlalchemy = MagicMock()
sys.modules['flask_sqlalchemy'] = mock_sqlalchemy

# Mock the database object
mock_db = MagicMock()
mock_sqlalchemy.SQLAlchemy.return_value = mock_db

# Import validation helpers
from utils.validation import ValidationError, validate_string, validate_float, validate_int
# Import the flask app
from app import app


class TestValidationHelpers(unittest.TestCase):
    """Test cases for the helper validation routines."""

    def test_validate_string(self):
        # Valid string
        self.assertEqual(validate_string("test"), "test")
        self.assertEqual(validate_string("  trimmed  "), "trimmed")
        
        # Missing/None
        with self.assertRaises(ValidationError):
            validate_string(None)
        self.assertIsNone(validate_string(None, allow_none=True))
        
        # Invalid type
        with self.assertRaises(ValidationError):
            validate_string(123)
            
        # Too short
        with self.assertRaises(ValidationError):
            validate_string("", min_length=1)
        with self.assertRaises(ValidationError):
            validate_string("   ", min_length=1)

    def test_validate_float(self):
        # Valid floats
        self.assertEqual(validate_float(10.5), 10.5)
        self.assertEqual(validate_float("10.5"), 10.5)
        self.assertEqual(validate_float(10), 10.0)
        
        # Missing/None
        with self.assertRaises(ValidationError):
            validate_float(None)
        self.assertIsNone(validate_float(None, allow_none=True))
        
        # Invalid types/values
        with self.assertRaises(ValidationError):
            validate_float("not a float")
        with self.assertRaises(ValidationError):
            validate_float(True)  # Booleans rejected
            
        # Min/max boundaries
        self.assertEqual(validate_float(5.0, min_val=5.0), 5.0)
        with self.assertRaises(ValidationError):
            validate_float(4.9, min_val=5.0)
        with self.assertRaises(ValidationError):
            validate_float(10.1, max_val=10.0)

    def test_validate_int(self):
        # Valid ints
        self.assertEqual(validate_int(10), 10)
        self.assertEqual(validate_int("10"), 10)
        self.assertEqual(validate_int(10.0), 10)
        
        # Missing/None
        with self.assertRaises(ValidationError):
            validate_int(None)
        self.assertIsNone(validate_int(None, allow_none=True))
        
        # Invalid types/values
        with self.assertRaises(ValidationError):
            validate_int(5.5)  # Decimal floats rejected
        with self.assertRaises(ValidationError):
            validate_int("not an int")
        with self.assertRaises(ValidationError):
            validate_int(False)  # Booleans rejected
            
        # Min/max boundaries
        self.assertEqual(validate_int(5, min_val=5), 5)
        with self.assertRaises(ValidationError):
            validate_int(4, min_val=5)
        with self.assertRaises(ValidationError):
            validate_int(11, max_val=10)


class TestEndpointValidation(unittest.TestCase):
    """Test cases for Flask endpoints validating request payloads."""

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        
        from models import Expense, Asset, Liability, BudgetLimit, BudgetAlert
        Expense.query = MagicMock()
        Asset.query = MagicMock()
        Liability.query = MagicMock()
        BudgetLimit.query = MagicMock()
        BudgetAlert.query = MagicMock()
        
        Asset.id = MagicMock()
        Liability.id = MagicMock()
        
        Expense.category = MagicMock()
        Expense.date = MagicMock()
        BudgetLimit.category = MagicMock()
        BudgetAlert.category = MagicMock()
        BudgetAlert.year_month = MagicMock()
        BudgetAlert.threshold = MagicMock()
        
        limit_mock = MagicMock()
        limit_mock.limit_amount = 1000.0
        BudgetLimit.query.filter_by.return_value.first.return_value = limit_mock
        
        # Setup mock client responses for tax and chat recommendations
        import sys
        app_module = sys.modules['app']
        app_module.client = MagicMock()
        mock_ai_res = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Mocked AI recommendation."
        mock_ai_res.choices = [mock_choice]
        app_module.client.chat.completions.create.return_value = mock_ai_res

    def test_sip_endpoint(self):
        # Valid payload
        response = self.app.post('/sip', json={
            "monthly": 5000,
            "rate": 12.5,
            "years": 10,
            "inflation": 6.0
        })
        self.assertEqual(response.status_code, 200)

        # Missing monthly
        response = self.app.post('/sip', json={
            "rate": 12.5,
            "years": 10
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("monthly", response.get_json()["message"])

        # Negative years
        response = self.app.post('/sip', json={
            "monthly": 5000,
            "rate": 12.5,
            "years": -1
        })
        self.assertEqual(response.status_code, 400)

        # Invalid type (rate as string that cannot be cast)
        response = self.app.post('/sip', json={
            "monthly": 5000,
            "rate": "invalid",
            "years": 10
        })
        self.assertEqual(response.status_code, 400)

    def test_tax_endpoint(self):
        # Valid payload
        response = self.app.post('/tax', json={
            "income": 1200000,
            "deduction_80c": 150000,
            "deduction_80d": 25000
        })
        self.assertEqual(response.status_code, 200)

        # Missing income
        response = self.app.post('/tax', json={
            "deduction_80c": 150000
        })
        self.assertEqual(response.status_code, 400)

        # Negative deduction
        response = self.app.post('/tax', json={
            "income": 1000000,
            "deduction_80c": -100
        })
        self.assertEqual(response.status_code, 400)

    def test_money_score_endpoint(self):
        # Valid payload
        response = self.app.post('/money-score', json={
            "income": 100000,
            "expenses": 40000,
            "savings": 20000,
            "investments": 15000,
            "debt": 10000,
            "emergency": 50000
        })
        self.assertEqual(response.status_code, 200)

        # Missing fields
        response = self.app.post('/money-score', json={
            "income": 100000,
            "expenses": 40000
        })
        self.assertEqual(response.status_code, 400)

        # Negative savings
        response = self.app.post('/money-score', json={
            "income": 100000,
            "expenses": 40000,
            "savings": -10,
            "investments": 15000,
            "debt": 10000,
            "emergency": 50000
        })
        self.assertEqual(response.status_code, 400)

    @patch('app.get_stock_price')
    def test_portfolio_endpoint(self, mock_get_price):
        mock_get_price.return_value = {"symbol": "AAPL", "price": 150.0}
        
        # Valid symbol
        response = self.app.post('/portfolio', json={"stock": "AAPL"})
        self.assertEqual(response.status_code, 200)

        # Invalid/empty stock symbol
        response = self.app.post('/portfolio', json={"stock": ""})
        self.assertEqual(response.status_code, 400)

        # Error from yfinance wrapper
        mock_get_price.return_value = {"error": "Invalid stock symbol or no data found"}
        response = self.app.post('/portfolio', json={"stock": "INVALID"})
        self.assertEqual(response.status_code, 400)

    def test_add_expense_endpoint(self):
        # Valid payload
        response = self.app.post('/add_expense', json={
            "category": "Food",
            "amount": 25.50,
            "date": "2026-06-06"
        })
        self.assertEqual(response.status_code, 200)

        # Missing category
        response = self.app.post('/add_expense', json={
            "amount": 25.50,
            "date": "2026-06-06"
        })
        self.assertEqual(response.status_code, 400)

        # Non-positive amount
        response = self.app.post('/add_expense', json={
            "category": "Food",
            "amount": 0,
            "date": "2026-06-06"
        })
        self.assertEqual(response.status_code, 400)

    def test_add_asset_endpoint(self):
        response = self.app.post('/add-asset', json={
            "name": "Savings Account",
            "amount": 10000
        })
        self.assertEqual(response.status_code, 200)

        # Negative amount
        response = self.app.post('/add-asset', json={
            "name": "Savings Account",
            "amount": -50
        })
        self.assertEqual(response.status_code, 400)

    def test_add_liability_endpoint(self):
        response = self.app.post('/add-liability', json={
            "name": "Home Loan",
            "amount": 500000
        })
        self.assertEqual(response.status_code, 200)

        # Missing name
        response = self.app.post('/add-liability', json={
            "amount": 500000
        })
        self.assertEqual(response.status_code, 400)

    def test_delete_item_endpoint(self):
        from models import Asset, Liability
        # Setup mock asset and liability queries
        mock_asset = MagicMock()
        Asset.query.get.return_value = mock_asset
        
        mock_liability = MagicMock()
        Liability.query.get.return_value = mock_liability

        # Valid type and id
        response = self.app.post('/delete-item', json={
            "type": "asset",
            "id": 1
        })
        self.assertEqual(response.status_code, 200)

        # Invalid type
        response = self.app.post('/delete-item', json={
            "type": "invalid_type",
            "id": 1
        })
        self.assertEqual(response.status_code, 400)

        # Invalid id (less than 1)
        response = self.app.post('/delete-item', json={
            "type": "asset",
            "id": 0
        })
        self.assertEqual(response.status_code, 400)

        # Item not found (404)
        Asset.query.get.return_value = None
        response = self.app.post('/delete-item', json={
            "type": "asset",
            "id": 10
        })
        self.assertEqual(response.status_code, 404)

    def test_budget_limits_endpoint(self):

        # Valid payload
        response = self.app.post('/budget/limits', json={
            "category": "Food",
            "limit_amount": 500
        })
        self.assertEqual(response.status_code, 200)

        # Missing limit_amount
        response = self.app.post('/budget/limits', json={
            "category": "Food"
        })
        self.assertEqual(response.status_code, 400)

        # Negative limit_amount
        response = self.app.post('/budget/limits', json={
            "category": "Food",
            "limit_amount": -10
        })
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
