from fastapi import APIRouter, HTTPException

from app.schemas.analysis import AnalyzeRequest, AnalyzeResponse
from app.services.analysis_service import analyze_position

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest):
    try:
        return analyze_position(request)

    except TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="KataGo analysis timed out",
        )