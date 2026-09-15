import json
from unittest.mock import patch

from app.llm.client import INSTRUCTIONS, OUTPUT_SCHEMA, request_explanation


def test_llm_contract_prioritizes_hedged_go_interpretation():
    assert "현재 바둑판" in INSTRUCTIONS
    assert "승률과 집 차이를 문장으로 반복하지 말고" in INSTRUCTIONS
    assert "바둑 선생님" in INSTRUCTIONS
    assert "자신의 바둑 지식을 적극적으로 사용" in INSTRUCTIONS
    assert "안형" in INSTRUCTIONS
    assert "후보 순위" in INSTRUCTIONS
    assert "maxVisits=5" not in INSTRUCTIONS
    assert OUTPUT_SCHEMA["additionalProperties"] is False


def test_request_explanation_sends_structured_evidence_and_parses_output():
    llm_output = {
        "summary": "백 대마를 압박하려는 수로 볼 수 있습니다.",
        "comparison": "",
        "pvExplanation": "공격을 이어가는 가능한 진행입니다.",
        "limitation": "AI 해설은 현재 판을 바탕으로 한 해석이며 실제 의도와 다를 수 있습니다.",
        "evidenceRefs": ["c1"],
    }
    api_response = {
        "output": [{
            "type": "message",
            "content": [{"type": "output_text", "text": json.dumps(llm_output)}],
        }]
    }

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps(api_response).encode()

    evidence = {
        "perspective": "BLACK",
        "selectedCandidate": {"id": "c1"},
        "candidates": [{"id": "c1"}],
        "boardState": {"diagram": ["." * 19] * 19},
    }
    with patch("app.llm.client.urllib.request.urlopen", return_value=FakeResponse()) as urlopen:
        result = request_explanation(evidence)

    assert result == llm_output
    request = urlopen.call_args.args[0]
    body = json.loads(request.data)
    assert json.loads(body["input"])["boardState"] == evidence["boardState"]
    assert body["instructions"] == INSTRUCTIONS
    assert body["text"]["format"]["schema"] == OUTPUT_SCHEMA
    assert urlopen.call_args.kwargs["timeout"] == 15
