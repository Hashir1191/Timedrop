from datetime import datetime, timezone
from hashlib import sha256
from pathlib import PurePath
import secrets

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Parcel, SupportCase, SupportCaseAttachment, SupportCaseEvent, SupportCaseMessage, User
from app.notifications import add_notification
from app.schemas import (
    SupportCaseCreate,
    SupportCaseMessageResponse, SupportCaseAttachmentResponse,
    SupportCaseResponse,
    SupportCaseUpdate,
    SupportMessageCreate,
)
from app.security import get_current_user, require_admin

router = APIRouter(prefix="/api/v1/support", tags=["Customer support"])
MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024
MAX_CASE_ATTACHMENTS = 5
MAX_CASE_ATTACHMENT_TOTAL = 15 * 1024 * 1024
ALLOWED_ATTACHMENT_TYPES = {"application/pdf": ".pdf", "image/jpeg": ".jpg", "image/png": ".png"}


def _serialize_case(db: Session, case: SupportCase, include_internal: bool = False) -> SupportCaseResponse:
    customer = db.get(User, case.customer_id)
    parcel = db.get(Parcel, case.parcel_id) if case.parcel_id else None
    assignee = db.get(User, case.assigned_to_id) if case.assigned_to_id else None
    statement = (
        select(SupportCaseMessage, User.full_name)
        .join(User, User.id == SupportCaseMessage.author_id)
        .where(SupportCaseMessage.case_id == case.id)
        .order_by(SupportCaseMessage.created_at, SupportCaseMessage.id)
    )
    if not include_internal:
        statement = statement.where(SupportCaseMessage.is_internal.is_(False))
    messages = [
        SupportCaseMessageResponse(
            id=message.id,
            author_id=message.author_id,
            author_name=author_name,
            body=message.body,
            is_internal=message.is_internal,
            created_at=message.created_at,
        )
        for message, author_name in db.execute(statement).all()
    ]
    attachment_statement = (
        select(SupportCaseAttachment)
        .where(SupportCaseAttachment.case_id == case.id)
        .order_by(SupportCaseAttachment.created_at, SupportCaseAttachment.id)
    )
    if not include_internal:
        attachment_statement = attachment_statement.where(SupportCaseAttachment.is_internal.is_(False))
    attachments = [
        SupportCaseAttachmentResponse(
            id=item.id,
            filename=item.filename,
            content_type=item.content_type,
            file_size=item.file_size,
            sha256=item.sha256,
            uploader_id=item.uploader_id,
            is_internal=item.is_internal,
            created_at=item.created_at,
        )
        for item in db.scalars(attachment_statement).all()
    ]
    return SupportCaseResponse(
        id=case.id,
        case_number=case.case_number,
        customer_id=case.customer_id,
        customer_name=customer.full_name if customer else "Customer",
        parcel_id=case.parcel_id,
        tracking_number=parcel.tracking_number if parcel else None,
        category=case.category,
        subject=case.subject,
        description=case.description,
        status=case.status,
        priority=case.priority,
        assigned_to_id=case.assigned_to_id,
        assigned_to_name=assignee.full_name if assignee else None,
        created_at=case.created_at,
        updated_at=case.updated_at,
        resolved_at=case.resolved_at,
        messages=messages,
        attachments=attachments,
    )


def _case_for_customer(db: Session, case_id: int, customer: User) -> SupportCase:
    case = db.get(SupportCase, case_id)
    if case is None or case.customer_id != customer.id:
        raise HTTPException(status_code=404, detail="Support case not found.")
    return case


