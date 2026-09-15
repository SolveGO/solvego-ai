import re
import logging

from app.llm.client import request_explanation
from app.schemas.analysis import GameCandidateMove
from app.schemas.explanation import ExplanationText
from app.services.evidence_service import verify_evidence_token


FORBIDDEN_TACTICAL_TERMS = {
    "축", "사활", "포획", "잡", "연결", "선수", "영토", "확정", "강제"
}
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
    comparisons = [
        f"{_label(candidate.rank)} 후보 {_position(candidate)}는 "
        f"예상 승률 {candidate.winRate * 100:.1f}%, "
        f"예상 집 차이 {candidate.scoreLead:+.1f}집입니다."
        for candidate in candidates
    ]
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
        comparison=" ".join(comparisons),
        pvExplanation=(
            f"A 후보의 가능한 예상 진행 한 예는 {pv_text}입니다."
            if pv else "A 후보에 제공된 예상 진행이 없습니다."
        ),
        limitation=(
            "maxVisits=5의 낮은 탐색량 결과이므로 확정적인 판단으로 볼 수 없으며, "
            "제공된 데이터만으로 구체적인 전술적 이유는 확인할 수 없습니다."
        ),
        evidenceRefs=[candidate.id for candidate in candidates],
    )


def _validate_llm_output(output: dict, candidate_ids: set[str]) -> ExplanationText:
    explanation = ExplanationText.model_validate(output)
    refs = set(explanation.evidenceRefs)
    if (not refs or len(refs) != len(explanation.evidenceRefs)
            or not refs.issubset(candidate_ids)):
        raise ValueError("Unknown evidence reference")
    combined = " ".join([
        explanation.summary,
        explanation.comparison,
        explanation.pvExplanation,
        explanation.limitation,
    ])
    if any(term in combined for term in FORBIDDEN_TACTICAL_TERMS):
        raise ValueError("Unsupported tactical claim")
    if re.search(r"\d", combined):
        raise ValueError("Unverified numeric claim")
    return explanation


def explain(evidence_token: str) -> dict:
    evidence = verify_evidence_token(evidence_token)
    candidates = [GameCandidateMove.model_validate(item) for item in evidence["candidates"]]
    source = "LLM"
    try:
        llm_input = {
            "perspective": evidence["perspective"],
            "candidates": evidence["candidates"],
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
