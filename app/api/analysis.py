from fastapi import APIRouter, HTTPException

from app.schemas.analysis import (
    AnalyzeRequest,
    AnalyzeResponse,
    GameNextMoveRequest,
    GameNextMoveResponse,
    RecommendRequest,
    RecommendResponse,
)
from app.services.analysis_service import (
    analyze_position,
    game_next_move,
    recommend_position,
)

router = APIRouter()


@router.post("/recommend", response_model=RecommendResponse)
def recommend(request: RecommendRequest):
    try:
        return recommend_position(request)

    except TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="KataGo analysis timed out",
        )


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest):
    try:
        return analyze_position(request)

    except TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="KataGo analysis timed out",
        )


@router.post(
    "/game/next-move",
    response_model=GameNextMoveResponse,
)
def next_game_move(request: GameNextMoveRequest):
    try:
        return game_next_move(request)

    except TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="KataGo analysis timed out",
        )