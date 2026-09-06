import json

from app.katago.client import analyze_with_katago
from app.katago.coordinate import (
    to_katago_coordinate,
    from_katago_coordinate,
)
from app.schemas.analysis import (
    AnalyzeRequest,
    GameNextMoveRequest,
    RecommendRequest,
)


def convert_katago_move(move: str):
    if move.lower() == "pass":
        return None

    return from_katago_coordinate(move)


def get_player_winrate(winrate: float, player: str) -> float:
    if player == "B":
        return winrate

    return 1 - winrate


def get_player_score_lead(score_lead: float, player: str) -> float:
    if player == "B":
        return score_lead

    return -score_lead


def convert_candidate(move_info: dict, player: str) -> dict:
    return {
        "move": convert_katago_move(move_info["move"]),
        "winRate": get_player_winrate(
            move_info["winrate"],
            player,
        ),
        "scoreLead": get_player_score_lead(
            move_info["scoreLead"],
            player,
        ),
        "visits": move_info["visits"],
        "pv": [
            convert_katago_move(move)
            for move in move_info["pv"]
        ],
    }


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


def build_game_query(request: GameNextMoveRequest) -> tuple[dict, str]:
    moves = []

    for move in request.moves:
        player = "B" if move.player == "BLACK" else "W"

        if move.position is None:
            coordinate = "pass"
        else:
            coordinate = to_katago_coordinate(
                move.position
            )

        moves.append([player, coordinate])

    # 흑부터 시작하므로, 현재까지 둔 수를 기준으로 다음 차례 계산
    player = "B" if len(request.moves) % 2 == 0 else "W"

    query = {
        "initialStones": [],
        "initialPlayer": "B",
        "moves": moves,
        "rules": "korean",
        "komi": 6.5,
        "boardXSize": 19,
        "boardYSize": 19,
        "analyzeTurns": [len(moves)],
        "maxVisits": 5,
    }

    return query, player


def recommend_position(request: RecommendRequest) -> dict:
    query, player = build_base_query(request)

    result = analyze_with_katago(query)

    print(json.dumps(result, indent=2))

    best_move_info = min(
        result["moveInfos"],
        key=lambda move: move["order"],
    )

    best_quality = get_player_winrate(
        best_move_info["winrate"],
        player,
    )

    best_score_lead = get_player_score_lead(
        best_move_info["scoreLead"],
        player,
    )

    candidates = [
        convert_candidate(move_info, player)
        for move_info in result["moveInfos"][:3]
    ]

    return {
        "bestMove": convert_katago_move(
            best_move_info["move"]
        ),
        "bestWinRate": best_quality,
        "scoreLead": best_score_lead,
        "candidates": candidates,
    }


def analyze_position(request: AnalyzeRequest) -> dict:
    query, player = build_base_query(request)

    selected_move = to_katago_coordinate(
        request.selectedPosition
    )

    # 1. 현재 포지션 전체 분석
    result = analyze_with_katago(query)

    print(json.dumps(result, indent=2))

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

    # 6. 현재 플레이어 관점으로 예상 집 차이 변환
    best_score_lead = get_player_score_lead(
        best_move_info["scoreLead"],
        player,
    )

    # 7. KataGo 후보 중 상위 3개만 반환
    candidates = [
        convert_candidate(move_info, player)
        for move_info in result["moveInfos"][:3]
    ]

    return {
        "bestMove": convert_katago_move(
            best_move_info["move"]
        ),
        "selectedMove": request.selectedPosition,
        "bestWinRate": best_quality,
        "selectedWinRate": selected_quality,
        "winRateLoss": win_rate_loss,
        "scoreLead": best_score_lead,
        "candidates": candidates,
    }


def game_next_move(request: GameNextMoveRequest) -> dict:
    query, player = build_game_query(request)

    result = analyze_with_katago(query)

    print(json.dumps(result, indent=2))

    best_move_info = min(
        result["moveInfos"],
        key=lambda move: move["order"],
    )

    return {
        "move": convert_katago_move(
            best_move_info["move"]
        ),
        "winRate": get_player_winrate(
            best_move_info["winrate"],
            player,
        ),
        "scoreLead": get_player_score_lead(
            best_move_info["scoreLead"],
            player,
        ),
    }