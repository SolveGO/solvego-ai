import os
from unittest.mock import patch

os.environ.setdefault(
    "KATAGO_MODEL_PATH",
    "dummy-model.bin",
)
os.environ.setdefault(
    "KATAGO_CONFIG_PATH",
    "dummy-analysis.cfg",
)

from app.schemas.analysis import (
    GameMove,
    GameNextMoveRequest,
    Position,
    RecommendRequest,
)
from app.services.analysis_service import (
    game_next_move,
    recommend_position,
)


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


def test_game_next_move_converts_history_and_pass():
    request = GameNextMoveRequest(
        moves=[
            GameMove(
                player="BLACK",
                moveType="PLAY",
                position=Position(x=3, y=15),
            ),
            GameMove(
                player="WHITE",
                moveType="PLAY",
                position=Position(x=15, y=3),
            ),
            GameMove(
                player="BLACK",
                moveType="PASS",
                position=None,
            ),
        ]
    )

    katago_response = {
        "moveInfos": [
            {
                "move": "D16",
                "order": 0,
                "winrate": 0.4,
                "scoreLead": -2.5,
                "visits": 10,
                "pv": ["D16"],
            }
        ]
    }

    with patch(
        "app.services.analysis_service.analyze_with_katago",
        return_value=katago_response,
    ) as mock_analyze:
        result = game_next_move(request)

    query = mock_analyze.call_args.args[0]

    assert query["initialPlayer"] == "B"
    assert query["initialStones"] == []
    assert query["moves"] == [
        ["B", "D4"],
        ["W", "Q16"],
        ["B", "pass"],
    ]
    assert query["analyzeTurns"] == [3]
    assert query["maxVisits"] == 5

    # 다음 차례는 WHITE이므로 WHITE 관점으로 변환
    assert result["moveType"] == "PLAY"
    assert result["move"] == Position(x=3, y=3)
    assert result["winRate"] == 0.6
    assert result["scoreLead"] == 2.5
    assert result["candidates"][0]["id"] == "c1"
    assert result["candidates"][0]["rank"] == 1
    assert result["candidates"][0]["moveType"] == "PLAY"
    assert result["candidates"][0]["winRate"] == 0.6
    assert result["candidates"][0]["scoreLead"] == 2.5
    assert result["evidenceToken"]


def test_game_next_move_when_katago_returns_pass():
    request = GameNextMoveRequest(
        moves=[
            GameMove(
                player="BLACK",
                moveType="PLAY",
                position=Position(x=3, y=15),
            ),
        ]
    )

    katago_response = {
        "moveInfos": [
            {
                "move": "pass",
                "order": 0,
                "winrate": 0.2,
                "scoreLead": -10.5,
                "visits": 10,
                "pv": ["pass"],
            }
        ]
    }

    with patch(
        "app.services.analysis_service.analyze_with_katago",
        return_value=katago_response,
    ):
        result = game_next_move(request)

    # 다음 차례는 WHITE
    assert result["moveType"] == "PASS"
    assert result["move"] is None
    assert result["winRate"] == 0.8
    assert result["scoreLead"] == 10.5
    assert result["candidates"][0]["moveType"] == "PASS"
    assert result["candidates"][0]["move"] is None
    assert result["candidates"][0]["winRate"] == 0.8
    assert result["candidates"][0]["scoreLead"] == 10.5


def test_game_next_move_sorts_and_limits_candidates():
    request = GameNextMoveRequest(moves=[])
    move_infos = [
        {
            "move": move,
            "order": order,
            "winrate": 0.5 + order / 100,
            "scoreLead": float(order),
            "visits": 5 - order,
            "pv": [move],
        }
        for move, order in [("D4", 2), ("Q16", 0), ("D16", 1), ("Q4", 3)]
    ]
    with patch(
        "app.services.analysis_service.analyze_with_katago",
        return_value={"moveInfos": move_infos},
    ) as mock_analyze:
        result = game_next_move(request)

    assert mock_analyze.call_count == 1
    assert [candidate["rank"] for candidate in result["candidates"]] == [1, 2, 3]
    assert [candidate["move"] for candidate in result["candidates"]] == [
        Position(x=15, y=3), Position(x=3, y=3), Position(x=3, y=15)
    ]
    assert result["move"] == result["candidates"][0]["move"]


def test_game_next_move_returns_only_available_candidates():
    request = GameNextMoveRequest(moves=[])
    with patch(
        "app.services.analysis_service.analyze_with_katago",
        return_value={
            "moveInfos": [
                {
                    "move": "D4", "order": 0, "winrate": 0.6,
                    "scoreLead": 1.0, "visits": 5, "pv": ["D4"]
                },
                {
                    "move": "Q16", "order": 1, "winrate": 0.5,
                    "scoreLead": 0.0, "visits": 0, "pv": ["Q16"]
                },
            ]
        },
    ):
        result = game_next_move(request)

    assert len(result["candidates"]) == 2
