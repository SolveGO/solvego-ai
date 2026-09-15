from app.llm.client import INSTRUCTIONS, OUTPUT_SCHEMA


def test_llm_contract_prioritizes_hedged_go_interpretation():
    assert "현재 바둑판" in INSTRUCTIONS
    assert "승률·집 차이를 문장으로 반복하지 마세요" in INSTRUCTIONS
    assert "의도로 볼 수 있습니다" in INSTRUCTIONS
    assert "후보 순위" in INSTRUCTIONS
    assert "maxVisits=5" not in INSTRUCTIONS
    assert OUTPUT_SCHEMA["additionalProperties"] is False
