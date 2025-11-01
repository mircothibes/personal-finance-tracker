from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "10d48f683bb9"
down_revision = "e7f294cb27e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("type", sa.String(10), nullable=False),  # 'income' | 'expense'
        sa.Column("category_id", sa.Integer, sa.ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("account_id", sa.Integer, sa.ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("notes", sa.String(255), nullable=True),
    )

    op.create_check_constraint(
        "ck_transactions_type",
        "transactions",
        "type IN ('income','expense')",
    )
    op.create_check_constraint(
        "ck_transactions_amount_positive",
        "transactions",
        "amount >= 0",
    )

    op.create_index("ix_transactions_date", "transactions", ["date"])
    op.create_index("ix_transactions_category", "transactions", ["category_id"])
    op.create_index("ix_transactions_account", "transactions", ["account_id"])


def downgrade() -> None:
    op.drop_index("ix_transactions_account", table_name="transactions")
    op.drop_index("ix_transactions_category", table_name="transactions")
    op.drop_index("ix_transactions_date", table_name="transactions")
    op.drop_constraint("ck_transactions_amount_positive", "transactions", type_="check")
    op.drop_constraint("ck_transactions_type", "transactions", type_="check")
    op.drop_table("transactions")

