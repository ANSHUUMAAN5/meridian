"""widen escalations.reason to text

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-18

The column was sized at VARCHAR(60) on a guess that "reason" would be a short
code. In practice it holds Threshold's full explanation sentence — e.g.
"write-tier action (refund_request) requires explicit confirmation" — which
is exactly the detail a human in Relay needs to see, and easily exceeds 60
characters. Found by actually exercising the escalation path end to end
(the first write-tier message sent through the running API failed with
StringDataRightTruncationError), not by review.
"""

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
    # Not reversible without risking truncation of existing rows — a real
    # rollback would need to decide what to do with over-length data, which
    # is a judgment call, not something the migration should decide silently.
    op.alter_column(
        "escalations", "reason", existing_type=sa.Text(), type_=sa.String(60), nullable=False
    )
