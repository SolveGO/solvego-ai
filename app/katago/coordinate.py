from app.schemas.analysis import Position


COLUMNS = "ABCDEFGHJKLMNOPQRST"


def to_katago_coordinate(position: Position) -> str:
    column = COLUMNS[position.x]
    row = 19 - position.y

    return f"{column}{row}"


def from_katago_coordinate(coordinate: str) -> Position:
    column = coordinate[0]
    row = int(coordinate[1:])

    x = COLUMNS.index(column)
    y = 19 - row

    return Position(
        x=x,
        y=y,
    )