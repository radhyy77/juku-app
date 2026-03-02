"""add homework tables: homeworks, homework_submissions

Revision ID: 0006
Revises: 0005
Create Date: 2026-03-01 00:00:00.000000

変更内容:
  1. homeworks テーブル新設
       宿題の基本情報（タイトル・期限・科目・状態）

  2. homework_submissions テーブル新設
       宿題ごとの生徒別提出状況（提出済みフラグ・日時）
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. homeworks テーブル ──────────────────────────────────────────────
    op.create_table(
        "homeworks",
        sa.Column("id",          sa.Integer(),    primary_key=True),
        sa.Column("title",       sa.String(200),  nullable=False),
        sa.Column("description", sa.Text(),       nullable=True),
        sa.Column("due_date",    sa.Date(),        nullable=False),
        sa.Column("subject",     sa.String(100),  nullable=True),
        # 状態: active（受付中）/ closed（締め切り）/ archived（非表示）
        sa.Column("status",      sa.String(16),   nullable=False, server_default="active"),
        sa.Column(
            "created_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at",  sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at",  sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_homeworks_id",         "homeworks", ["id"])
    op.create_index("ix_homeworks_created_by", "homeworks", ["created_by"])
    op.create_index("ix_homeworks_due_date",   "homeworks", ["due_date"])

    # ── 2. homework_submissions テーブル ──────────────────────────────────
    op.create_table(
        "homework_submissions",
        sa.Column("id",           sa.Integer(), primary_key=True),
        sa.Column(
            "homework_id",
            sa.Integer(),
            sa.ForeignKey("homeworks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "student_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # 提出状況
        sa.Column("submitted",    sa.Boolean(),             nullable=False, server_default=sa.text("false")),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("comment",      sa.Text(),                nullable=True),
        sa.Column("created_at",   sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at",   sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        # 同一宿題・同一生徒のレコードは1件のみ
        sa.UniqueConstraint("homework_id", "student_id", name="uq_submission_homework_student"),
    )
    op.create_index("ix_homework_submissions_id",          "homework_submissions", ["id"])
    op.create_index("ix_homework_submissions_homework_id", "homework_submissions", ["homework_id"])
    op.create_index("ix_homework_submissions_student_id",  "homework_submissions", ["student_id"])


def downgrade() -> None:
    op.drop_table("homework_submissions")
    op.drop_table("homeworks")
