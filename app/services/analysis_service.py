from app.katago.client import analyze_with_katago
from app.katago.coordinate import (
    to_katago_coordinate,
    from_katago_coordinate,
)
from app.schemas.analysis import AnalyzeRequest, RecommendRequest


def build_base_query(request) -> tuple[dict, str]:
    initial_stones = []

    for stone in request.blackStones:
        initial_stones.append(
            ["B", to_katago_coordinate(stone)]
        )

    for stone in request.whiteStones:
        initial_stones.append(
            ["W", to_katago_coordinate(stone)]
        )

    player = "B" if request.nextPlayer == "BLACK" else "W"

    query = {
        "initialStones": initial_stones,
        "initialPlayer": player,
        "moves": [],
        "rules": "korean",
        "komi": 6.5,
        "boardXSize": 19,
        "boardYSize": 19,
        "analyzeTurns": [0],
        "maxVisits": 5,
    }

    return query, player


def get_player_winrate(winrate: float, player: str) -> float:
    if player == "B":
        return winrate

    return 1 - winrate


def recommend_position(request: RecommendRequest) -> dict:
    query, player = build_base_query(request)

    result = analyze_with_katago(query)

    best_move_info = min(
        result["moveInfos"],
        key=lambda move: move["order"],
    )

    best_quality = get_player_winrate(
        best_move_info["winrate"],
        player,
    )

    return {
        "bestMove": from_katago_coordinate(
            best_move_info["move"]
        ),
        "bestWinRate": best_quality,
    }


def analyze_position(request: AnalyzeRequest) -> dict:
    query, player = build_base_query(request)

    selected_move = to_katago_coordinate(
        request.selectedPosition
    )

    # 1. 현재 포지션 전체 분석
    result = analyze_with_katago(query)

    # KataGo가 판단한 최선수
    best_move_info = min(
        result["moveInfos"],
        key=lambda move: move["order"],
    )

    # 2. 사용자가 선택한 수가 기존 분석 결과에 있는지 확인
    selected_move_info = None

    for move in result["moveInfos"]:
        if move["move"] == selected_move:
            selected_move_info = move
            break

    # 3. 없다면 사용자가 선택한 수를 강제로 분석
    if selected_move_info is None:
        selected_query = {
            **query,
            "allowMoves": [
                {
                    "player": player,
                    "moves": [selected_move],
                    "untilDepth": 1,
                }
            ],
        }

        selected_result = analyze_with_katago(
            selected_query
        )

        selected_move_info = (
            selected_result["moveInfos"][0]
        )

    # 4. 현재 플레이어 관점으로 승률 변환
    best_quality = get_player_winrate(
        best_move_info["winrate"],
        player,
    )

    selected_quality = get_player_winrate(
        selected_move_info["winrate"],
        player,
    )

    # 5. 최선수 대비 승률 손실
    win_rate_loss = max(
        0.0,
        best_quality - selected_quality,
    )

    return {
        "bestMove": from_katago_coordinate(
            best_move_info["move"]
        ),
        "selectedMove": request.selectedPosition,
        "bestWinRate": best_quality,
        "selectedWinRate": selected_quality,
        "winRateLoss": win_rate_loss,
    }