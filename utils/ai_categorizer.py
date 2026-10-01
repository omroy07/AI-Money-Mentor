"""Fast, explainable categorization for short expense descriptions."""

import re
import unicodedata
from dataclasses import dataclass
from typing import Any


CATEGORIES = (
    "Food",
    "Transport",
    "Shopping",
    "Bills",
    "Entertainment",
    "Healthcare",
    "Education",
    "Investments",
    "Other",
)


@dataclass(frozen=True)
class _Rule:
    category: str
    subcategory: str
    confidence: float
    phrases: tuple[str, ...]


# Confidence is an evidence-strength score, not a statistically calibrated probability.
_RULES = (
    _Rule("Food", "Food Delivery", 0.97, (
        "zomato", "swiggy", "food delivery", "food order", "takeaway", "takeout",
    )),
    _Rule("Food", "Groceries", 0.95, (
        "bigbasket", "blinkit", "zepto", "instamart", "supermarket", "grocery",
        "groceries", "vegetable", "vegetables", "fruits", "dairy", "kirana", "provisions",
        "किराना", "सब्जी", "सब्ज़ी",
    )),
    _Rule("Food", "Dining", 0.92, (
        "restaurant", "cafe", "coffee", "food court", "canteen", "food", "dining", "lunch", "dinner",
        "breakfast", "bakery", "pizza", "burger", "meal", "eatery", "खाना", "भोजन",
    )),
    _Rule("Transport", "Cab", 0.97, (
        "uber", "ola", "rapido", "cab", "taxi", "auto rickshaw", "rickshaw",
    )),
    _Rule("Transport", "Fuel", 0.95, (
        "petrol", "fuel", "diesel", "cng", "gas station", "fuel station", "charging station",
        "पेट्रोल", "ईंधन",
    )),
    _Rule("Transport", "Public Transit", 0.93, (
        "metro", "bus pass", "bus ticket", "train ticket", "rail ticket", "railway",
        "train", "bus", "parking", "toll", "fastag", "मेट्रो", "बस", "रेल",
    )),
    _Rule("Shopping", "Online Shopping", 0.92, (
        "amazon", "flipkart", "myntra", "online shopping", "online purchase", "ecommerce",
    )),
    _Rule("Shopping", "Clothing", 0.90, (
        "clothing", "clothes", "apparel", "shoes", "footwear", "dress", "jeans", "kurta",
        "saree", "shirt", "jacket", "sneakers",
    )),
    _Rule("Shopping", "Electronics", 0.91, (
        "electronics", "laptop", "headphones", "mobile phone", "smartphone", "tablet", "gadget",
    )),
    _Rule("Shopping", "Shopping", 0.84, (
        "shopping", "purchase", "bought", "mall", "retail store",
    )),
    _Rule("Bills", "Electricity", 0.96, (
        "electricity", "electric bill", "power bill", "utility bill", "बिजली बिल",
    )),
    _Rule("Bills", "Water", 0.94, ("water bill", "water utility", "पानी बिल")),
    _Rule("Bills", "Internet", 0.94, (
        "internet bill", "broadband", "wifi", "wi fi", "internet service", "airtel fiber",
        "jio fiber", "jio airfiber", "fiber internet",
    )),
    _Rule("Bills", "Phone and Recharge", 0.94, (
        "mobile recharge", "phone recharge", "phone bill", "mobile bill", "airtel recharge",
        "jio recharge", "recharge phone", "airtel", "jio", "vodafone", "रिचार्ज",
    )),
    _Rule("Bills", "Gas", 0.92, ("gas bill", "gas cylinder", "lpg bill", "lpg cylinder", "piped gas")),
    _Rule("Bills", "Rent", 0.92, ("rent", "lease payment", "monthly rent", "किराया")),
    _Rule("Entertainment", "Streaming", 0.98, (
        "netflix", "spotify", "amazon prime", "prime video", "disney hotstar", "hotstar",
        "youtube premium", "streaming", "music subscription", "video subscription",
    )),
    _Rule("Entertainment", "Movies and Events", 0.95, (
        "movie ticket", "movie tickets", "cinema", "film ticket", "bookmyshow", "concert",
        "theatre", "theater", "live show",
    )),
    _Rule("Entertainment", "Gaming", 0.94, (
        "gaming", "video game", "playstation", "xbox", "steam", "game pass", "arcade",
    )),
    _Rule("Healthcare", "Pharmacy", 0.96, (
        "pharmacy", "medicine", "medication", "prescription", "chemist", "दवा",
    )),
    _Rule("Healthcare", "Medical Care", 0.95, (
        "hospital", "doctor", "clinic", "medical", "apollo", "dental", "dentist",
        "diagnostic lab", "lab test", "diagnostic", "अस्पताल", "डॉक्टर",
    )),
    _Rule("Education", "Courses", 0.97, (
        "udemy", "coursera", "online course", "course fee", "tuition", "exam fee",
        "exam fees", "certification course", "learning course",
    )),
    _Rule("Education", "School and College", 0.95, (
        "college fees", "college fee", "university fees", "university fee", "school fees",
        "school fee", "college", "university", "school", "education fee", "शिक्षा शुल्क",
    )),
    _Rule("Education", "Study Materials", 0.95, (
        "study materials", "school supplies", "textbook", "textbooks",
    )),
    _Rule("Education", "Education", 0.88, (
        "education", "exam registration", "class fee",
    )),
    _Rule("Investments", "Mutual Funds", 0.98, (
        "mutual fund", "mutual funds", "sip", "systematic investment plan", "index fund",
    )),
    _Rule("Investments", "Stocks and ETFs", 0.96, (
        "stock", "stocks", "share purchase", "shares", "etf", "equity investment",
        "brokerage", "demat", "nps investment",
    )),
    _Rule("Investments", "Investments", 0.91, (
        "investment", "investments", "invested", "securities purchase",
    )),
)

