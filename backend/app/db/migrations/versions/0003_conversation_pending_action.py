import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("pending_action", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column("pending_action_expires_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("conversations", "pending_action_expires_at")
    op.drop_column("conversations", "pending_action")
