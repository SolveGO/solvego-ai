import base64
import hashlib
import hmac
import json
import time

from pydantic import ValidationError

from app.config import (
    EXPLANATION_TOKEN_SECRET,
    EXPLANATION_TOKEN_TTL_SECONDS,
)
from app.schemas.analysis import GameCandidateMove, GameMove, Position


class InvalidEvidenceToken(ValueError):
    pass


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def create_evidence_token(
    perspective: str,
    candidates: list[dict],
    board_state: dict | None = None,
) -> str:
    payload = {
        "version": 1,
        "expiresAt": int(time.time()) + EXPLANATION_TOKEN_TTL_SECONDS,
        "perspective": perspective,
        "candidates": candidates,
        "boardState": board_state,
        "limitations": [
            "후보 평가는 제한된 분석량을 바탕으로 하므로 작은 수치 차이를 과도하게 해석하지 않습니다.",
            "PV는 가능한 예상 진행의 한 예이며 강제 수순이 아닙니다.",
            "바둑적 의도는 현재 판과 후보 수를 바탕으로 한 가능성 있는 해석입니다.",
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
    try:
        validated_candidates = [
            GameCandidateMove.model_validate(candidate)
            for candidate in candidates
        ]
    except ValidationError as error:
        raise InvalidEvidenceToken("Invalid evidence candidates") from error
    if any(
        candidate.id != f"c{index}" or candidate.rank != index
        for index, candidate in enumerate(validated_candidates, start=1)
    ):
        raise InvalidEvidenceToken("Invalid evidence candidate ranking")
    board_state = payload.get("boardState")
    if board_state is not None:
        if (
            not isinstance(board_state, dict)
            or board_state.get("boardSize") != 19
            or board_state.get("sideToMove") != payload["perspective"]
            or not isinstance(board_state.get("blackStones"), list)
            or not isinstance(board_state.get("whiteStones"), list)
            or not isinstance(board_state.get("moves"), list)
        ):
            raise InvalidEvidenceToken("Invalid evidence board state")
        try:
            for stone in board_state["blackStones"] + board_state["whiteStones"]:
                position = Position.model_validate(stone)
                if not (0 <= position.x < 19 and 0 <= position.y < 19):
                    raise ValueError("Position is outside the board")
            [GameMove.model_validate(move) for move in board_state["moves"]]
        except (ValidationError, ValueError) as error:
            raise InvalidEvidenceToken("Invalid evidence board state") from error
        diagram = board_state.get("diagram")
        if diagram is not None and (
            not isinstance(diagram, list)
            or len(diagram) != 19
            or any(
                not isinstance(row, str)
                or len(row) != 19
                or not set(row).issubset({".", "X", "O"})
                for row in diagram
            )
        ):
            raise InvalidEvidenceToken("Invalid evidence board diagram")
    return payload
