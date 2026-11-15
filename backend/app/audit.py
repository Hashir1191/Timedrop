import json

from sqlalchemy.orm import Session

from app.models import OperationsAuditLog


def record_operations_audit(
    db: Session,
    *,
    actor_id: int,
    action: str,
    entity_type: str,
    entity_id: int,
    summary: str,
    changed_fields: list[str] | tuple[str, ...] = (),
) -> None:
    """Append an audit event without storing submitted field values or sensitive data."""
    db.add(
        OperationsAuditLog(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            summary=summary[:255],
            changed_fields_json=json.dumps(sorted(set(changed_fields))),
        )
    )
