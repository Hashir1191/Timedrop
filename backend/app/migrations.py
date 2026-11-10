from sqlalchemy import inspect, text

from app.database import engine


def upgrade_legacy_parcel_table() -> None:
    """Add ownership to databases created before customer accounts existed.

    Existing parcels are intentionally left unowned (owner_id NULL). They remain
    visible to administrators only until an administrator assigns them.
    """
    inspector = inspect(engine)
    if "parcels" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("parcels")}
    if "owner_id" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE parcels "
                    "ADD COLUMN owner_id INTEGER REFERENCES users(id) ON DELETE SET NULL"
                )
            )
            connection.execute(
                text("CREATE INDEX IF NOT EXISTS ix_parcels_owner_id ON parcels (owner_id)")
            )


def upgrade_delivery_assignment_table() -> None:
    """Add delivery failure details to databases created before this field existed."""
    inspector = inspect(engine)
    if "delivery_assignments" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("delivery_assignments")}
    if "failure_reason" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE delivery_assignments ADD COLUMN failure_reason VARCHAR(300)"))


def upgrade_delivery_proof_fields() -> None:
    """Add OTP-based proof-of-delivery fields to existing assignment tables."""
    inspector = inspect(engine)
    if "delivery_assignments" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("delivery_assignments")}
    additions = {
        "delivery_code_hash": "VARCHAR(255)",
        "delivery_code_expires_at": "DATETIME",
        "delivery_code_attempts": "INTEGER NOT NULL DEFAULT 0",
        "delivered_at": "DATETIME",
        "proof_recipient_name": "VARCHAR(120)",
    }
    with engine.begin() as connection:
        for name, sql_type in additions.items():
            if name not in columns:
                connection.execute(text(f"ALTER TABLE delivery_assignments ADD COLUMN {name} {sql_type}"))
