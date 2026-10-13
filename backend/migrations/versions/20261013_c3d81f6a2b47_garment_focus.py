"""garment focus

Revision ID: c3d81f6a2b47
Revises: ffabeaea0902
"""

import sqlalchemy as sa
from alembic import op

revision = "c3d81f6a2b47"
down_revision = "ffabeaea0902"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("garments", sa.Column("focus", sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column("garments", "focus")
