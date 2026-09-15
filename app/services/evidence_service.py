import base64
import hashlib
import hmac
import json
import time

from app.config import (
    EXPLANATION_TOKEN_SECRET,
    EXPLANATION_TOKEN_TTL_SECONDS,
)


class InvalidEvidenceToken(ValueError):
    pass


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def create_evidence_token(perspective: str, candidates: list[dict]) -> str:
    payload = {
        "version": 1,
        "expiresAt": int(time.time()) + EXPLANATION_TOKEN_TTL_SECONDS,
        "perspective": perspective,
        "candidates": candidates,
        "limitations": [
            "KataGo maxVisits=5의 낮은 탐색량 분석입니다.",
            "PV는 가능한 예상 진행의 한 예이며 강제 수순이 아닙니다.",
            "제공된 데이터만으로 구체적인 전술적 이유를 확인할 수 없습니다.",
        ],
    }
    encoded = _encode(
        json.dumps(
            payload,
            separators=(",", ":"),
            sort_keys=True,
            default=lambda value: value.model_dump(),
        ).encode()
    )
    signature = hmac.new(
        EXPLANATION_TOKEN_SECRET.encode(), encoded.encode(), hashlib.sha256
    ).digest()
    return f"{encoded}.{_encode(signature)}"


def verify_evidence_token(token: str) -> dict:
    try:
        encoded, supplied_signature = token.split(".", 1)
        expected_signature = hmac.new(
            EXPLANATION_TOKEN_SECRET.encode(), encoded.encode(), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(_decode(supplied_signature), expected_signature):
            raise InvalidEvidenceToken("Invalid evidence signature")
        payload = json.loads(_decode(encoded))
    except (ValueError, TypeError, json.JSONDecodeError) as error:
        if isinstance(error, InvalidEvidenceToken):
            raise
        raise InvalidEvidenceToken("Malformed evidence token") from error

    if payload.get("version") != 1 or payload.get("expiresAt", 0) < time.time():
        raise InvalidEvidenceToken("Expired or unsupported evidence token")
    if payload.get("perspective") not in {"BLACK", "WHITE"}:
        raise InvalidEvidenceToken("Invalid evidence perspective")
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not 1 <= len(candidates) <= 3:
        raise InvalidEvidenceToken("Invalid evidence candidates")
    return payload