_MAX_DESCRIPTION_LENGTH = 2000
_AMOUNT_PATTERN = re.compile(r"\d[\d,]*(?:\.\d+)?")
_NON_WORD_PATTERN = re.compile(r"[^\w]+", flags=re.UNICODE)


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    text = unicodedata.normalize("NFKC", value[:_MAX_DESCRIPTION_LENGTH]).casefold()
    text = text.replace("&", " and ")
    text = re.sub(r"(?:₹|\brs\.?\b|\binr\b|\brupees?\b|रुपये|रु)", " ", text)
    text = _AMOUNT_PATTERN.sub(" ", text)
    return " ".join(_NON_WORD_PATTERN.sub(" ", text).split())


def _contains_phrase(text: str, phrase: str) -> bool:
    normalized_phrase = _normalize(phrase)
    return bool(normalized_phrase) and f" {normalized_phrase} " in f" {text} "


def _fallback(confidence: float = 0.15) -> dict[str, Any]:
    return {"category": "Other", "subcategory": None, "confidence": confidence}


class AICategorizer:
    """Classify descriptions with maintainable rules and conservative confidence."""

    def categorize(self, description: Any) -> dict[str, Any]:
        text = _normalize(description)
        if not text:
            return _fallback()

        matches = []
        for rule in _RULES:
            for phrase in rule.phrases:
                normalized_phrase = _normalize(phrase)
                if _contains_phrase(text, normalized_phrase):
                    matches.append((rule, normalized_phrase))

        if not matches:
            return _fallback()

        # Prefer specific phrases over contained generic words, e.g. Amazon Prime.
        specific_matches = [
            match
            for match in matches
            if not any(
                match[1] != other[1]
                and f" {match[1]} " in f" {other[1]} "
                and len(other[1].split()) > len(match[1].split())
                for other in matches
            )
        ]

        category_matches: dict[str, _Rule] = {}
        for rule, _phrase in specific_matches:
            current = category_matches.get(rule.category)
            if current is None or rule.confidence > current.confidence:
                category_matches[rule.category] = rule

        ranked = sorted(category_matches.values(), key=lambda rule: rule.confidence, reverse=True)
        if len(ranked) > 1 and ranked[0].confidence - ranked[1].confidence < 0.08:
            return _fallback(0.25)

        best = ranked[0]
        return {
            "category": best.category,
            "subcategory": best.subcategory,
            "confidence": best.confidence,
        }