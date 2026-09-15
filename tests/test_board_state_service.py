from app.schemas.analysis import GameMove, Position
from app.services.board_state_service import build_board_state


def play(player: str, x: int, y: int) -> GameMove:
    return GameMove(
        player=player,
        moveType="PLAY",
        position=Position(x=x, y=y),
    )


def test_build_board_state_includes_full_history_and_pass():
    moves = [
        play("BLACK", 3, 3),
        GameMove(player="WHITE", moveType="PASS", position=None),
    ]

    state = build_board_state(moves, "BLACK")

    assert state["sideToMove"] == "BLACK"
    assert state["blackStones"] == [{"x": 3, "y": 3}]
    assert state["whiteStones"] == []
    assert state["moves"] == [move.model_dump() for move in moves]


def test_build_board_state_removes_captured_stones():
    moves = [
        play("BLACK", 1, 0),
        play("WHITE", 0, 0),
        play("BLACK", 0, 1),
    ]

    state = build_board_state(moves, "WHITE")

    assert state["blackStones"] == [{"x": 1, "y": 0}, {"x": 0, "y": 1}]
    assert state["whiteStones"] == []
