import pytest

pytestmark = [pytest.mark.usefixtures("disable_rate_limit")]