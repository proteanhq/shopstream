"""Guards the pytest warning filters in pyproject.toml (issue #66).

A Protean deprecation must fail the test run. `ProteanDeprecationWarning`
subclasses `DeprecationWarning`, and pytest applies the last matching
`filterwarnings` entry. So the `error::...ProteanDeprecationWarning` entry only
works while it comes after `ignore::DeprecationWarning`. If it is moved ahead
of that entry, or deleted, Protean deprecations are silently hidden again and
no other check notices.

These tests emit warnings inside a normal test body, where pytest has already
applied the configured filters, so they check what the suite actually does.
"""

import warnings

import pytest
from protean.exceptions import ProteanDeprecationWarning


class _SampleProteanDeprecation(ProteanDeprecationWarning):
    """Stands in for a release-specific subclass such as RemovedInProtean10Warning."""


def test_protean_deprecation_warning_raises_under_the_configured_filters():
    with pytest.raises(ProteanDeprecationWarning):
        warnings.warn("old option", ProteanDeprecationWarning, stacklevel=1)


def test_protean_deprecation_subclass_raises_under_the_configured_filters():
    with pytest.raises(_SampleProteanDeprecation):
        warnings.warn("old option", _SampleProteanDeprecation, stacklevel=1)


def test_other_deprecation_warnings_stay_ignored():
    # The blanket ignore still covers third-party deprecations, so only
    # Protean's own warnings fail the run.
    with warnings.catch_warnings(record=True) as caught:
        warnings.warn("third-party deprecation", DeprecationWarning, stacklevel=1)

    assert caught == []
