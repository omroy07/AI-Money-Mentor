import json
from unittest.mock import Mock
from utils.portfolio_explainer import (
    build_ai_payload,
    template_explanation,
    ai_explanation,
    build_explanation,
    handle_risk_request
)


def test_template_explanation_deterministic():
    # Expected: source is "template" and output is strictly deterministic
    analysis_balanced = {
        "risk_label": "Low",
        "concentration_flags": [],
        "scenarios": [{"name": "equity_crash", "portfolio_change_percent": -5.0}]
    }
    analysis_concentrated = {
        "risk_label": "High",
        "concentration_flags": [{"message": "High concentration"}],
        "scenarios": [{"name": "equity_crash", "portfolio_change_percent": -40.0}]
    }

    res1 = template_explanation(analysis_balanced)
    res2 = template_explanation(analysis_balanced)

    # Expected: Identical across calls
    assert res1 == res2
    # Expected: "template"
    assert res1["source"] == "template"
    assert "summary" in res1
    assert "tips" in res1
    assert "alternatives" in res1

    res_conc = template_explanation(analysis_concentrated)
    assert res_conc["source"] == "template"


def test_build_ai_payload_no_names():
    analysis = {
        "total_value": 1000,
        "weights": {
            "holdings": [{"name": "SECRET_NAME_XYZ", "weight_percent": 100}],
            "asset_classes": {"equity": 100}
        },
        "expected_return_percent": 10,
        "volatility_percent": 15,
        "sharpe_ratio": 0.5,
        "average_correlation": 0.2,
        "risk_score": 50,
        "risk_label": "Moderate",
        "diversification_score": 30,
        "concentration_flags": [{"message": "Flagged", "subject": "SECRET_NAME_XYZ"}],
        "scenarios": [{"name": "crash", "portfolio_change_percent": -20}]
    }

    payload = build_ai_payload(analysis)
    payload_str = json.dumps(payload)

    # Expected: SECRET_NAME_XYZ is absent
    assert "SECRET_NAME_XYZ" not in payload_str


def test_ai_explanation_failures(monkeypatch):
    analysis = {"risk_label": "Low"}

    # Missing key
    monkeypatch.setenv("GROQ_API_KEY", "")
    assert ai_explanation(analysis) is None

    monkeypatch.setenv("GROQ_API_KEY", "YOUR_API_KEY")
    assert ai_explanation(analysis) is None

    monkeypatch.setenv("GROQ_API_KEY", "dummy")

    # GroqError
    from groq import GroqError

    def raise_groq_error(*args, **kwargs):
        raise GroqError("API down")

    class MockGroqError:
        def __init__(self, *args, **kwargs):
            self.chat = Mock()
            self.chat.completions.create.side_effect = raise_groq_error

    monkeypatch.setattr("groq.Groq", MockGroqError)
    assert ai_explanation(analysis) is None

    # Generic Exception
    class MockException:
        def __init__(self, *args, **kwargs):
            self.chat = Mock()
            self.chat.completions.create.side_effect = Exception("Generic")
    monkeypatch.setattr("groq.Groq", MockException)
    assert ai_explanation(analysis) is None

    # Empty Reply
    class MockEmpty:
        def __init__(self, *args, **kwargs):
            self.chat = Mock()
            mock_res = Mock()
            mock_res.choices = [Mock(message=Mock(content=""))]
            self.chat.completions.create.return_value = mock_res
    monkeypatch.setattr("groq.Groq", MockEmpty)
    assert ai_explanation(analysis) is None

    # Invalid JSON
    class MockInvalidJson:
        def __init__(self, *args, **kwargs):
            self.chat = Mock()
            mock_res = Mock()
            mock_res.choices = [Mock(message=Mock(content="not json"))]
            self.chat.completions.create.return_value = mock_res
    monkeypatch.setattr("groq.Groq", MockInvalidJson)
    assert ai_explanation(analysis) is None

    # Missing Summary
    class MockMissingSummary:
        def __init__(self, *args, **kwargs):
            self.chat = Mock()
            mock_res = Mock()
            mock_res.choices = [Mock(message=Mock(content='{"tips": [], "alternatives": []}'))]
            self.chat.completions.create.return_value = mock_res
    monkeypatch.setattr("groq.Groq", MockMissingSummary)
    assert ai_explanation(analysis) is None

    # Tips > 5
    class MockTooManyTips:
        def __init__(self, *args, **kwargs):
            self.chat = Mock()
            mock_res = Mock()
            # 6 tips
            msg = '{"summary": "Valid", "tips": ["1","2","3","4","5","6"], "alternatives": []}'
            mock_res.choices = [Mock(message=Mock(content=msg))]
            self.chat.completions.create.return_value = mock_res
    monkeypatch.setattr("groq.Groq", MockTooManyTips)
    assert ai_explanation(analysis) is None


