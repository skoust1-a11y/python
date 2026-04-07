"""Environment and path bootstrap for test configuration."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv


project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

test_env_file = project_root / ".env.test"
if test_env_file.exists():
    load_dotenv(test_env_file, override=True)
else:
    load_dotenv(project_root / ".env", override=True)

os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["DATABASE_URL"] = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://mohit:mohit007@localhost:5432/wellbeing_coach_test",
)
# postgresql://postgres:mohit007@localhost:5432/llm_queries_db