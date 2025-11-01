"""bootstrap

Revision ID: 6479886f489c
Revises: 9e27f65a6b81
Create Date: 2025-11-01 19:11:41.800028

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6479886f489c'
down_revision: Union[str, Sequence[str], None] = '9e27f65a6b81'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
