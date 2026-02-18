import nox

PYTHON_VERSIONS = ["3.11", "3.12", "3.13", "3.14"]

# Packages with C extensions that must be rebuilt per Python version.
# Poetry's wheel cache can serve a .so compiled for the wrong interpreter.
_C_EXT_PACKAGES = ["psycopg2"]


def _install(session: nox.Session) -> None:
    """Install the project with all test extras into the nox virtualenv."""
    session.run(
        "poetry",
        "install",
        "--with",
        "test",
        "--all-extras",
        external=True,
    )
    # Force-rebuild C-extension packages so the .so matches this Python version.
    session.run(
        "pip",
        "install",
        "--force-reinstall",
        "--no-cache-dir",
        *_C_EXT_PACKAGES,
    )


@nox.session(python=PYTHON_VERSIONS)
def tests(session: nox.Session) -> None:
    """Run full test suite across Python versions."""
    _install(session)
    session.run("pytest")


@nox.session(python=PYTHON_VERSIONS)
def tests_domain(session: nox.Session) -> None:
    """Run domain-layer tests only (no infrastructure required)."""
    _install(session)
    session.run(
        "pytest",
        "tests/identity/domain/",
        "tests/catalogue/domain/",
        "tests/ordering/domain/",
    )
