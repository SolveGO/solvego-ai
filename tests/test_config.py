import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.config import (
    ConfigurationError,
    positive_float_environment_variable,
    positive_int_environment_variable,
    required_environment_variable,
)


@pytest.mark.parametrize("value", [None, "", "   "])
def test_required_environment_variable_rejects_missing_or_empty(monkeypatch, value):
    name = "REQUIRED_TEST_SETTING"
    if value is None:
        monkeypatch.delenv(name, raising=False)
    else:
        monkeypatch.setenv(name, value)

    with pytest.raises(ConfigurationError, match=name):
        required_environment_variable(name)


def test_explanation_defaults_match_environment_contract(monkeypatch):
    monkeypatch.delenv("TEST_TIMEOUT", raising=False)
    monkeypatch.delenv("TEST_TTL", raising=False)

    assert positive_float_environment_variable("TEST_TIMEOUT", "5") == 5
    assert positive_int_environment_variable("TEST_TTL", "600") == 600


@pytest.mark.parametrize("value", ["invalid", "0", "-1"])
def test_numeric_environment_variable_rejects_invalid_value(monkeypatch, value):
    monkeypatch.setenv("TEST_TTL", value)

    with pytest.raises(ConfigurationError, match="TEST_TTL"):
        positive_int_environment_variable("TEST_TTL", "600")


@pytest.mark.parametrize("missing_name", ["OPENAI_API_KEY", "EXPLANATION_TOKEN_SECRET"])
def test_application_import_fails_for_missing_required_secret(missing_name):
    environment = os.environ.copy()
    environment["OPENAI_API_KEY"] = "test-api-key"
    environment["EXPLANATION_TOKEN_SECRET"] = "test-token-secret"
    environment[missing_name] = " "
    project_root = Path(__file__).resolve().parents[1]

    result = subprocess.run(
        [sys.executable, "-c", "import app.config"],
        cwd=project_root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert missing_name in result.stderr
