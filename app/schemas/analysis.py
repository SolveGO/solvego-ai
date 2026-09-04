from typing import Literal

from pydantic import BaseModel, Field


class Position(BaseModel):
    x: int = Field(ge=0, le=18)
    y: int = Field(ge=0, le=18)


class AnalyzeRequest(BaseModel):
    blackStones: list[Position]
    whiteStones: list[Position]
    nextPlayer: Literal["BLACK", "WHITE"]
    selectedPosition: Position

class AnalyzeResponse(BaseModel):
    bestMove: str
    selectedMove: str
    bestWinRate: float
    selectedWinRate: float
    winRateLoss: float