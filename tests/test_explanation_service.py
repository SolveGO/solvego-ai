import urllib.error
from unittest.mock import patch

import pytest

from app.services.evidence_service import (
    InvalidEvidenceToken,
    create_evidence_token,
    verify_evidence_token,
)
from app.services.explanation_service import explain


def candidate(candidate_id="c1", rank=1):
    return {
        "id": candidate_id,
        "rank": rank,
        "moveType": "PLAY",
        "move": {"x": 3, "y": 3},
        "winRate": 0.6,
        "scoreLead": 1.5,
        "visits": 4,
        "pv": [{"x": 3, "y": 3}],
    }


def test_explanation_reuses_signed_evidence_without_katago():
    token = create_evidence_token("BLACK", [candidate()])
    output = {
        "summary": "이번 KataGo 분석에서는 A 후보가 가장 높은 평가를 받았습니다.",
        "comparison": "비교할 다른 후보가 없습니다.",
        "pvExplanation": "PV는 가능한 예상 진행의 한 예입니다.",
        "limitation": "낮은 탐색량의 결과입니다.",
        "evidenceRefs": ["c1"],
    }
    with patch(
        "app.services.explanation_service.request_explanation",
        return_value=output,
    ), patch(
        "app.katago.client.analyze_with_katago"
    ) as katago:
        result = explain(token)

    katago.assert_not_called()
    assert result["source"] == "LLM"
    assert result["explanation"].evidenceRefs == ["c1"]


def test_explanation_falls_back_for_unknown_evidence_reference():
    token = create_evidence_token("BLACK", [candidate()])
    invalid_output = {
        "summary": "A 후보입니다.",
        "comparison": "비교입니다.",
        "pvExplanation": "예상 진행입니다.",
        "limitation": "낮은 탐색량입니다.",
        "evidenceRefs": ["c9"],
    }
    with patch(
        "app.services.explanation_service.request_explanation",
        return_value=invalid_output,
    ):
        result = explain(token)

    assert result["source"] == "TEMPLATE"
    assert result["explanation"].evidenceRefs == ["c1"]


def test_explanation_falls_back_when_llm_fails():
    token = create_evidence_token("WHITE", [candidate()])
    with patch(
        "app.services.explanation_service.request_explanation",
        side_effect=TimeoutError,
    ):
        result = explain(token)

    assert result["source"] == "TEMPLATE"
    assert result["perspective"] == "WHITE"


@pytest.mark.parametrize(
    "llm_failure",
    [
        urllib.error.URLError("API unavailable"),
        {"summary": "schema fields are missing"},
    ],
)
def test_explanation_falls_back_for_api_or_schema_failure(llm_failure):
    token = create_evidence_token("BLACK", [candidate()])
    if isinstance(llm_failure, Exception):
        mocked = patch(
            "app.services.explanation_service.request_explanation",
            side_effect=llm_failure,
        )
    else:
        mocked = patch(
            "app.services.explanation_service.request_explanation",
            return_value=llm_failure,
        )
    with mocked:
        result = explain(token)
    assert result["source"] == "TEMPLATE"


def test_evidence_token_rejects_tampering():
    token = create_evidence_token("BLACK", [candidate()])
    replacement = "A" if token[0] != "A" else "B"
    tampered = replacement + token[1:]
    with pytest.raises(InvalidEvidenceToken):
        verify_evidence_token(tampered)


def test_evidence_token_rejects_expiration():
    with patch("app.services.evidence_service.time.time", return_value=100):
        token = create_evidence_token("BLACK", [candidate()])
    with patch("app.services.evidence_service.time.time", return_value=10_000):
        with pytest.raises(InvalidEvidenceToken):
            verify_evidence_token(token)