def test_ai_explanation_success(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "dummy")
    analysis = {"risk_label": "Low"}

    class MockSuccess:
        def __init__(self, *args, **kwargs):
            self.chat = Mock()
            mock_res = Mock()
            mock_res.choices = [Mock(message=Mock(content='{"summary": "Valid", "tips": [], "alternatives": []}'))]
            self.chat.completions.create.return_value = mock_res

    monkeypatch.setattr("groq.Groq", MockSuccess)
    res = ai_explanation(analysis)

    # Expected source is "ai"
    assert res is not None
    assert res["source"] == "ai"


def test_build_explanation(monkeypatch):
    analysis = {"disclaimer": "test dis"}

    # Fallback to template
    monkeypatch.setattr("utils.portfolio_explainer.ai_explanation", lambda x: None)
    res_fail = build_explanation(analysis, use_ai=True)
    # Expected: "template"
    assert res_fail["source"] == "template"
    assert res_fail["disclaimer"] == "test dis"

    # Success AI
    monkeypatch.setattr("utils.portfolio_explainer.ai_explanation", lambda x: {"source": "ai"})
    res_succ = build_explanation(analysis, use_ai=True)
    # Expected: "ai"
    assert res_succ["source"] == "ai"
    assert res_succ["disclaimer"] == "test dis"

    # use_ai=False makes zero Groq calls
    def fail_if_called(*args):
        raise AssertionError("Should not be called")
    monkeypatch.setattr("utils.portfolio_explainer.ai_explanation", fail_if_called)
    res_no_ai = build_explanation(analysis, use_ai=False)
    # Expected: "template"
    assert res_no_ai["source"] == "template"


def test_handle_risk_request(monkeypatch):
    # None input
    # Expected: 400
    res, code = handle_risk_request(None)
    assert code == 400
    assert "error" in res

    # list input
    # Expected: 400
    res, code = handle_risk_request([])
    assert code == 400

    # missing holdings
    # Expected: 400
    res, code = handle_risk_request({"use_ai": True})
    assert code == 400

    # non-boolean use_ai
    # Expected: 400
    res, code = handle_risk_request({"holdings": [], "use_ai": "yes"})
    assert code == 400

    # invalid holding (400 with risk module error)
    monkeypatch.setattr("utils.portfolio_explainer.analyze_portfolio", lambda x: {"error": "bad"})
    res, code = handle_risk_request({"holdings": ["bad"]})
    # Expected: 400
    assert code == 400
    assert res["error"] == "bad"

    # valid portfolio
    monkeypatch.setattr("utils.portfolio_explainer.analyze_portfolio", lambda x: {"disclaimer": "OK"})
    monkeypatch.setattr("utils.portfolio_explainer.build_explanation", lambda a, use_ai: {"source": "mock"})
    res, code = handle_risk_request({"holdings": []})
    # Expected: 200
    assert code == 200
    assert "analysis" in res
    assert "explanation" in res

    # unexpected exception
    def raise_err(x):
        raise Exception("Hidden detail")
    monkeypatch.setattr("utils.portfolio_explainer.analyze_portfolio", raise_err)
    res, code = handle_risk_request({"holdings": []})
    # Expected: 500
    assert code == 500
    assert res["error"] == "Portfolio analysis failed."
    assert "Hidden detail" not in str(res)
