"""garment wear count

Revision ID: 7b1e4c9d2a10
Revises: 2f3f9c33d47c
"""

import sqlalchemy as sa
from alembic import op

revision = "7b1e4c9d2a10"
down_revision = "2f3f9c33d47c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "garments", sa.Column("wear_count", sa.Integer(), server_default="0", nullable=False)
    )
    # Counts what was already worn before this column existed.
    op.execute(
        """
        UPDATE garments g SET wear_count = (
            SELECT count(*) FROM outfits o
            WHERE o.worn_at IS NOT NULL
              AND g.id IN (o.top_id, o.bottom_id, o.one_piece_id,
                           o.outerwear_id, o.shoes_id, o.accessory_id)
        )
        """
    )


def downgrade() -> None:
    op.drop_column("garments", "wear_count")
