import os

from dotenv import load_dotenv


# The same call is used in every environment. Locally it loads solvego_ai/.env;
# in production the externally injected environment variables take precedence.
load_dotenv()


class ConfigurationError(RuntimeError):
    pass


def required_environment_variable(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise ConfigurationError(
            f"Required environment variable is missing or empty: {name}"
        )
    return value


def positive_int_environment_variable(name: str, default: str) -> int:
    try:
        value = int(os.getenv(name, default))
    except ValueError as error:
        raise ConfigurationError(
            f"Environment variable must be an integer: {name}"
        ) from error
    if value <= 0:
        raise ConfigurationError(
            f"Environment variable must be positive: {name}"
        )
    return value


def positive_float_environment_variable(name: str, default: str) -> float:
    try:
        value = float(os.getenv(name, default))
    except ValueError as error:
        raise ConfigurationError(
            f"Environment variable must be a number: {name}"
        ) from error
    if value <= 0:
        raise ConfigurationError(
            f"Environment variable must be positive: {name}"
        )
    return value


KATAGO_PATH = os.getenv("KATAGO_PATH", "katago")
MODEL_PATH = os.environ["KATAGO_MODEL_PATH"]
CONFIG_PATH = os.environ["KATAGO_CONFIG_PATH"]

OPENAI_API_KEY = required_environment_variable("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL")
OPENAI_TIMEOUT_SECONDS = positive_float_environment_variable(
    "OPENAI_TIMEOUT_SECONDS", "5"
)
EXPLANATION_TOKEN_SECRET = required_environment_variable(
    "EXPLANATION_TOKEN_SECRET"
)
EXPLANATION_TOKEN_TTL_SECONDS = positive_int_environment_variable(
    "EXPLANATION_TOKEN_TTL_SECONDS", "600"
)
EXPLANATION_PV_MAX_MOVES = positive_int_environment_variable(
    "EXPLANATION_PV_MAX_MOVES", "8"
)
