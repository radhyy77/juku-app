"""add exam tables: exams, exam_scores

Revision ID: 0007
Revises: 0006
Create Date: 2026-03-01 00:00:00.000000

変更内容:
  1. exams テーブル新設
       試験の基本情報（試験名・科目・実施日・満点）

  2. exam_scores テーブル新設
       試験ごとの生徒別点数（点数・コメント）
       NULL = 未採点（0点と区別する）
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. exams テーブル ──────────────────────────────────────────────────
    op.create_table(
        "exams",
        sa.Column("id",          sa.Integer(),   primary_key=True),
        sa.Column("title",       sa.String(200), nullable=False),
        sa.Column("subject",     sa.String(100), nullable=True),
        sa.Column("exam_date",   sa.Date(),       nullable=False),
        # 満点（デフォルト100）。点数の割合計算に使用する
        sa.Column("max_score",   sa.Integer(),   nullable=False, server_default="100"),
        sa.Column("description", sa.Text(),      nullable=True),
        sa.Column(
            "created_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_exams_id",         "exams", ["id"])
    op.create_index("ix_exams_exam_date",  "exams", ["exam_date"])
    op.create_index("ix_exams_created_by", "exams", ["created_by"])

    # ── 2. exam_scores テーブル ────────────────────────────────────────────
    op.create_table(
        "exam_scores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "exam_id",
            sa.Integer(),
            sa.ForeignKey("exams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "student_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # score は NULL 可（NULL = 未採点、0点とは区別する）
        sa.Column("score",      sa.Integer(), nullable=True),
        sa.Column("comment",    sa.Text(),    nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        # 同一試験・同一生徒のレコードは1件のみ
        sa.UniqueConstraint("exam_id", "student_id", name="uq_score_exam_student"),
    )
    op.create_index("ix_exam_scores_id",         "exam_scores", ["id"])
    op.create_index("ix_exam_scores_exam_id",    "exam_scores", ["exam_id"])
    op.create_index("ix_exam_scores_student_id", "exam_scores", ["student_id"])


def downgrade() -> None:
    op.drop_table("exam_scores")
    op.drop_table("exams")