@router.post("/cases", response_model=SupportCaseResponse, status_code=status.HTTP_201_CREATED)
def create_support_case(
    data: SupportCaseCreate,
    db: Session = Depends(get_db),
    customer: User = Depends(get_current_user),
):
    if customer.role != "customer":
        raise HTTPException(status_code=403, detail="Customer access is required.")
    if data.parcel_id is not None:
        parcel = db.get(Parcel, data.parcel_id)
        if parcel is None or parcel.owner_id != customer.id:
            raise HTTPException(status_code=404, detail="Parcel not found.")
    now = datetime.now(timezone.utc)
    case = SupportCase(
        case_number=f"TD-{now:%y%m%d}-{secrets.token_hex(3).upper()}",
        customer_id=customer.id,
        parcel_id=data.parcel_id,
        category=data.category,
        subject=data.subject,
        description=data.description,
        status="open",
        priority="high" if data.category in {"suspected_theft", "missing_parcel"} else "normal",
        created_at=now,
        updated_at=now,
    )
    db.add(case)
    try:
        db.flush()
        db.add(SupportCaseEvent(
            case_id=case.id,
            actor_id=customer.id,
            event_type="case_created",
            to_status="open",
            note=f"Customer opened a {data.category.replace('_', ' ')} case.",
            created_at=now,
        ))
        db.commit()
        db.refresh(case)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Unable to create the support case. Please try again.")
    return _serialize_case(db, case)


@router.get("/cases", response_model=list[SupportCaseResponse])
def list_customer_cases(
    db: Session = Depends(get_db),
    customer: User = Depends(get_current_user),
):
    if customer.role != "customer":
        raise HTTPException(status_code=403, detail="Customer access is required.")
    cases = db.scalars(
        select(SupportCase)
        .where(SupportCase.customer_id == customer.id)
        .order_by(SupportCase.updated_at.desc(), SupportCase.id.desc())
    ).all()
    return [_serialize_case(db, case) for case in cases]


@router.get("/cases/{case_id}", response_model=SupportCaseResponse)
def get_customer_case(
    case_id: int,
    db: Session = Depends(get_db),
    customer: User = Depends(get_current_user),
):
    if customer.role != "customer":
        raise HTTPException(status_code=403, detail="Customer access is required.")
    return _serialize_case(db, _case_for_customer(db, case_id, customer))


async def _store_case_attachment(
    db: Session,
    case: SupportCase,
    uploader: User,
    upload: UploadFile,
    is_internal: bool,
) -> SupportCaseResponse:
    if case.status in {"resolved", "closed"}:
        raise HTTPException(status_code=409, detail="Reopen the case before adding evidence.")
    content_type = (upload.content_type or "").lower()
    extension = ALLOWED_ATTACHMENT_TYPES.get(content_type)
    if extension is None:
        raise HTTPException(status_code=415, detail="Upload a PDF, JPEG or PNG evidence file.")
    filename = PurePath(upload.filename or "evidence").name
    filename = "".join(character for character in filename if character.isalnum() or character in " ._-")[:180].strip()
    allowed_extensions = {extension, ".jpeg" if extension == ".jpg" else extension}
    if not filename or PurePath(filename).suffix.lower() not in allowed_extensions:
        raise HTTPException(status_code=415, detail="The file extension does not match its allowed content type.")
    content = await upload.read(MAX_ATTACHMENT_BYTES + 1)
    if not content:
        raise HTTPException(status_code=422, detail="The evidence file is empty.")
    if len(content) > MAX_ATTACHMENT_BYTES:
        raise HTTPException(status_code=413, detail="Each evidence file must be 5 MB or smaller.")
    valid_magic = (
        (content_type == "application/pdf" and content.startswith(b"%PDF-"))
        or (content_type == "image/jpeg" and content.startswith(b"\xff\xd8\xff"))
        or (content_type == "image/png" and content.startswith(b"\x89PNG\r\n\x1a\n"))
    )
    if not valid_magic:
        raise HTTPException(status_code=415, detail="The file contents do not match the declared PDF, JPEG or PNG type.")
    count = db.scalar(select(func.count(SupportCaseAttachment.id)).where(SupportCaseAttachment.case_id == case.id)) or 0
    total_size = db.scalar(select(func.coalesce(func.sum(SupportCaseAttachment.file_size), 0)).where(SupportCaseAttachment.case_id == case.id)) or 0
    if count >= MAX_CASE_ATTACHMENTS:
        raise HTTPException(status_code=409, detail="A support case can contain up to five evidence files.")
    if total_size + len(content) > MAX_CASE_ATTACHMENT_TOTAL:
        raise HTTPException(status_code=413, detail="The total evidence size for this case cannot exceed 15 MB.")
    now = datetime.now(timezone.utc)
    attachment = SupportCaseAttachment(
        case_id=case.id,
        uploader_id=uploader.id,
        filename=filename,
        content_type=content_type,
        file_size=len(content),
        sha256=sha256(content).hexdigest(),
        is_internal=is_internal,
        file_content=content,
        created_at=now,
    )
    db.add(attachment)
    case.updated_at = now
    db.add(SupportCaseEvent(
        case_id=case.id,
        actor_id=uploader.id,
        event_type="evidence_attached",
        from_status=case.status,
        to_status=case.status,
        note="An evidence file was attached to the support case.",
        created_at=now,
    ))
    db.commit()
    db.refresh(case)
    return _serialize_case(db, case, include_internal=uploader.role == "admin")


