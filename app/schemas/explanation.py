from typing import Literal

from pydantic import BaseModel

from app.schemas.analysis import GameCandidateMove


class ExplanationRequest(BaseModel):
    evidenceToken: str


class ExplanationText(BaseModel):
    summary: str
    comparison: str
    pvExplanation: str
    limitation: str
    evidenceRefs: list[str]


class ExplanationResponse(BaseModel):
    source: Literal["LLM", "TEMPLATE"]
    perspective: Literal["BLACK", "WHITE"]
    candidates: list[GameCandidateMove]
    explanation: ExplanationText
