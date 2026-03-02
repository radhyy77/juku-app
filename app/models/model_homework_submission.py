"""
宿題提出状況テーブルモデル

1宿題 × 1生徒 = 1レコードで提出状況を管理する。
宿題作成時に全生徒分のレコードを自動生成し、
提出チェック時に submitted=True に更新する運用。

状態遷移:
  [作成時]   submitted=False, submitted_at=None  → 未提出
  [提出確認] submitted=True,  submitted_at=datetime → 提出済み
  [取り消し] submitted=False, submitted_at=None  → 未提出に戻す（任意）
"""
from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, Boolean, Text, DateTime,
    ForeignKey, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


class HomeworkSubmission(Base):
    """
    宿題提出状況テーブル。

    宿題（Homework）と生徒（User）の中間テーブル。
    1宿題につき1生徒1レコード（ユニーク制約あり）。
    """
    __tablename__ = "homework_submissions"
    __table_args__ = (
        # 同一宿題・同一生徒のレコードは1件のみ
        UniqueConstraint("homework_id", "student_id", name="uq_submission_homework_student"),
    )

    id = Column(Integer, primary_key=True, index=True)

    # ── 紐付け ───────────────────────────────────────────────────────────────
    homework_id = Column(
        Integer,
        ForeignKey("homeworks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── 提出状況 ─────────────────────────────────────────────────────────────
    submitted    = Column(Boolean, nullable=False, default=False)  # 提出済みフラグ
    submitted_at = Column(DateTime(timezone=True), nullable=True)  # 提出確認日時

    # ── 教師メモ ─────────────────────────────────────────────────────────────
    # 提出物へのコメントや評価メモ（任意）
    comment = Column(Text, nullable=True)

    # ── タイムスタンプ ──────────────────────────────────────────────────────
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── リレーション ────────────────────────────────────────────────────────
    homework = relationship("Homework", back_populates="submissions")
    student  = relationship("User", foreign_keys=[student_id])

    def __repr__(self) -> str:
        return (
            f"<HomeworkSubmission hw={self.homework_id} "
            f"student={self.student_id} submitted={self.submitted}>"
        )
