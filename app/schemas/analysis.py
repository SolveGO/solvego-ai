from typing import Literal

from pydantic import BaseModel


class Position(BaseModel):
    x: int
    y: int


class RecommendRequest(BaseModel):
    blackStones: list[Position]
    whiteStones: list[Position]
    nextPlayer: Literal["BLACK", "WHITE"]


class RecommendResponse(BaseModel):
    bestMove: Position
    bestWinRate: float


class AnalyzeRequest(BaseModel):
    blackStones: list[Position]
    whiteStones: list[Position]
    nextPlayer: Literal["BLACK", "WHITE"]
    selectedPosition: Position


class AnalyzeResponse(BaseModel):
    bestMove: Position
    selectedMove: Position
    bestWinRate: float
    selectedWinRate: float
    winRateLoss: float