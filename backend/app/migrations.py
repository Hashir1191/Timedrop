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
