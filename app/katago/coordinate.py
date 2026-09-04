from app.schemas.analysis import Position


def to_katago_coordinate(position: Position) -> str:
    columns = "ABCDEFGHJKLMNOPQRST"

    column = columns[position.x]
    row = 19 - position.y

    return f"{column}{row}"