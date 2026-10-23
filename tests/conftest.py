import os
import sys
from types import ModuleType
from unittest.mock import MagicMock


class _MockModule(ModuleType):
    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        fullname = f"{self.__name__}.{name}"
        if fullname not in sys.modules:
            mod = _MockModule(fullname)
            mod.__path__ = []
            sys.modules[fullname] = mod
            setattr(self, name, mod)
        return sys.modules[fullname]

    def __or__(self, other):
        return object

    def __ror__(self, other):
        return object

    def __call__(self, *args, **kwargs):
        return MagicMock()


MOCK_PACKAGES = {
    "pyaudio",
    "pyttsx3",
    "transformers",
    "yfinance",
    "pdfplumber",
    "speech_recognition",
    "gtts",
    "pandas",
    "sklearn",
    "scipy",
    "seaborn",
    "groq",
    "flask_socketio",
    "webauthn",
    "cbor2",
    "joblib",
    "langdetect",
    "pytesseract",
    "pdf2image",
    "PIL",
    "torch",
}


class _MockLoader:
    def __init__(self, fullname):
        self.fullname = fullname

    def create_module(self, spec):
        mod = _MockModule(self.fullname)
        mod.__path__ = []
        return mod

    def exec_module(self, module):
        pass


class _MockFinder:
    def find_spec(self, fullname, path, target=None):
        root_pkg = fullname.split(".")[0]
        if root_pkg in MOCK_PACKAGES:
            from importlib.machinery import ModuleSpec

            return ModuleSpec(fullname, _MockLoader(fullname), is_package=True)
        return None


sys.meta_path.insert(0, _MockFinder())
for name in MOCK_PACKAGES:
    if name not in sys.modules:
        mod = _MockModule(name)
        mod.__path__ = []
        sys.modules[name] = mod

import pytest
from app import app, db
import app as app_module

# Shutdown the background scheduler that app.py starts at module level
try:
    app_module.scheduler.shutdown(wait=False)
except Exception:
    pass
