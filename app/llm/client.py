import json
import urllib.request

from app.config import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_TIMEOUT_SECONDS


OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "comparison": {"type": "string"},
        "pvExplanation": {"type": "string"},
        "limitation": {"type": "string"},
        "evidenceRefs": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
        },
    },
    "required": [
        "summary", "comparison", "pvExplanation", "limitation", "evidenceRefs"
    ],
    "additionalProperties": False,
}

INSTRUCTIONS = """당신은 KataGo 분석 결과를 쉬운 한국어로 설명합니다.
이번 근거는 maxVisits=5인 낮은 탐색량 분석입니다. 후보 순위나 좋은 수를 독자적으로 바꾸지 마세요.
승률, 예상 집 차이, visits는 제공된 값만 사용하세요. PV는 가능한 예상 진행의 한 예이며 강제 수순이라고 표현하지 마세요.
근거에 없는 축, 사활, 포획, 연결, 선수, 영토 확정 같은 전술적 이유를 만들지 마세요.
AI의 내부 의도를 안다고 표현하지 말고 '이번 KataGo 분석에서는 A 후보가 가장 높은 평가를 받았습니다'처럼 쓰세요.
visits 수를 높은 신뢰도나 확정적 판단으로 표현하지 마세요. 모든 주장에 사용한 후보 id를 evidenceRefs에 넣으세요.
후보의 좌표나 숫자는 UI가 별도로 표시하므로 설명문에 직접 쓰지 말고 A/B/C 후보명만 사용하세요."""


def request_explanation(evidence: dict) -> dict:
    if not OPENAI_API_KEY or not OPENAI_MODEL:
        raise RuntimeError("LLM is not configured")

    body = {
        "model": OPENAI_MODEL,
        "instructions": INSTRUCTIONS,
        "input": json.dumps(evidence, ensure_ascii=False),
        "max_output_tokens": 500,
        "store": False,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "solvego_move_explanation",
                "strict": True,
                "schema": OUTPUT_SCHEMA,
            }
        },
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=OPENAI_TIMEOUT_SECONDS) as response:
        result = json.loads(response.read())

    for item in result.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                return json.loads(content["text"])
    raise ValueError("LLM response did not contain structured output")
