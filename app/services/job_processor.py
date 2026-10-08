from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import GenerationJob, JobStatus, Recipient, RecipientStatus
from app.services.certificate import generate_certificate


def process_job(job_id: str) -> None:
    """Process recipients independently so one failure does not stop the batch."""
    db: Session = SessionLocal()
    try:
        job = db.get(GenerationJob, job_id)
        if not job:
            return

        job.status = JobStatus.PROCESSING
        db.commit()

        recipients = db.query(Recipient).filter(Recipient.job_id == job_id).all()
        for recipient in recipients:
            try:
                recipient.status = RecipientStatus.PROCESSING
                db.commit()

                recipient.certificate_path = generate_certificate(
                    recipient_name=recipient.name,
                    certificate_title=job.certificate_title,
                    event_name=job.event_name,
                    output_dir=settings.certificate_output_dir,
                )
                recipient.status = RecipientStatus.COMPLETED
                recipient.error_message = None
            except Exception as exc:  # isolate failure to this recipient
                recipient.status = RecipientStatus.FAILED
                recipient.error_message = str(exc)[:2000]
            finally:
                db.commit()

        successful = db.query(Recipient).filter(
            Recipient.job_id == job_id,
            Recipient.status == RecipientStatus.COMPLETED,
        ).count()
        failed = db.query(Recipient).filter(
            Recipient.job_id == job_id,
            Recipient.status == RecipientStatus.FAILED,
        ).count()

        job.successful_count = successful
        job.failed_count = failed
        job.status = JobStatus.COMPLETED_WITH_ERRORS if failed else JobStatus.COMPLETED
        db.commit()
    finally:
        db.close()
