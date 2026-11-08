import os
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def pytest_configure():
    os.environ.setdefault("GEMINI_API_KEY", "test-key")
    os.environ.setdefault("GEMINI_BASE_URL", "https://example.com/v1")
    os.environ.setdefault("GEMINI_MODEL", "gemini-test-model")
