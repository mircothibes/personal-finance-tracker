from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "4509b646c55f"
down_revision = "6479886f489c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("type", sa.String(10), nullable=False),
    )
    # simple constraint: only 'income' or 'expense'
    op.create_check_constraint(
        "ck_categories_type",
        "categories",
        "type IN ('income','expense')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_categories_type", "categories", type_="check")
    op.drop_table("categories")



