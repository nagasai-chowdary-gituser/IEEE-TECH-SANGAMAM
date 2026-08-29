from pydantic import BaseModel, Field

from app.schemas.common import Severity


class MetadataSignal(BaseModel):
    id: str
    finding: str
    severity: Severity
    score_impact: int
    detail: str


class MetadataForensicsResult(BaseModel):
    layer: str = "metadata"
    suspicion_score: int = Field(ge=0, le=100)
    flagged: bool
    confidence: float = Field(ge=0.0, le=1.0)
    signals: list[MetadataSignal] = Field(default_factory=list)
    summary: str
