import json
import urllib.request

from app.config import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_TIMEOUT_SECONDS


OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {
            "type": "string",
            "description": "A 후보의 바둑적 의미를 불확실성 표현과 함께 설명",
        },
        "comparison": {
            "type": "string",
            "description": "B/C가 있으면 A와 방향 및 목적을 비교",
        },
        "pvExplanation": {
            "type": "string",
            "description": "PV를 강제 수순이 아닌 가능한 후속 진행으로 해석",
        },
        "limitation": {
            "type": "string",
            "description": "분석량이 적어 해석에는 오차가 있을 수 있습니다.",
        },
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

INSTRUCTIONS = """당신은 KataGo가 고른 바둑 수의 의미를 현재 바둑판에 비추어 쉬운 한국어로 해석합니다.
KataGo가 수 선택과 평가를 담당하며, 당신은 후보 순위나 좋은 수를 독자적으로 바꾸지 않습니다.
boardState의 현재 흑돌·백돌과 전체 착수 기록, A/B/C 후보, 제한된 PV를 함께 살펴보세요.
좌표는 19줄 바둑판에서 x=0이 왼쪽, y=0이 위쪽이며 표준 바둑 좌표의 I 열은 건너뜁니다.

숫자 요약보다 A 후보가 어느 돌이나 지역에 작용하고 어떤 방향의 공격, 수비, 연결, 압박, 삭감, 확장을 노리는 수로 보이는지 설명하세요.
비교할 후보가 있으면 B/C와 수의 방향이나 목적이 어떻게 달라 보이는지 설명하세요. 승률·집 차이를 문장으로 반복하지 마세요.
전략적·전술적 의미를 추론할 수 있지만 확인된 사실이나 AI의 실제 내부 의도처럼 단정하면 안 됩니다.
'~하려는 의도로 볼 수 있습니다', '~을 노리는 수로 해석할 수 있습니다', '~일 가능성이 있습니다' 같은 불확실성 표현을 summary, comparison, pvExplanation 중 적어도 하나에 반드시 사용하세요.
'AI가 이 이유 때문에 두었다', '반드시', '무조건', '확실히', '죽어 있다', '잡힌다'처럼 확정적으로 표현하지 마세요.

후보 순위는 제공된 rank를 그대로 따르세요. 승률과 예상 집 차이는 제공된 값만 사실로 취급하세요.
PV는 가능한 예상 진행의 한 예이며 강제 수순이라고 표현하지 마세요.
분석량이나 visits 같은 내부 구현 수치는 사용자에게 노출하지 마세요.
limitation은 '분석량이 적어 해석에는 오차가 있을 수 있습니다.'로 작성하세요.
모든 주장에 실제 사용한 후보 id만 evidenceRefs에 넣으세요."""


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
