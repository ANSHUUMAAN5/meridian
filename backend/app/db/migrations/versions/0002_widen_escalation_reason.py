import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "escalations", "reason", existing_type=sa.String(60), type_=sa.Text(), nullable=False
    )


def downgrade() -> None:
    op.alter_column(
        "escalations", "reason", existing_type=sa.Text(), type_=sa.String(60), nullable=False
    )
