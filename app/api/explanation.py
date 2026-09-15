from fastapi import APIRouter, HTTPException

from app.schemas.explanation import ExplanationRequest, ExplanationResponse
from app.services.evidence_service import InvalidEvidenceToken
from app.services.explanation_service import explain


router = APIRouter()


@router.post("/game/explanation", response_model=ExplanationResponse)
def game_explanation(request: ExplanationRequest):
    try:
        return explain(request.evidenceToken)
    except InvalidEvidenceToken as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
