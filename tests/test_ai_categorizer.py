import pytest

from utils.ai_categorizer import AICategorizer, CATEGORIES
from utils.bank_integration import BankIntegration


@pytest.mark.parametrize(
    ("description", "expected_category"),
    [
        ("Spent ₹850 on Zomato", "Food"),
        ("Swiggy order ₹450", "Food"),
        ("Lunch at restaurant ₹700", "Food"),
        ("Groceries ₹2200", "Food"),
        ("Uber ride ₹320", "Transport"),
        ("Petrol ₹2000", "Transport"),
        ("Metro recharge ₹500", "Transport"),
        ("Amazon purchase ₹1299", "Shopping"),
        ("Myntra order ₹2200", "Shopping"),
        ("Bought new shoes ₹3000", "Shopping"),
        ("Electricity bill ₹2400", "Bills"),
        ("Internet bill ₹999", "Bills"),
        ("Mobile recharge ₹299", "Bills"),
        ("Netflix subscription ₹649", "Entertainment"),
        ("Movie tickets ₹800", "Entertainment"),
        ("Spotify ₹119", "Entertainment"),
        ("Apollo hospital ₹5000", "Healthcare"),
        ("Pharmacy ₹850", "Healthcare"),
        ("Doctor consultation ₹700", "Healthcare"),
        ("Udemy course ₹599", "Education"),
        ("College fees ₹25000", "Education"),
        ("Exam fees ₹1000", "Education"),
        ("SIP ₹5000", "Investments"),
        ("Mutual fund investment ₹10000", "Investments"),
        ("Bought stocks ₹15000", "Investments"),
        ("Paid 850 to Zomato", "Food"),
        ("ZOMATO---ORDER Rs. 850", "Food"),
        ("  Uber   ride  320  ", "Transport"),
        ("Airtel fiber monthly bill", "Bills"),
        ("LPG cylinder payment", "Bills"),
        ("Purchased a cotton kurta", "Shopping"),
        ("College semester payment", "Education"),
        ("खाना delivery ₹450", "Food"),
    ],
)
def test_categorizes_supported_descriptions(description, expected_category):
    result = AICategorizer().categorize(description)

    assert result["category"] == expected_category
    assert result["subcategory"]
    assert 0.0 <= result["confidence"] <= 1.0


@pytest.mark.parametrize(
    "description",
    [
        "XYZ Services ₹700",
        "Payment ₹43829",
        "Miscellaneous ₹900",
        "Paid ₹500",
        "Monthly payment",
        "Transfer ₹1500",
        "",
        "   ",
        None,
        123456,
        "123456",
        {"description": "Zomato"},
        "Paid gas ₹500",
    ],
)
def test_unknown_or_malformed_descriptions_fall_back_to_other(description):
    result = AICategorizer().categorize(description)

    assert result == {
        "category": "Other",
        "subcategory": None,
        "confidence": 0.15,
    }


def test_category_vocabulary_is_exactly_the_supported_set():
    assert set(CATEGORIES) == {
        "Food", "Transport", "Shopping", "Bills", "Entertainment",
        "Healthcare", "Education", "Investments", "Other",
    }


def test_specific_longer_phrase_wins_over_contained_merchant():
    result = AICategorizer().categorize("Amazon Prime Video subscription 649")

    assert result["category"] == "Entertainment"
    assert result["subcategory"] == "Streaming"


def test_long_unusual_text_is_bounded_and_safe():
    result = AICategorizer().categorize("x" * 100_000)

    assert result["category"] == "Other"
    assert result["confidence"] == 0.15


@pytest.mark.parametrize(
    ("transaction", "expected_category"),
    [
        ({"description": "Payment", "merchant": "Zomato"}, "Food"),
        ({"description": "", "merchant": "Jio fiber"}, "Bills"),
        ({"description": "Transfer 1234", "merchant": "Unknown"}, "Other"),
    ],
)
def test_bank_sync_uses_shared_categorizer(transaction, expected_category):
    bank_integration = BankIntegration.__new__(BankIntegration)
    bank_integration.categorizer = AICategorizer()

    assert bank_integration._categorize_transaction(transaction) == expected_category