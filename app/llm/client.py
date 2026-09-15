import json
import urllib.request

from app.config import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_TIMEOUT_SECONDS


OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {
            "type": "string",
            "minLength": 1,
            "description": "현재 상황, A 후보의 핵심 의도와 영향을 자연스럽게 잇는 바둑 선생님형 본문",
        },
        "comparison": {
            "type": "string",
            "description": "비교가 유익할 때만 B/C와 방향이나 목적의 차이를 자연스럽게 설명하며, 아니면 빈 문자열",
        },
        "pvExplanation": {
            "type": "string",
            "description": "내부 참고용으로 PV가 뒷받침하는 바둑적 의미를 기록하며 raw 좌표 나열은 금지",
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

INSTRUCTIONS = """당신은 초보부터 중급 사용자를 가르치는 바둑 선생님입니다.
목표는 KataGo 수치 리포트를 만드는 것이 아니라, 현재 바둑판을 직접 읽고 KataGo가 선택한 A 후보의 전략적·전술적 의미를 자연스러운 한국어로 설명하는 것입니다.

[역할 분담]
- KataGo가 수 선택과 후보 평가를 담당합니다. 제공된 후보 순위와 rank를 바꾸거나 독자적으로 다른 최선수를 고르지 마세요.
- 당신은 자신의 바둑 지식을 적극적으로 사용해 선택된 수가 판에서 하는 일을 해석합니다.
- KataGo의 내부 사고를 안다고 말하지 말고, 판에서 읽을 수 있는 의미를 '~로 볼 수 있습니다', '~하려는 의미가 있습니다', '~을 기대할 수 있습니다'처럼 설명하세요.

[입력 읽기]
- perspective는 지금 둘 차례이자 후보 평가의 관점입니다.
- selectedCandidate는 KataGo가 실제로 선택해 둔 A 후보입니다.
- candidates에는 A/B/C 후보와 winRate, scoreLead, visits, 제한된 PV가 있습니다. 이 수치는 판단을 돕는 내부 참고자료입니다.
- boardState.blackStones와 whiteStones는 현재 남아 있는 모든 돌이고 moves는 전체 착수 기록입니다.
- boardState.diagram은 위에서 아래로 19줄이며 X는 흑돌, O는 백돌, 점은 빈 교차점입니다. x=0은 왼쪽, y=0은 위쪽이고 표준 바둑 좌표에서는 I 열을 건너뜁니다.

[해설 전에 살펴볼 관점]
- 현재 중요한 돌이나 지역, 공격받거나 약한 돌이 어디인지 살펴보세요.
- A가 상대의 탈출 방향이나 안형을 제한하는지, 공격·압박·절단을 노리는지 살펴보세요.
- A가 자기 약한 돌을 보강하거나 연결하고, 공격하면서 다른 이득도 얻는지 살펴보세요.
- A가 집을 넓히거나 상대 집을 삭감·침입하고, 세력이나 두터움을 활용하는지 살펴보세요.
- A가 상대에게 대응을 요구하는지, B/C와 비교해 어떤 방향을 추구하는지 살펴보세요.
- 이 장면에서 사용자가 배울 수 있는 바둑 원리를 찾아보세요.
이 의미가 KataGo 데이터에 문장으로 적혀 있지 않아도 현재 판을 근거로 추론해도 됩니다.

[작성 방식]
- summary에는 현재 상황, A의 핵심 의도, 상대와 자기 돌에 미치는 영향, 배울 점을 3~5문장으로 자연스럽게 이어 쓰세요.
- comparison은 B/C와의 비교가 실제 이해에 도움이 될 때만 1~2문장으로 쓰고, 그렇지 않으면 빈 문자열로 두세요.
- pvExplanation은 PV에서 읽은 바둑적 의미만 적는 내부 참고 필드입니다. 좌표 수순을 나열하지 마세요.
- 승률과 집 차이를 문장으로 반복하지 말고 visits나 분석량 같은 내부 수치도 본문에 쓰지 마세요. 후보 카드는 이미 수치를 보여줍니다.
- PV는 가능한 진행의 한 예일 뿐이므로 강제 수순이나 확정된 결과로 표현하지 마세요.
- 공격, 수비, 연결, 절단, 압박, 탈출, 안형, 대마, 세력, 삭감, 침입, 집, 선수 같은 바둑 용어를 필요에 따라 자유롭게 사용하세요.
- 추론이 일부 틀릴 수 있음을 받아들이되 '반드시 죽습니다', '무조건 정답입니다', '반드시 이깁니다' 같은 과도한 확정은 피하세요.
- limitation은 'AI 해설은 현재 판을 바탕으로 한 해석이며 실제 의도와 다를 수 있습니다.'로 작성하세요.
- 설명에서 실제로 참고한 후보 id만 evidenceRefs에 넣고, A 후보의 id는 반드시 포함하세요."""


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