def _attachment_response(attachment: SupportCaseAttachment) -> Response:
    safe_filename = attachment.filename.replace('"', "").replace("\r", "").replace("\n", "")
    return Response(
        content=attachment.file_content,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename}"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
            "X-Evidence-SHA256": attachment.sha256,
        },
    )


@router.post("/cases/{case_id}/attachments", response_model=SupportCaseResponse, status_code=status.HTTP_201_CREATED)
async def upload_customer_evidence(
    case_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    customer: User = Depends(get_current_user),
):
    if customer.role != "customer":
        raise HTTPException(status_code=403, detail="Customer access is required.")
    case = _case_for_customer(db, case_id, customer)
    return await _store_case_attachment(db, case, customer, file, is_internal=False)


@router.post("/admin/cases/{case_id}/attachments", response_model=SupportCaseResponse, status_code=status.HTTP_201_CREATED)
async def upload_admin_evidence(
    case_id: int,
    file: UploadFile = File(...),
    is_internal: bool = Form(default=True),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    case = db.get(SupportCase, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Support case not found.")
    return await _store_case_attachment(db, case, admin, file, is_internal=is_internal)


@router.get("/cases/{case_id}/attachments/{attachment_id}")
def download_customer_evidence(
    case_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    customer: User = Depends(get_current_user),
):
    if customer.role != "customer":
        raise HTTPException(status_code=403, detail="Customer access is required.")
    _case_for_customer(db, case_id, customer)
    attachment = db.get(SupportCaseAttachment, attachment_id)
    if attachment is None or attachment.case_id != case_id or attachment.is_internal:
        raise HTTPException(status_code=404, detail="Evidence file not found.")
    return _attachment_response(attachment)


@router.get("/admin/cases/{case_id}/attachments/{attachment_id}")
def download_admin_evidence(
    case_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    attachment = db.get(SupportCaseAttachment, attachment_id)
    if attachment is None or attachment.case_id != case_id:
        raise HTTPException(status_code=404, detail="Evidence file not found.")
    return _attachment_response(attachment)


@router.post("/cases/{case_id}/messages", response_model=SupportCaseResponse)
def reply_to_customer_case(
    case_id: int,
    data: SupportMessageCreate,
    db: Session = Depends(get_db),
    customer: User = Depends(get_current_user),
):
    if customer.role != "customer" or data.is_internal:
        raise HTTPException(status_code=403, detail="Customers can only add public replies to their own cases.")
    case = _case_for_customer(db, case_id, customer)
    if case.status in {"resolved", "closed"}:
        raise HTTPException(status_code=409, detail="This case is closed. Open a new case if you still need help.")
    now = datetime.now(timezone.utc)
    db.add(SupportCaseMessage(case_id=case.id, author_id=customer.id, body=data.body, is_internal=False, created_at=now))
    previous_status = case.status
    if case.status == "waiting_customer":
        case.status = "in_progress"
    case.updated_at = now
    db.add(SupportCaseEvent(
        case_id=case.id, actor_id=customer.id, event_type="customer_replied",
        from_status=previous_status, to_status=case.status, note="Customer added a reply.", created_at=now,
    ))
    db.commit()
    db.refresh(case)
    return _serialize_case(db, case)


@router.get("/admin/cases", response_model=list[SupportCaseResponse])
def list_support_queue(
    status_filter: str | None = Query(default=None, alias="status", pattern=r"^(open|triaged|in_progress|waiting_customer|resolved|closed)$"),
    priority: str | None = Query(default=None, pattern=r"^(low|normal|high|urgent)$"),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    statement = select(SupportCase)
    if status_filter:
        statement = statement.where(SupportCase.status == status_filter)
    if priority:
        statement = statement.where(SupportCase.priority == priority)
    cases = db.scalars(statement.order_by(SupportCase.updated_at.desc(), SupportCase.id.desc()).limit(limit)).all()
    return [_serialize_case(db, case, include_internal=True) for case in cases]


@router.get("/admin/cases/{case_id}", response_model=SupportCaseResponse)
def get_admin_case(case_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    case = db.get(SupportCase, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Support case not found.")
    return _serialize_case(db, case, include_internal=True)


@router.patch("/admin/cases/{case_id}", response_model=SupportCaseResponse)
def update_support_case(
    case_id: int,
    data: SupportCaseUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    case = db.get(SupportCase, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Support case not found.")
    changes = data.model_dump(exclude_unset=True)
    if "assigned_to_id" in changes and changes["assigned_to_id"] is not None:
        assignee = db.get(User, changes["assigned_to_id"])
        if assignee is None or assignee.role != "admin" or not assignee.is_active:
            raise HTTPException(status_code=422, detail="Cases can only be assigned to an active operations administrator.")
    now = datetime.now(timezone.utc)
    previous_status = case.status
    previous_priority = case.priority
    previous_assignee = case.assigned_to_id
    for field, value in changes.items():
        setattr(case, field, value)
    if "status" in changes:
        case.resolved_at = now if case.status in {"resolved", "closed"} else None
    case.updated_at = now
    notes = []
    if "status" in changes:
        notes.append(f"Status: {previous_status} → {case.status}")
    if "priority" in changes:
        notes.append(f"Priority: {previous_priority} → {case.priority}")
    if "assigned_to_id" in changes:
        notes.append(f"Assignee: {previous_assignee or 'unassigned'} → {case.assigned_to_id or 'unassigned'}")
    if "status" in changes:
        add_notification(
            db,
            user_id=case.customer_id,
            parcel_id=case.parcel_id,
            event_type="support_case_status",
            title="Support case updated",
            message=f"Your TimeDrop case {case.case_number} is now {case.status.replace('_', ' ')}.",
        )
    db.add(SupportCaseEvent(
        case_id=case.id, actor_id=admin.id, event_type="case_updated",
        from_status=previous_status, to_status=case.status,
        note="; ".join(notes), created_at=now,
    ))
    db.commit()
    db.refresh(case)
    return _serialize_case(db, case, include_internal=True)


@router.post("/admin/cases/{case_id}/messages", response_model=SupportCaseResponse)
def reply_from_support(
    case_id: int,
    data: SupportMessageCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    case = db.get(SupportCase, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Support case not found.")
    if case.status in {"resolved", "closed"} and not data.is_internal:
        raise HTTPException(status_code=409, detail="Reopen the case before sending a customer-visible reply.")
    now = datetime.now(timezone.utc)
    db.add(SupportCaseMessage(
        case_id=case.id, author_id=admin.id, body=data.body,
        is_internal=data.is_internal, created_at=now,
    ))
    case.updated_at = now
    if not data.is_internal:
        add_notification(
            db,
            user_id=case.customer_id,
            parcel_id=case.parcel_id,
            event_type="support_case_reply",
            title="Support team replied",
            message=f"Our team replied to support case {case.case_number}.",
        )
        previous_status = case.status
        case.status = "waiting_customer"
        db.add(SupportCaseEvent(
            case_id=case.id, actor_id=admin.id, event_type="support_replied",
            from_status=previous_status, to_status=case.status,
            note="Operations sent a customer-visible reply.", created_at=now,
        ))
    else:
        db.add(SupportCaseEvent(
            case_id=case.id, actor_id=admin.id, event_type="internal_note",
            from_status=case.status, to_status=case.status,
            note="Operations added an internal note.", created_at=now,
        ))
    db.commit()
    db.refresh(case)
    return _serialize_case(db, case, include_internal=True)
