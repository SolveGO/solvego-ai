import logging

from app.llm.client import request_explanation
from app.schemas.analysis import GameCandidateMove
from app.schemas.explanation import ExplanationText
from app.services.evidence_service import verify_evidence_token


OVERCONFIDENT_REPLACEMENTS = {
    "반드시 죽습니다": "위태로워질 가능성이 있습니다",
    "반드시 잡힙니다": "잡힐 가능성이 있습니다",
    "반드시 이깁니다": "유리하게 이어갈 가능성이 있습니다",
    "무조건 정답입니다": "좋은 선택으로 볼 수 있습니다",
    "강제 수순입니다": "가능한 진행의 한 예로 볼 수 있습니다",
}
LIMITATION_TEXT = "AI 해설은 현재 판을 바탕으로 한 해석이며 실제 의도와 다를 수 있습니다."
logger = logging.getLogger(__name__)


def build_template(candidates: list[GameCandidateMove]) -> ExplanationText:
    best = candidates[0]
    return ExplanationText(
        summary="이번 수의 AI 해설을 불러오지 못했습니다.",
        comparison="",
        pvExplanation="",
        limitation="잠시 후 다시 시도해주세요.",
        evidenceRefs=[best.id],
    )


def _soften_overconfident_language(text: str) -> str:
    for original, replacement in OVERCONFIDENT_REPLACEMENTS.items():
        text = text.replace(original, replacement)
    return text


def _validate_llm_output(
    output: dict,
    candidate_ids: set[str],
    selected_candidate_id: str,
) -> ExplanationText:
    explanation = ExplanationText.model_validate(output)
    refs = set(explanation.evidenceRefs)
    if (not refs or len(refs) != len(explanation.evidenceRefs)
            or not refs.issubset(candidate_ids)
            or selected_candidate_id not in refs):
        raise ValueError("Unknown evidence reference")
    return explanation.model_copy(update={
        "summary": _soften_overconfident_language(explanation.summary),
        "comparison": _soften_overconfident_language(explanation.comparison),
        "pvExplanation": _soften_overconfident_language(
            explanation.pvExplanation
        ),
        "limitation": LIMITATION_TEXT,
    })


def explain(evidence_token: str) -> dict:
    evidence = verify_evidence_token(evidence_token)
    candidates = [GameCandidateMove.model_validate(item) for item in evidence["candidates"]]
    source = "LLM"
    try:
        llm_input = {
            "task": "현재 판을 읽고 KataGo가 선택한 수의 바둑적 의미를 설명하세요.",
            "perspective": evidence["perspective"],
            "selectedCandidate": evidence["candidates"][0],
            "candidates": evidence["candidates"],
            "boardState": evidence.get("boardState"),
            "limitations": evidence["limitations"],
        }
        explanation = _validate_llm_output(
            request_explanation(llm_input),
            {candidate.id for candidate in candidates},
            candidates[0].id,
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
