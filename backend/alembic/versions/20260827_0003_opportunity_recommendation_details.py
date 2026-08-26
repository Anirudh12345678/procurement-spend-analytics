"""Add explainability fields to opportunities and recommendations.

Revision ID: 20260827_0003
Revises: 20260826_0002
Create Date: 2026-08-27
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260827_0003"
down_revision: str | None = "20260826_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        op.f("ck_cost_opportunities_valid_status"),
        "cost_opportunities",
        type_="check",
    )
    op.add_column(
        "cost_opportunities",
        sa.Column(
            "review_spend",
            sa.Numeric(precision=18, scale=4),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.add_column(
        "cost_opportunities",
        sa.Column("supporting_metrics", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
    )
    op.create_check_constraint(
        op.f("ck_cost_opportunities_valid_status"),
        "cost_opportunities",
        "status IN ('OPEN', 'IN_REVIEW', 'ACCEPTED', 'REJECTED', 'COMPLETED', 'STALE')",
    )
    op.create_check_constraint(
        op.f("ck_cost_opportunities_review_spend_nonnegative"),
        "cost_opportunities",
        "review_spend >= 0",
    )
    op.add_column("ai_recommendations", sa.Column("risks", sa.Text(), nullable=True))
    op.add_column(
        "ai_recommendations",
        sa.Column("next_steps", sa.JSON(), server_default=sa.text("'[]'"), nullable=False),
    )
    op.add_column(
        "ai_recommendations",
        sa.Column("context_snapshot", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("ai_recommendations", "context_snapshot")
    op.drop_column("ai_recommendations", "next_steps")
    op.drop_column("ai_recommendations", "risks")
    op.drop_constraint(
        op.f("ck_cost_opportunities_review_spend_nonnegative"),
        "cost_opportunities",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_cost_opportunities_valid_status"),
        "cost_opportunities",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_cost_opportunities_valid_status"),
        "cost_opportunities",
        "status IN ('OPEN', 'IN_REVIEW', 'ACCEPTED', 'REJECTED', 'COMPLETED')",
    )
    op.drop_column("cost_opportunities", "supporting_metrics")
    op.drop_column("cost_opportunities", "review_spend")
