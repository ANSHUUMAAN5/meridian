import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "messages", "created_at",
        server_default=sa.text("clock_timestamp()"),
    )


def downgrade() -> None:
    op.alter_column(
        "messages", "created_at",
        server_default=sa.text("now()"),
    )
