import os


# Tests use the same explicit environment-variable contract as the application.
# These values are local test fixtures and are never used for external requests.
os.environ.setdefault("OPENAI_API_KEY", "test-api-key")
os.environ.setdefault("OPENAI_MODEL", "test-model")
os.environ.setdefault("EXPLANATION_TOKEN_SECRET", "test-explanation-token-secret")
os.environ.setdefault("OPENAI_TIMEOUT_SECONDS", "15")
os.environ.setdefault("EXPLANATION_TOKEN_TTL_SECONDS", "600")
os.environ.setdefault("EXPLANATION_PV_MAX_MOVES", "8")
os.environ.setdefault("KATAGO_MODEL_PATH", "dummy-model.bin")
os.environ.setdefault("KATAGO_CONFIG_PATH", "dummy-analysis.cfg")
