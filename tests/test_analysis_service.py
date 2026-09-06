from unittest.mock import patch

from app.schemas.analysis import RecommendRequest
from app.services.analysis_service import recommend_position


def test_recommend_position_when_katago_returns_pass():
    request = RecommendRequest(
        blackStones=[],
        whiteStones=[],
        nextPlayer="BLACK",
    )

    katago_response = {
        "moveInfos": [
            {
                "move": "pass",
                "order": 0,
                "winrate": 0.7,
                "scoreLead": 3.5,
                "visits": 10,
                "pv": ["pass"],
            }
        ]
    }

    with patch(
        "app.services.analysis_service.analyze_with_katago",
        return_value=katago_response,
    ):
        result = recommend_position(request)

    assert result["bestMove"] is None
    assert result["bestWinRate"] == 0.7
    assert result["scoreLead"] == 3.5

    assert len(result["candidates"]) == 1

    candidate = result["candidates"][0]

    assert candidate["move"] is None
    assert candidate["winRate"] == 0.7
    assert candidate["scoreLead"] == 3.5
    assert candidate["visits"] == 10
    assert candidate["pv"] == [None]