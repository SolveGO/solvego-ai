from app.schemas.analysis import GameMove


BOARD_SIZE = 19


def _neighbors(position: tuple[int, int]) -> list[tuple[int, int]]:
    x, y = position
    return [
        candidate
        for candidate in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))
        if 0 <= candidate[0] < BOARD_SIZE and 0 <= candidate[1] < BOARD_SIZE
    ]


def _group(
    start: tuple[int, int], stones: set[tuple[int, int]]
) -> set[tuple[int, int]]:
    found: set[tuple[int, int]] = set()
    pending = [start]
    while pending:
        current = pending.pop()
        if current in found:
            continue
        found.add(current)
        pending.extend(
            neighbor
            for neighbor in _neighbors(current)
            if neighbor in stones and neighbor not in found
        )
    return found


def _has_liberty(
    group: set[tuple[int, int]], occupied: set[tuple[int, int]]
) -> bool:
    return any(
        neighbor not in occupied
        for stone in group
        for neighbor in _neighbors(stone)
    )


def build_board_state(moves: list[GameMove], side_to_move: str) -> dict:
    """Replay a validated game history into signed, LLM-readable position evidence."""
    black: set[tuple[int, int]] = set()
    white: set[tuple[int, int]] = set()

    for move in moves:
        if move.moveType == "PASS" or move.position is None:
            continue

        position = (move.position.x, move.position.y)
        own, opponent = (black, white) if move.player == "BLACK" else (white, black)
        own.add(position)

        for neighbor in _neighbors(position):
            if neighbor not in opponent:
                continue
            opponent_group = _group(neighbor, opponent)
            if not _has_liberty(opponent_group, own | opponent):
                opponent.difference_update(opponent_group)

    diagram = [["." for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
    for x, y in black:
        diagram[y][x] = "X"
    for x, y in white:
        diagram[y][x] = "O"

    return {
        "boardSize": BOARD_SIZE,
        "sideToMove": side_to_move,
        "blackStones": [
            {"x": x, "y": y} for x, y in sorted(black, key=lambda item: (item[1], item[0]))
        ],
        "whiteStones": [
            {"x": x, "y": y} for x, y in sorted(white, key=lambda item: (item[1], item[0]))
        ],
        "diagram": ["".join(row) for row in diagram],
        "moves": [move.model_dump() for move in moves],
    }
