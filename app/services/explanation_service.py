import logging

from app.llm.client import request_explanation
from app.schemas.analysis import GameCandidateMove
from app.schemas.explanation import ExplanationText
from app.services.evidence_service import verify_evidence_token


HEDGED_INTERPRETATION_MARKERS = {
    "볼 수 있습니다",
    "해석할 수 있습니다",
    "가능성이 있습니다",
    "것으로 보입니다",
    "의도로 보입니다",
}
UNSUPPORTED_CERTAINTY_MARKERS = {
    "반드시",
    "무조건",
    "확실히",
    "확정됩니다",
    "강제 수순",
    "죽어 있습니다",
    "잡힙니다",
}
LIMITATION_TEXT = "분석량이 적어 해석에는 오차가 있을 수 있습니다."
logger = logging.getLogger(__name__)
COLUMNS = "ABCDEFGHJKLMNOPQRST"


def _label(rank: int) -> str:
    return chr(ord("A") + rank - 1)


def _position(candidate: GameCandidateMove) -> str:
    if candidate.moveType == "PASS":
        return "PASS"
    return f"{COLUMNS[candidate.move.x]}{19 - candidate.move.y}"


def build_template(candidates: list[GameCandidateMove]) -> ExplanationText:
    best = candidates[0]
    pv = best.pv
    pv_text = " → ".join(
        "PASS" if move is None else f"{COLUMNS[move.x]}{19 - move.y}"
        for move in pv
    )
    return ExplanationText(
        summary=(
            f"이번 KataGo 분석에서는 A 후보 {_position(best)}가 "
            "가장 높은 평가를 받았습니다."
        ),
        comparison=(
            "바둑적 의도를 설명하는 자동 해설을 불러오지 못했습니다. "
            "후보별 수치는 위 카드에서 비교할 수 있습니다."
        ),
        pvExplanation=(
            f"A 후보의 가능한 예상 진행 한 예는 {pv_text}입니다."
            if pv else "A 후보에 제공된 예상 진행이 없습니다."
        ),
        limitation=LIMITATION_TEXT,
        evidenceRefs=[candidate.id for candidate in candidates],
    )


def _validate_llm_output(output: dict, candidate_ids: set[str]) -> ExplanationText:
    explanation = ExplanationText.model_validate(output)
    refs = set(explanation.evidenceRefs)
    if (not refs or len(refs) != len(explanation.evidenceRefs)
            or not refs.issubset(candidate_ids)):
        raise ValueError("Unknown evidence reference")
    narrative = " ".join([
        explanation.summary,
        explanation.comparison,
        explanation.pvExplanation,
    ])
    if not any(marker in narrative for marker in HEDGED_INTERPRETATION_MARKERS):
        raise ValueError("Go interpretation must be expressed as uncertain")
    if any(marker in narrative for marker in UNSUPPORTED_CERTAINTY_MARKERS):
        raise ValueError("Unsupported certain claim")
    return explanation.model_copy(update={"limitation": LIMITATION_TEXT})


def explain(evidence_token: str) -> dict:
    evidence = verify_evidence_token(evidence_token)
    candidates = [GameCandidateMove.model_validate(item) for item in evidence["candidates"]]
    source = "LLM"
    try:
        llm_input = {
            "perspective": evidence["perspective"],
            "candidates": evidence["candidates"],
            "boardState": evidence.get("boardState"),
            "limitations": evidence["limitations"],
        }
        explanation = _validate_llm_output(
            request_explanation(llm_input), {candidate.id for candidate in candidates}
        )
    except Exception as error:
        logger.warning("LLM explanation failed; using template: %s", error)
        source = "TEMPLATE"
        explanation = build_template(candidates)

    return {
        "source": source,
        "perspective": evidence["perspective"],
        "candidates": candidates,
        "explanation": explanation,
    }
