from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.schemas.signature import (
    ManualRegionRequest,
    ReferenceListResponse,
    ReferenceSignatureResponse,
    SignatureComparisonListResponse,
    SignatureComparisonResponse,
)
from app.services.signature.orchestrator import SignatureOrchestrator
from app.services.signature.report import build_signature_report
from app.services.signature.serializers import to_reference_response
from app.services.signature.storage import resolve_signature_artifact

router = APIRouter()


def get_orchestrator(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SignatureOrchestrator:
    return SignatureOrchestrator(db, settings)


@router.post("/signatures/references", response_model=ReferenceSignatureResponse)
async def create_reference(
    file: UploadFile = File(...),
    label: str | None = Form(default=None),
    orchestrator: SignatureOrchestrator = Depends(get_orchestrator),
) -> ReferenceSignatureResponse:
    record = orchestrator.create_reference(file, label)
    return to_reference_response(record)


@router.get("/signatures/references", response_model=ReferenceListResponse)
def list_references(orchestrator: SignatureOrchestrator = Depends(get_orchestrator)) -> ReferenceListResponse:
    return orchestrator.list_references()


@router.delete("/signatures/references/{reference_id}")
def delete_reference(
    reference_id: str,
    orchestrator: SignatureOrchestrator = Depends(get_orchestrator),
) -> dict[str, str]:
    orchestrator.delete_reference(reference_id)
    return {"status": "deleted"}


@router.get("/signatures/references/{reference_id}/image")
def get_reference_image(
    reference_id: str,
    variant: str = Query(default="original"),
    orchestrator: SignatureOrchestrator = Depends(get_orchestrator),
) -> FileResponse:
    from pathlib import Path

    record = orchestrator._require_reference(reference_id)
    path = Path(record.file_path)
    if variant == "normalized":
        path = path.with_name(f"{path.stem}-normalized.png")
    if not path.is_file():
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reference image not found.")
    root = orchestrator.settings.upload_path.resolve()
    if not str(path.resolve()).startswith(str(root)):
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid storage path.")
    return FileResponse(path, media_type="image/png", filename=path.name)


@router.post("/signatures/compare", response_model=SignatureComparisonResponse)
async def compare_signature(
    file: UploadFile = File(...),
    reference_id: str | None = Form(default=None),
    orchestrator: SignatureOrchestrator = Depends(get_orchestrator),
) -> SignatureComparisonResponse:
    cleaned = (reference_id or "").strip() or None
    return orchestrator.start_comparison(file, cleaned)


@router.post("/signatures/comparisons/{comparison_id}/region", response_model=SignatureComparisonResponse)
def set_region(
    comparison_id: str,
    payload: ManualRegionRequest,
    orchestrator: SignatureOrchestrator = Depends(get_orchestrator),
) -> SignatureComparisonResponse:
    return orchestrator.apply_region(comparison_id, payload)


@router.get("/signatures/comparisons", response_model=SignatureComparisonListResponse)
def list_comparisons(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    orchestrator: SignatureOrchestrator = Depends(get_orchestrator),
) -> SignatureComparisonListResponse:
    return orchestrator.list_comparisons(limit=limit, offset=offset)


@router.get("/signatures/comparisons/{comparison_id}", response_model=SignatureComparisonResponse)
def get_comparison(
    comparison_id: str,
    orchestrator: SignatureOrchestrator = Depends(get_orchestrator),
) -> SignatureComparisonResponse:
    return orchestrator.get_comparison(comparison_id)


@router.get("/signatures/comparisons/{comparison_id}/report")
def get_comparison_report(
    comparison_id: str,
    orchestrator: SignatureOrchestrator = Depends(get_orchestrator),
) -> Response:
    record = orchestrator._require_comparison(comparison_id)
    if record.status == "PROCESSING":
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Certificate analysis is still running.")
    reference = orchestrator.repo.get_reference(record.reference_id) if record.reference_id else None
    data = build_signature_report(record, reference)
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="docuverify-certificate-{comparison_id[:8]}.pdf"'},
    )


@router.get("/signatures/comparisons/{comparison_id}/artifacts/{artifact_id}")
def get_comparison_artifact(
    comparison_id: str,
    artifact_id: str,
    orchestrator: SignatureOrchestrator = Depends(get_orchestrator),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    orchestrator.get_comparison(comparison_id)
    path = resolve_signature_artifact(settings, comparison_id, artifact_id)
    return FileResponse(path, media_type="image/png", filename=f"{artifact_id}.png")
