from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models import GenerationJob, JobStatus, Recipient
from app.schemas.job import GenerationJobCreate, JobResponse, RecipientResponse
from app.services.job_processor import process_job

router = APIRouter(prefix="/api", tags=["certificate generation"])


def serialize_job(job: GenerationJob, base_url: str) -> JobResponse:
    completed = job.successful_count + job.failed_count
    progress = round((completed / job.total_recipients) * 100, 2) if job.total_recipients else 0.0
    recipients = [
        RecipientResponse(
            id=r.id,
            name=r.name,
            email=r.email,
            status=r.status.value,
            certificate_url=f"{base_url}/api/certificates/{r.id}" if r.certificate_path else None,
            error_message=r.error_message,
        )
        for r in job.recipients
    ]
    return JobResponse(
        id=job.id,
        event_name=job.event_name,
        certificate_title=job.certificate_title,
        total_recipients=job.total_recipients,
        successful_count=job.successful_count,
        failed_count=job.failed_count,
        status=job.status.value,
        created_at=job.created_at,
        updated_at=job.updated_at,
        progress_percent=progress,
        recipients=recipients,
    )


@router.post("/jobs", response_model=JobResponse, status_code=202)
def create_generation_job(
    payload: GenerationJobCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    # Pydantic handles structural validation; this prevents blank/whitespace-only names.
    cleaned = []
    seen_names = set()
    for item in payload.recipients:
        name = item.name.strip()
        if not name:
            raise HTTPException(status_code=422, detail="Recipient name cannot be blank")
        key = (name.casefold(), (item.email or "").casefold())
        if key in seen_names:
            raise HTTPException(status_code=422, detail=f"Duplicate recipient: {name}")
        seen_names.add(key)
        cleaned.append((name, item.email))

    job = GenerationJob(
        event_name=payload.event_name.strip(),
        certificate_title=payload.certificate_title.strip(),
        total_recipients=len(cleaned),
    )
    job.recipients = [Recipient(name=name, email=email) for name, email in cleaned]
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(process_job, job.id)
    return serialize_job(job, "")


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.get(GenerationJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Generation job not found")
    return serialize_job(job, "")


@router.get("/certificates/{recipient_id}")
def get_certificate(recipient_id: str, db: Session = Depends(get_db)):
    recipient = db.get(Recipient, recipient_id)
    if not recipient:
        raise HTTPException(status_code=404, detail="Certificate record not found")
    if not recipient.certificate_path or recipient.status.value != "COMPLETED":
        raise HTTPException(status_code=404, detail="Certificate is not available")

    path = Path(recipient.certificate_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Generated certificate file not found")
    return FileResponse(path, media_type="application/pdf", filename=f"certificate-{recipient.name}.pdf")
