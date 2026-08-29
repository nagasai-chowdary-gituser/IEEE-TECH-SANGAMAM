from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from app.api.deps import AiIdentity, resolve_ai_identity
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.schemas.ai import AIExplanation, AnalysisListResponse, AskRequest, AskResponse
from app.schemas.analysis import AnalysisResponse
from app.services.forensics.artifacts import resolve_artifact_path
from app.services.orchestration import AnalysisOrchestrator

router = APIRouter()


def get_orchestrator(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AnalysisOrchestrator:
    return AnalysisOrchestrator(db, settings)


@router.post("/documents/analyze", response_model=AnalysisResponse)
async def analyze_document(
    file: UploadFile = File(...),
    orchestrator: AnalysisOrchestrator = Depends(get_orchestrator),
) -> AnalysisResponse:
    return orchestrator.analyze_upload(file)


@router.get("/documents", response_model=AnalysisListResponse)
def list_documents(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    orchestrator: AnalysisOrchestrator = Depends(get_orchestrator),
) -> AnalysisListResponse:
    return orchestrator.list_analyses(limit=limit, offset=offset)


@router.get("/documents/{analysis_id}", response_model=AnalysisResponse)
def get_document_analysis(
    analysis_id: str,
    orchestrator: AnalysisOrchestrator = Depends(get_orchestrator),
) -> AnalysisResponse:
    return orchestrator.get_analysis(analysis_id)


@router.get("/documents/{analysis_id}/explanation", response_model=AIExplanation)
def get_document_explanation(
    analysis_id: str,
    orchestrator: AnalysisOrchestrator = Depends(get_orchestrator),
    identity: AiIdentity = Depends(resolve_ai_identity),
) -> AIExplanation:
    return orchestrator.get_explanation(analysis_id, identity)


@router.post("/documents/{analysis_id}/ask", response_model=AskResponse)
def ask_about_analysis(
    analysis_id: str,
    payload: AskRequest,
    orchestrator: AnalysisOrchestrator = Depends(get_orchestrator),
    identity: AiIdentity = Depends(resolve_ai_identity),
) -> AskResponse:
    return orchestrator.ask(analysis_id, payload.question, identity)


@router.get("/documents/{analysis_id}/report")
def get_document_report(
    analysis_id: str,
    orchestrator: AnalysisOrchestrator = Depends(get_orchestrator),
) -> Response:
    data = orchestrator.get_report(analysis_id)
    filename = f"docuverify-report-{analysis_id[:8]}.pdf"
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/documents/{analysis_id}/artifacts/{artifact_id}")
def get_analysis_artifact(
    analysis_id: str,
    artifact_id: str,
    orchestrator: AnalysisOrchestrator = Depends(get_orchestrator),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    orchestrator.get_analysis(analysis_id)
    path = resolve_artifact_path(settings, analysis_id, artifact_id)
    return FileResponse(path, media_type="image/png", filename=f"{artifact_id}.png")
