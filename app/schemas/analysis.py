from typing import Literal

from pydantic import BaseModel


class Position(BaseModel):
    x: int
    y: int


class CandidateMove(BaseModel):
    move: Position | None
    winRate: float
    scoreLead: float
    visits: int
    pv: list[Position | None]


class GameCandidateMove(CandidateMove):
    id: str
    rank: int
    moveType: Literal["PLAY", "PASS"]


class RecommendRequest(BaseModel):
    blackStones: list[Position]
    whiteStones: list[Position]
    nextPlayer: Literal["BLACK", "WHITE"]


class RecommendResponse(BaseModel):
    bestMove: Position | None
    bestWinRate: float
    scoreLead: float
    candidates: list[CandidateMove]


class AnalyzeRequest(BaseModel):
    blackStones: list[Position]
    whiteStones: list[Position]
    nextPlayer: Literal["BLACK", "WHITE"]
    selectedPosition: Position


class AnalyzeResponse(BaseModel):
    bestMove: Position | None
    selectedMove: Position
    bestWinRate: float
    selectedWinRate: float
    winRateLoss: float
    scoreLead: float
    candidates: list[CandidateMove]


class GameMove(BaseModel):
    player: Literal["BLACK", "WHITE"]
    moveType: Literal["PLAY", "PASS"]
    position: Position | None


class GameNextMoveRequest(BaseModel):
    moves: list[GameMove]


class GameNextMoveResponse(BaseModel):
    moveType: Literal["PLAY", "PASS"]
    move: Position | None
    winRate: float
    scoreLead: float
    candidates: list[GameCandidateMove]
    evidenceToken: str
