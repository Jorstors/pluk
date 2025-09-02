# tests/test_version.py
import re
from pluk import __version__


def test_version_is_semver():
    assert isinstance(__version__, str)
    assert re.match(r"^\d+\.\d+\.\d+$", __version__)
