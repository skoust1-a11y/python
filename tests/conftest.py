"""Root pytest configuration loader.

Delegates fixture/config setup to tests/configTest to mirror app/config style.
"""

pytest_plugins = ["tests.configTest.fixtures"]
