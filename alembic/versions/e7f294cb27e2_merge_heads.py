"""merge heads

Revision ID: e7f294cb27e2
Revises: fedad2007a6a, 9e27f65a6b81
Create Date: 2025-11-01 20:58:57.205853

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7f294cb27e2'
down_revision: Union[str, Sequence[str], None] = ('fedad2007a6a', '9e27f65a6b81')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
