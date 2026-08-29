from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.schemas.compliance import ComplianceListResponse, ComplianceResponse
from app.services.compliance.orchestrator import ComplianceOrchestrator
from app.services.compliance.report import build_compliance_report

router = APIRouter()


def get_orchestrator(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ComplianceOrchestrator:
    return ComplianceOrchestrator(db, settings)


@router.post("/compliance/analyze", response_model=ComplianceResponse)
async def analyze_compliance(
    file: UploadFile = File(...),
    orchestrator: ComplianceOrchestrator = Depends(get_orchestrator),
) -> ComplianceResponse:
    return orchestrator.start(file)


@router.get("/compliance", response_model=ComplianceListResponse)
def list_compliance(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    orchestrator: ComplianceOrchestrator = Depends(get_orchestrator),
) -> ComplianceListResponse:
    return orchestrator.list_analyses(limit=limit, offset=offset)


@router.get("/compliance/{compliance_id}", response_model=ComplianceResponse)
def get_compliance(
    compliance_id: str,
    orchestrator: ComplianceOrchestrator = Depends(get_orchestrator),
) -> ComplianceResponse:
    return orchestrator.get(compliance_id)


@router.get("/compliance/{compliance_id}/report")
def get_compliance_report(
    compliance_id: str,
    orchestrator: ComplianceOrchestrator = Depends(get_orchestrator),
    settings: Settings = Depends(get_settings),
) -> Response:
    record = orchestrator._require(compliance_id)
    if record.status == "PROCESSING":
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Compliance analysis is still running.")
    forensic = orchestrator.forensics.repo.get(record.forensic_analysis_id) if record.forensic_analysis_id else None
    data = build_compliance_report(record, forensic)
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="docuverify-compliance-{compliance_id[:8]}.pdf"'},
    )
