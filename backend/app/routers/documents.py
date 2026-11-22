from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Parcel, ParcelDocument
from app.schemas import DocumentVerificationResponse

router = APIRouter(prefix="/api/v1/documents", tags=["Printable documents"])


@router.get("/verify/{verification_code}", response_model=DocumentVerificationResponse)
def verify_document(verification_code: str, db: Session = Depends(get_db)):
    """Publicly verify a receipt without disclosing recipient contact or address details."""
    document = db.scalar(
        select(ParcelDocument).where(ParcelDocument.verification_code == verification_code)
    )
    if document is None:
        raise HTTPException(status_code=404, detail="No TimeDrop document matches this verification code.")
    parcel = db.get(Parcel, document.parcel_id)
    if parcel is None:
        raise HTTPException(status_code=404, detail="The parcel record for this document no longer exists.")
    return DocumentVerificationResponse(
        valid=True,
        document_number=document.document_number,
        document_type=document.document_type,
        tracking_number=parcel.tracking_number,
        issued_at=document.created_at,
        sha256=document.sha256,
    )
