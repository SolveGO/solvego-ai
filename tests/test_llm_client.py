import json
from unittest.mock import patch

import pytest

from app.llm.client import INSTRUCTIONS, OUTPUT_SCHEMA, request_explanation


class FakeResponse:
    status = 200

    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


def test_llm_contract_prioritizes_hedged_go_interpretation():
    assert "현재 바둑판" in INSTRUCTIONS
    assert "승률과 집 차이를 문장으로 반복하지 말고" in INSTRUCTIONS
    assert "3~5문장으로 짧고 자연스럽게" in INSTRUCTIONS
    assert "같은 의미를 반복하거나 불필요한 부연 설명" in INSTRUCTIONS
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
        "status": "completed",
        "output": [{
            "type": "message",
            "content": [{"type": "output_text", "text": json.dumps(llm_output)}],
        }]
    }

    evidence = {
        "perspective": "BLACK",
        "selectedCandidate": {"id": "c1"},
        "candidates": [{"id": "c1"}],
        "boardState": {"diagram": ["." * 19] * 19},
    }
    with patch(
        "app.llm.client.urllib.request.urlopen",
        return_value=FakeResponse(api_response),
    ) as urlopen:
        result = request_explanation(evidence)

    assert result == llm_output
    request = urlopen.call_args.args[0]
    body = json.loads(request.data)
    assert json.loads(body["input"])["boardState"] == evidence["boardState"]
    assert body["instructions"] == INSTRUCTIONS
    assert body["text"]["format"]["schema"] == OUTPUT_SCHEMA
    assert body["max_output_tokens"] == 1200
    assert body["reasoning"] == {"effort": "low"}
    assert urlopen.call_args.kwargs["timeout"] == 15


def test_request_explanation_reports_incomplete_reason_without_response_content(caplog):
    api_response = {
        "status": "incomplete",
        "incomplete_details": {"reason": "max_output_tokens"},
        "output": [{"type": "reasoning"}],
        "usage": {
            "output_tokens": 500,
            "output_tokens_details": {"reasoning_tokens": 500},
        },
    }
    with patch(
        "app.llm.client.urllib.request.urlopen",
        return_value=FakeResponse(api_response),
    ), caplog.at_level("WARNING"):
        with pytest.raises(ValueError, match="not completed"):
            request_explanation({"privateBoardState": "must-not-be-logged"})

    assert "max_output_tokens" in caplog.text
    assert "'httpStatus': 200" in caplog.text
    assert "'responseStatus': 'incomplete'" in caplog.text
    assert "'outputItemTypes': ['reasoning']" in caplog.text
    assert "'hasOutputText': False" in caplog.text
    assert "'hasStructuredOutput': False" in caplog.text
    assert "'outputTokens': 500" in caplog.text
    assert "'reasoningTokens': 500" in caplog.text
    assert "must-not-be-logged" not in caplog.text


def test_request_explanation_reports_refusal_without_logging_refusal_text(caplog):
    api_response = {
        "status": "completed",
        "output": [{
            "type": "message",
            "content": [{"type": "refusal", "refusal": "private refusal text"}],
        }],
        "usage": {"output_tokens": 12},
    }
    with patch(
        "app.llm.client.urllib.request.urlopen",
        return_value=FakeResponse(api_response),
    ), caplog.at_level("WARNING"):
        with pytest.raises(ValueError, match="structured output"):
            request_explanation({})

    assert "'hasRefusal': True" in caplog.text
    assert "'contentItemTypes': ['refusal']" in caplog.text
    assert "private refusal text" not in caplog.text


def test_request_explanation_accepts_top_level_output_text():
    structured_output = {
        "summary": "해설",
        "comparison": "",
        "pvExplanation": "",
        "limitation": "한계",
        "evidenceRefs": ["c1"],
    }
    api_response = {
        "status": "completed",
        "output_text": json.dumps(structured_output),
        "output": [],
    }
    with patch(
        "app.llm.client.urllib.request.urlopen",
        return_value=FakeResponse(api_response),
    ):
        assert request_explanation({}) == structured_output
