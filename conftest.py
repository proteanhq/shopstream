"""Pytest setup shared by tests/ and verification/.

The loyalty domain's test reporting store is a SQLite file. Its default path in
domain.toml is fixed, so two test runs on one machine at the same time share it,
and one run's setup and teardown drop the tables the other is using. Each run
gets a file of its own here, before any domain loads its config. A URL already
set in the environment is kept, and subprocesses the tests start inherit it.
"""

import atexit
import os
import shutil
import tempfile

if "TEST_LOYALTY_REPORTING_URL" not in os.environ:
    _run_dir = tempfile.mkdtemp(prefix="shopstream-test-")
    atexit.register(shutil.rmtree, _run_dir, ignore_errors=True)
    os.environ["TEST_LOYALTY_REPORTING_URL"] = f"sqlite:///{_run_dir}/loyalty_reporting.db"
