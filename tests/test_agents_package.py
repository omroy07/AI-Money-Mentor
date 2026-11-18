import importlib
import os


def test_agents_package_has_real_init_file():
    # A file named _init_.py (single underscores) is not an __init__.py, so the folder
    # was only importable as a namespace package.
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    agents_dir = os.path.join(here, "utils", "agents")
    assert os.path.isfile(os.path.join(agents_dir, "__init__.py"))
    assert not os.path.exists(os.path.join(agents_dir, "_init_.py"))


def test_agents_package_exports_every_agent():
    pkg = importlib.import_module("utils.agents")
    assert pkg.__file__ is not None
    for name in ("BaseAgent", "TaxAgent", "InvestmentAgent", "DebtAgent", "InsuranceAgent", "PortfolioAgent"):
        assert hasattr(pkg, name), name
